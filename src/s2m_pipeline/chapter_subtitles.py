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

# How far ahead to look when matching a scene's narration back to the
# transcript; scenes group a handful of segments, never dozens.
_MAX_SEGMENTS_PER_SCENE = 60


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
    """Find the consecutive run of ASR segments whose text is this narration.

    Returns the run and the index to continue searching from. Scenes are
    processed in order, so the search starts where the previous one ended,
    which also keeps repeated phrases from matching the wrong occurrence.
    """
    target = " ".join(narration.split())

    for start in range(search_from, len(segments)):
        accumulated = ""
        for end in range(start, min(start + _MAX_SEGMENTS_PER_SCENE, len(segments))):
            accumulated = f"{accumulated} {segments[end].text}".strip()
            accumulated = " ".join(accumulated.split())
            if accumulated == target:
                return segments[start : end + 1], end + 1
            if len(accumulated) > len(target):
                break
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
