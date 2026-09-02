"""Sprint 3 (original-voice mode): build narration scenes from the real recording.

Replaces the script.py -> storyboard.py -> narration.py (TTS) chain with an
approach that keeps the intervenant's actual voice (cahier section 6.2,
option 1): consecutive "kept" transcript segments (content_selection.py) are
grouped into scene-sized chunks, the matching audio is spliced directly from
the enhanced master recording (audio.py), and the LLM is asked only to plan
the accompanying visual per chunk - narration text and audio are real, not
generated.

Output is still a list[StoryboardScene] (same schema as the TTS pipeline),
so anything downstream (Sprint 3-4 visual rendering / assembly) doesn't care
which narration mode produced it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tqdm import tqdm

from s2m_pipeline.core import audio
from s2m_pipeline.from_video import content_selection
from s2m_pipeline.core import llm
from s2m_pipeline.models import Chapter, Scene, StoryboardScene, TranscriptSegment

# Target duration for a narration scene chunk before starting a new one -
# short enough for a visual change roughly every ~20s, matching the pacing
# used in the TTS-based storyboard prototype.
_TARGET_SCENE_SECONDS = 20.0
# A gap this large between two kept segments means content was cut in
# between (or a real pause) - start a new scene rather than splicing across it.
_MAX_GAP_SECONDS = 3.0

# A scene shorter than this reads as a jump cut: the viewer gets a new diagram
# before having read the previous one. Groups are closed whenever a segment is
# dropped or a pause occurs, which on an opening full of short sentences
# produced two-second scenes, so short groups are merged back afterwards.
_MIN_SCENE_SECONDS = 8.0
# Ceiling for a merged scene, so smoothing the rhythm never produces one long
# static shot.
_MAX_SCENE_SECONDS = 34.0
# Only merge across a break if little was actually removed between the two
# groups; beyond this the splice would join two unrelated moments.
_MERGE_MAX_GAP_SECONDS = 15.0


def _group_kept_segments(
    decided: list[tuple[TranscriptSegment, str]],
) -> list[list[TranscriptSegment]]:
    groups: list[list[TranscriptSegment]] = []
    current: list[TranscriptSegment] = []
    current_duration = 0.0

    for seg, decision in decided:
        if decision != "garder":
            if current:
                groups.append(current)
                current, current_duration = [], 0.0
            continue

        if current and (seg.start - current[-1].end) > _MAX_GAP_SECONDS:
            groups.append(current)
            current, current_duration = [], 0.0

        current.append(seg)
        current_duration += seg.end - seg.start
        if current_duration >= _TARGET_SCENE_SECONDS:
            groups.append(current)
            current, current_duration = [], 0.0

    if current:
        groups.append(current)

    return _merge_short_groups(groups)


def _group_seconds(group: list[TranscriptSegment]) -> float:
    return sum(s.end - s.start for s in group)


def _merge_short_groups(
    groups: list[list[TranscriptSegment]],
) -> list[list[TranscriptSegment]]:
    """Fold groups that are too short to stand as a scene into their neighbour.

    Grouping closes a scene on every dropped segment and every pause, which is
    right for keeping the spliced audio coherent but wrong for the rhythm: a
    passage of short sentences yields a run of two-second scenes, and the
    viewer sees the visuals flick past before reading them. Merging afterwards
    keeps the audio logic untouched and only smooths the cutting.
    """
    if not groups:
        return groups

    merged: list[list[TranscriptSegment]] = [list(groups[0])]
    for group in groups[1:]:
        previous = merged[-1]
        gap = group[0].start - previous[-1].end
        too_short = (
            _group_seconds(previous) < _MIN_SCENE_SECONDS
            or _group_seconds(group) < _MIN_SCENE_SECONDS
        )
        fits = _group_seconds(previous) + _group_seconds(group) <= _MAX_SCENE_SECONDS
        if too_short and fits and gap <= _MERGE_MAX_GAP_SECONDS:
            previous.extend(group)
            continue
        merged.append(list(group))

    return merged


def _overlapping_ocr(scenes: list[Scene], start: float, end: float) -> str:
    overlapping = [s for s in scenes if s.start < end and s.end > start]
    return "\n".join(dict.fromkeys(s.ocr_text for s in overlapping if s.ocr_text))


def _splice_group_audio(
    chapter_id: str, index: int, group: list[TranscriptSegment], master_audio_path: Path, output_dir: Path
) -> Path:
    scene_id = f"{chapter_id}_scene_{index:02d}"
    final_path = output_dir / f"{scene_id}.wav"

    if len(group) == 1:
        audio.extract_clip(master_audio_path, group[0].start, group[0].end, final_path)
        return final_path

    part_paths = []
    for j, seg in enumerate(group):
        part_path = output_dir / f"{scene_id}_part{j:02d}.wav"
        audio.extract_clip(master_audio_path, seg.start, seg.end, part_path)
        part_paths.append(part_path)

    audio.concat_clips(part_paths, final_path)
    for p in part_paths:
        p.unlink(missing_ok=True)

    return final_path


def build_narration_scenes(
    chapter: Chapter,
    transcript_segments: list[TranscriptSegment],
    scenes: list[Scene],
    master_audio_path: Path,
    output_dir: Path,
) -> list[StoryboardScene]:
    decided = content_selection.classify_chapter_segments(chapter, transcript_segments)
    groups = _group_kept_segments(decided)
    if not groups:
        return []

    narration_texts = [" ".join(s.text for s in group).strip() for group in groups]
    audio_paths = [
        _splice_group_audio(chapter.id, i, group, master_audio_path, output_dir)
        for i, group in enumerate(groups)
    ]
    durations = [audio.audio_duration_seconds(p) for p in audio_paths]

    ocr_text = _overlapping_ocr(scenes, chapter.start, chapter.end)
    visual_plans = llm.generate_visual_plan(list(enumerate(narration_texts)), ocr_text)

    result: list[StoryboardScene] = []
    for i in range(len(groups)):
        plan = visual_plans[i]
        result.append(
            StoryboardScene(
                scene_id=f"{chapter.id}_scene_{i:02d}",
                chapter_id=chapter.id,
                duration=round(durations[i], 2),
                narration=narration_texts[i],
                visual_type=plan.visual_type,
                visual_description=plan.visual_description,
                on_screen_text=plan.on_screen_text,
                transition=plan.transition,
                audio_path=str(audio_paths[i]),
            )
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="S2M Sprint 3 (original-voice) narration + storyboard"
    )
    parser.add_argument("--chapters", required=True, type=Path, help="Path to chapters.json")
    parser.add_argument("--scenes", required=True, type=Path, help="Path to scenes.json")
    parser.add_argument("--transcript", required=True, type=Path, help="Path to transcript.json")
    parser.add_argument("--master-audio", required=True, type=Path, help="Enhanced master audio.wav")
    parser.add_argument(
        "--output-dir", required=True, type=Path, help="Where to write spliced narration clips"
    )
    parser.add_argument("--output", type=Path, default=Path("output/storyboard.json"))
    parser.add_argument(
        "--chapter-ids",
        nargs="*",
        default=None,
        help="Only process these chapter ids. Default: all chapters.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip chapters whose scenes are already present in --output",
    )
    args = parser.parse_args()

    chapters = [
        Chapter.model_validate(c) for c in json.loads(args.chapters.read_text(encoding="utf-8"))
    ]
    scenes = [Scene.model_validate(s) for s in json.loads(args.scenes.read_text(encoding="utf-8"))]
    transcript_segments = [
        TranscriptSegment.model_validate(s)
        for s in json.loads(args.transcript.read_text(encoding="utf-8"))
    ]

    if args.chapter_ids:
        chapters = [c for c in chapters if c.id in args.chapter_ids]

    all_scenes: list[StoryboardScene] = []
    done_chapter_ids: set[str] = set()
    if args.resume and args.output.exists():
        existing = [
            StoryboardScene.model_validate(s)
            for s in json.loads(args.output.read_text(encoding="utf-8"))
        ]
        all_scenes.extend(existing)
        done_chapter_ids = {s.chapter_id for s in existing}

    for chapter in tqdm(chapters, desc="Building original-voice narration"):
        if chapter.id in done_chapter_ids:
            continue

        all_scenes.extend(
            build_narration_scenes(
                chapter, transcript_segments, scenes, args.master_audio, args.output_dir
            )
        )

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump([s.model_dump() for s in all_scenes], f, ensure_ascii=False, indent=2)

    total_duration = sum(s.duration for s in all_scenes)
    print(f"\nDone. {len(all_scenes)} narration scenes written to {args.output}")
    print(f"      Total narration duration: {total_duration / 60:.1f} min")


if __name__ == "__main__":
    main()
