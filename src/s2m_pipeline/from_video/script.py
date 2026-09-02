"""Sprint 3 (part 1): script pedagogique generation, per chapter.

Cahier des charges section 5.5: the generated script must preserve meaning,
stay factually exact, follow the chapter structure, drop conversational
filler, improve clarity, keep technical terminology, and connect ideas
naturally. It is a rewrite, not a summary (section 2, "principe fondamental
du projet").
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tqdm import tqdm

from s2m_pipeline.core import llm
from s2m_pipeline.models import Chapter, Scene, TranscriptSegment


def _overlapping_text(segments: list[TranscriptSegment], start: float, end: float) -> str:
    return " ".join(s.text for s in segments if s.start < end and s.end > start).strip()


def _overlapping_ocr(scenes: list[Scene], start: float, end: float) -> str:
    overlapping = [s for s in scenes if s.start < end and s.end > start]
    return "\n".join(dict.fromkeys(s.ocr_text for s in overlapping if s.ocr_text))


def build_scripts(
    chapters: list[Chapter],
    transcript_segments: list[TranscriptSegment],
    scenes: list[Scene],
    checkpoint_path: Path | None = None,
    resume: bool = False,
) -> dict[str, str]:
    """Returns {chapter_id: script_text}.

    Checkpointed after every chapter (same reasoning as chaptering.py: a
    quota error partway through shouldn't lose completed calls).
    """
    scripts: dict[str, str] = {}
    if resume and checkpoint_path is not None and checkpoint_path.exists():
        scripts = json.loads(checkpoint_path.read_text(encoding="utf-8"))

    for chapter in tqdm(chapters, desc="Generating scripts"):
        if chapter.id in scripts:
            continue

        transcript_text = _overlapping_text(transcript_segments, chapter.start, chapter.end)
        ocr_text = _overlapping_ocr(scenes, chapter.start, chapter.end)
        scripts[chapter.id] = llm.generate_script(transcript_text, ocr_text)

        if checkpoint_path is not None:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(scripts, f, ensure_ascii=False, indent=2)

    return scripts


def main() -> None:
    parser = argparse.ArgumentParser(description="S2M Sprint 3 script generation")
    parser.add_argument("--chapters", required=True, type=Path, help="Path to chapters.json")
    parser.add_argument("--scenes", required=True, type=Path, help="Path to scenes.json")
    parser.add_argument("--transcript", required=True, type=Path, help="Path to transcript.json")
    parser.add_argument("--output", type=Path, default=Path("output/scripts.json"))
    parser.add_argument(
        "--chapter-ids",
        nargs="*",
        default=None,
        help="Only generate scripts for these chapter ids (e.g. chapter_00 chapter_01). "
        "Default: all chapters.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse scripts already present in --output instead of re-generating them",
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

    scripts = build_scripts(
        chapters, transcript_segments, scenes, checkpoint_path=args.output, resume=args.resume
    )

    print(f"\nDone. {len(scripts)} scripts written to {args.output}")


if __name__ == "__main__":
    main()
