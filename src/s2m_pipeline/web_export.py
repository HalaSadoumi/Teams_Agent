"""Stage the course for the web player prototype.

Collects everything the player needs into web/data/: chapter metadata
measured from the rendered files, the quiz, and the per-chapter videos.

Only chapters that have actually been rendered are exported, so the player
can be tried while a long batch is still running instead of waiting for all
of them.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .assemble import _format_timestamp
from .audio import audio_duration_seconds
from .models import Chapter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = PROJECT_ROOT / "web"


def export(chapters_path: Path, video_dir: Path, quiz_path: Path | None, copy_videos: bool) -> None:
    chapters = [
        Chapter.model_validate(c) for c in json.loads(chapters_path.read_text(encoding="utf-8"))
    ]

    data_dir = WEB_DIR / "data"
    videos_dir = data_dir / "videos"
    data_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    exported: list[dict] = []
    missing: list[str] = []
    cursor = 0.0

    for chapter in chapters:
        source = video_dir / f"{chapter.id}.mp4"
        if not source.exists() or source.stat().st_size == 0:
            missing.append(chapter.id)
            continue

        try:
            duration = audio_duration_seconds(source)
        except RuntimeError:
            # A render still writing this file leaves it unreadable (no moov
            # atom yet); treat it as not ready rather than aborting the export,
            # so the player can be used while a batch is running.
            missing.append(chapter.id)
            continue
        exported.append(
            {
                "id": chapter.id,
                "title": chapter.title,
                "start": round(cursor, 3),
                "end": round(cursor + duration, 3),
                "duration": round(duration, 3),
                "timestamp": _format_timestamp(cursor),
                "summary": chapter.summary,
                "key_points": chapter.key_points,
            }
        )
        cursor += duration

        if copy_videos:
            target = videos_dir / source.name
            if not target.exists() or target.stat().st_size != source.stat().st_size:
                shutil.copy(source, target)

    (data_dir / "course_chapters.json").write_text(
        json.dumps(exported, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if quiz_path and quiz_path.exists():
        quiz = json.loads(quiz_path.read_text(encoding="utf-8"))
        # Keep only quizzes for chapters actually exported, so the player
        # never advertises a quiz for a chapter it cannot play.
        exported_ids = {c["id"] for c in exported}
        filtered = {k: v for k, v in quiz.items() if k in exported_ids}
        (data_dir / "quiz.json").write_text(
            json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        questions = sum(len(v) for v in filtered.values())
    else:
        (data_dir / "quiz.json").write_text("{}", encoding="utf-8")
        questions = 0

    total = cursor / 60
    print(f"Exported {len(exported)}/{len(chapters)} chapters ({total:.1f} min) to {data_dir}")
    print(f"  {questions} quiz questions")
    if missing:
        print(f"  {len(missing)} not yet rendered: {', '.join(missing)}")
    if not copy_videos:
        print("  videos not copied (--no-videos)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage the course for the web player")
    parser.add_argument("--chapters", required=True, type=Path)
    parser.add_argument("--video-dir", required=True, type=Path)
    parser.add_argument("--quiz", type=Path, default=None)
    parser.add_argument(
        "--no-videos", action="store_true", help="Only refresh metadata, skip copying video files"
    )
    args = parser.parse_args()

    export(args.chapters, args.video_dir, args.quiz, copy_videos=not args.no_videos)


if __name__ == "__main__":
    main()
