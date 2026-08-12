"""Render a captioned 1080p baseline using the enhanced original narration audio."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import imageio_ffmpeg


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        raise RuntimeError(f"Could not probe duration for {path}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _escape_subtitle_path(captions: Path) -> str:
    return captions.resolve().as_posix().replace(":", "\\:")


def render_baseline(video: Path, narration: Path, captions: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    video_duration = _probe_duration(video)
    audio_duration = _probe_duration(narration)
    subtitle_path = _escape_subtitle_path(captions)

    audio_filter = "anull"
    if audio_duration + 0.05 < video_duration:
        pad_seconds = video_duration - audio_duration + 0.1
        audio_filter = f"apad=pad_dur={pad_seconds:.3f}"
    elif audio_duration > video_duration + 0.05:
        audio_filter = f"atrim=0:{video_duration:.3f}"

    vf = (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
        f"subtitles='{subtitle_path}'"
    )

    subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-i",
            str(video),
            "-i",
            str(narration),
            "-vf",
            vf,
            "-af",
            audio_filter,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "256k",
            "-t",
            f"{video_duration:.3f}",
            str(output),
        ],
        check=True,
    )
