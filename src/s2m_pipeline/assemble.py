"""Sprint 4: final assembly — chapter videos into one navigable course.

Concatenates the per-chapter renders into a single MP4 and attaches the
chapter metadata required by the cahier des charges (section 3.2, objective
8: "métadonnées de chapitrage exploitables par une plateforme
d'apprentissage"), in three forms:

  - embedded MP4 chapter markers (players show a chapter list / seek points)
  - chapters.vtt (WebVTT chapters, for web players)
  - course_chapters.json (titles, timestamps, summaries, key points)

Chapter boundaries are measured from the *rendered* files with ffprobe rather
than summed from the storyboard, so the timestamps match the real video
exactly (per-scene frame rounding otherwise drifts by a few hundredths).
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .audio import audio_duration_seconds
from .models import Chapter


@dataclass
class RenderedChapter:
    chapter: Chapter
    path: Path
    start: float
    duration: float

    @property
    def end(self) -> float:
        return self.start + self.duration


def _format_timestamp(seconds: float, *, millis: bool = False) -> str:
    total_ms = round(seconds * 1000)
    h, total_ms = divmod(total_ms, 3_600_000)
    m, total_ms = divmod(total_ms, 60_000)
    s, ms = divmod(total_ms, 1000)
    if millis:
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
    return f"{h:02d}:{m:02d}:{s:02d}"


def measure_chapters(chapters: list[Chapter], video_dir: Path) -> list[RenderedChapter]:
    rendered: list[RenderedChapter] = []
    cursor = 0.0
    for chapter in chapters:
        path = video_dir / f"{chapter.id}.mp4"
        if not path.exists():
            raise FileNotFoundError(f"Missing rendered chapter: {path}")
        duration = audio_duration_seconds(path)  # ffprobe format=duration
        rendered.append(RenderedChapter(chapter=chapter, path=path, start=cursor, duration=duration))
        cursor += duration
    return rendered


def _write_ffmetadata(rendered: list[RenderedChapter], path: Path) -> Path:
    lines = [";FFMETADATA1"]
    for r in rendered:
        # Timebase 1/1000 => start/end expressed in milliseconds.
        lines += [
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={round(r.start * 1000)}",
            f"END={round(r.end * 1000)}",
            f"title={r.chapter.title}",
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_vtt(rendered: list[RenderedChapter], path: Path) -> Path:
    lines = ["WEBVTT", ""]
    for i, r in enumerate(rendered, start=1):
        lines += [
            str(i),
            f"{_format_timestamp(r.start, millis=True)} --> {_format_timestamp(r.end, millis=True)}",
            r.chapter.title,
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_json(rendered: list[RenderedChapter], path: Path) -> Path:
    data = [
        {
            "id": r.chapter.id,
            "title": r.chapter.title,
            "start": round(r.start, 3),
            "end": round(r.end, 3),
            "duration": round(r.duration, 3),
            "timestamp": _format_timestamp(r.start),
            "summary": r.chapter.summary,
            "key_points": r.chapter.key_points,
        }
        for r in rendered
    ]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def concat_chapters(rendered: list[RenderedChapter], metadata_path: Path, output_path: Path) -> Path:
    """Concatenate chapter MP4s and attach chapter markers.

    Uses stream copy: every chapter comes from the same Remotion render
    settings (same codec/resolution/fps), so no re-encode is needed.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    list_file = output_path.with_suffix(".concat.txt")
    list_file.write_text(
        "\n".join(f"file '{r.path.resolve().as_posix()}'" for r in rendered), encoding="utf-8"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-i",
        str(metadata_path),
        "-map_metadata",
        "1",
        "-c",
        "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    list_file.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed:\n{result.stderr}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="S2M Sprint 4 final course assembly")
    parser.add_argument("--chapters", required=True, type=Path, help="Path to chapters.json")
    parser.add_argument("--video-dir", required=True, type=Path, help="Directory of <chapter_id>.mp4")
    parser.add_argument("--output-dir", type=Path, default=Path("output/course"))
    args = parser.parse_args()

    chapters = [
        Chapter.model_validate(c) for c in json.loads(args.chapters.read_text(encoding="utf-8"))
    ]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Measuring {len(chapters)} rendered chapters ...")
    rendered = measure_chapters(chapters, args.video_dir)

    metadata_path = _write_ffmetadata(rendered, args.output_dir / "chapters.ffmetadata")
    vtt_path = _write_vtt(rendered, args.output_dir / "chapters.vtt")
    json_path = _write_json(rendered, args.output_dir / "course_chapters.json")

    print("Concatenating into the full course video ...")
    course_path = concat_chapters(rendered, metadata_path, args.output_dir / "course_full.mp4")

    total = rendered[-1].end if rendered else 0.0
    print(f"\nDone. Course: {course_path} ({total / 60:.1f} min)")
    print(f"      Chapter metadata: {json_path}, {vtt_path}")
    print()
    for r in rendered:
        print(f"  {_format_timestamp(r.start)}  {r.chapter.title}")


if __name__ == "__main__":
    main()
