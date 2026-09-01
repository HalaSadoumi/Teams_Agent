"""Per-chapter subtitle tracks, timed from the real ASR segments.

The narration of each storyboard scene is the concatenation of a consecutive
run of ASR segments, so those segments can be matched back to recover their
true start/end times. Cue timing therefore follows the actual delivery
instead of assuming speech is evenly paced across a scene, which is what made
burnt-in captions drift.

Emitted as WebVTT next to each chapter video, so the player can offer them as
a toggleable track rather than baking them into the picture.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .models import StoryboardScene, TranscriptSegment

# How many dropped segments may sit between two kept ones inside a scene.
# Scenes are merged across cut passages to keep the cutting rhythm calm, so a
# scene's segments are ordered but not necessarily adjacent in the transcript.
_MAX_SKIPPED_SEGMENTS = 40


@dataclass
class Cue:
    start: float
    end: float
    text: str


def _format(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    h, millis = divmod(millis, 3_600_000)
    m, millis = divmod(millis, 60_000)
    s, ms = divmod(millis, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def match_scene_segments(
    narration: str, segments: list[TranscriptSegment], search_from: int
) -> tuple[list[TranscriptSegment], int]:
    """Find the run of ASR segments whose text makes up this narration.

    The segments are in order but need not be adjacent: a scene may span a
    passage that was dropped, since short groups are merged back together to
    keep the cutting rhythm calm. Segments that do not continue the narration
    are therefore skipped rather than ending the match — matching them exactly
    as consecutive made every merged scene fall back to one long cue.

    Returns the run and the index to continue searching from. Scenes are
    processed in order, so the search starts where the previous one ended,
    which also keeps repeated phrases from matching the wrong occurrence.
    """
    target = narration.split()
    if not target:
        return [], search_from

    for start in range(search_from, len(segments)):
        words = segments[start].text.split()
        if not words or words != target[: len(words)]:
            continue

        run = [segments[start]]
        matched = len(words)
        skipped = 0
        index = start + 1
        while matched < len(target) and index < len(segments) and skipped <= _MAX_SKIPPED_SEGMENTS:
            words = segments[index].text.split()
            if words and words == target[matched : matched + len(words)]:
                run.append(segments[index])
                matched += len(words)
                skipped = 0
            else:
                skipped += 1
            index += 1

        if matched == len(target):
            return run, index

    return [], search_from


def build_chapter_cues(
    scenes: list[StoryboardScene], segments: list[TranscriptSegment]
) -> list[Cue]:
    """Cues for one chapter, on the chapter's own timeline (starting at 0)."""
    cues: list[Cue] = []
    cursor = 0.0  # position in the rendered chapter video
    search_from = 0

    for scene in scenes:
        run, search_from = match_scene_segments(scene.narration, segments, search_from)

        if not run:
            # No exact match: fall back to one cue spanning the whole scene,
            # so the chapter still gets subtitles rather than a silent gap.
            cues.append(Cue(cursor, cursor + scene.duration, scene.narration))
            cursor += scene.duration
            continue

        # Segments are spliced back to back in the rendered audio, so each
        # one's offset inside the scene is the sum of the preceding lengths.
        offset = 0.0
        for segment in run:
            length = segment.end - segment.start
            cues.append(Cue(cursor + offset, cursor + offset + length, segment.text.strip()))
            offset += length
        cursor += scene.duration

    return cues


def write_vtt(cues: list[Cue], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["WEBVTT", ""]
    for i, cue in enumerate(cues, start=1):
        lines += [str(i), f"{_format(cue.start)} --> {_format(cue.end)}", cue.text, ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate per-chapter subtitle tracks")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    storyboard = [
        StoryboardScene.model_validate(s)
        for s in json.loads(args.storyboard.read_text(encoding="utf-8"))
    ]
    segments = [
        TranscriptSegment.model_validate(s)
        for s in json.loads(args.transcript.read_text(encoding="utf-8"))
    ]

    by_chapter: dict[str, list[StoryboardScene]] = {}
    for scene in storyboard:
        by_chapter.setdefault(scene.chapter_id, []).append(scene)

    total_cues = 0
    fallbacks = 0
    for chapter_id, scenes in by_chapter.items():
        cues = build_chapter_cues(scenes, segments)
        # A fallback cue spans an entire scene; count them as a quality signal.
        fallbacks += sum(
            1 for c, s in zip(cues, scenes) if abs((c.end - c.start) - s.duration) < 0.01
        )
        write_vtt(cues, args.output_dir / f"{chapter_id}.vtt")
        total_cues += len(cues)

    print(f"Wrote {len(by_chapter)} subtitle tracks ({total_cues} cues) to {args.output_dir}")
    if fallbacks:
        print(f"  {fallbacks} scene(s) used a whole-scene fallback cue")


if __name__ == "__main__":
    main()
