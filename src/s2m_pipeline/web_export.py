"""Stage a course for the web player, and register it in the catalog.

Each course gets its own folder under web/data/<course_id>/ holding its
chapter metadata, quiz, videos and optional reading support (PDF). A shared
web/data/courses.json lists every exported course, which is what the catalog
page reads — so adding a second course is just another run of this command.

Only chapters that have actually been rendered are exported, and files a
render is still writing are skipped, so the player can be used while a long
batch is running.
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
DATA_DIR = WEB_DIR / "data"
CATALOG_PATH = DATA_DIR / "courses.json"


def _export_chapters(
    chapters: list[Chapter], video_dir: Path, course_dir: Path, copy_videos: bool
) -> tuple[list[dict], list[str]]:
    videos_dir = course_dir / "videos"
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
            # atom yet); treat it as not ready rather than aborting.
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

    return exported, missing


def _update_catalog(entry: dict) -> list[dict]:
    catalog: list[dict] = []
    if CATALOG_PATH.exists():
        try:
            catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8")).get("courses", [])
        except json.JSONDecodeError:
            catalog = []

    catalog = [c for c in catalog if c.get("id") != entry["id"]]
    catalog.append(entry)
    catalog.sort(key=lambda c: c.get("title", ""))

    CATALOG_PATH.write_text(
        json.dumps({"courses": catalog}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return catalog


def export(
    course_id: str,
    title: str,
    description: str,
    chapters_path: Path,
    video_dir: Path,
    quiz_path: Path | None,
    pdf_path: Path | None,
    thumbnail_path: Path | None,
    copy_videos: bool,
) -> None:
    chapters = [
        Chapter.model_validate(c) for c in json.loads(chapters_path.read_text(encoding="utf-8"))
    ]
    course_dir = DATA_DIR / course_id
    course_dir.mkdir(parents=True, exist_ok=True)

    exported, missing = _export_chapters(chapters, video_dir, course_dir, copy_videos)
    (course_dir / "course_chapters.json").write_text(
        json.dumps(exported, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    questions = 0
    if quiz_path and quiz_path.exists():
        quiz = json.loads(quiz_path.read_text(encoding="utf-8"))
        exported_ids = {c["id"] for c in exported}
        # Never advertise a quiz for a chapter the player cannot play.
        filtered = {k: v for k, v in quiz.items() if k in exported_ids}
        questions = sum(len(v) for v in filtered.values())
    else:
        filtered = {}
    (course_dir / "quiz.json").write_text(
        json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    pdf_name = None
    if pdf_path and pdf_path.exists():
        pdf_name = "support.pdf"
        shutil.copy(pdf_path, course_dir / pdf_name)

    thumb_name = None
    if thumbnail_path and thumbnail_path.exists():
        thumb_name = "thumbnail" + thumbnail_path.suffix
        shutil.copy(thumbnail_path, course_dir / thumb_name)

    total_minutes = round(sum(c["duration"] for c in exported) / 60)
    catalog = _update_catalog(
        {
            "id": course_id,
            "title": title,
            "description": description,
            "chapters": len(exported),
            "duration_minutes": total_minutes,
            "questions": questions,
            "pdf": pdf_name,
            "thumbnail": thumb_name,
        }
    )

    print(f"Exported '{title}' -> {course_dir}")
    print(f"  {len(exported)}/{len(chapters)} chapters ({total_minutes} min), {questions} questions")
    if pdf_name:
        print("  reading support included")
    if missing:
        print(f"  {len(missing)} not yet rendered: {', '.join(missing)}")
    print(f"  catalog now lists {len(catalog)} course(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage a course for the web player")
    parser.add_argument("--course-id", required=True, help="Folder name under web/data/")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--chapters", required=True, type=Path)
    parser.add_argument("--video-dir", required=True, type=Path)
    parser.add_argument("--quiz", type=Path, default=None)
    parser.add_argument("--pdf", type=Path, default=None, help="Reading support to offer")
    parser.add_argument("--thumbnail", type=Path, default=None)
    parser.add_argument(
        "--no-videos", action="store_true", help="Only refresh metadata, skip copying videos"
    )
    args = parser.parse_args()

    export(
        args.course_id,
        args.title,
        args.description,
        args.chapters,
        args.video_dir,
        args.quiz,
        args.pdf,
        args.thumbnail,
        copy_videos=not args.no_videos,
    )


if __name__ == "__main__":
    main()
