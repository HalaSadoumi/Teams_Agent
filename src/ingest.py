"""Ingest raw video assets and prepare audio and visual inputs."""

from pathlib import Path
import subprocess

import imageio_ffmpeg


def extract_audio(video_path: Path, output_audio: Path, sample_rate: int = 48000, channels: int = 1) -> Path:
    """Extract a standardized WAV audio track from the source video."""
    output_audio.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([
        ffmpeg_exe,
        "-y",
        "-i",
        str(video_path),
        "-ac",
        str(channels),
        "-ar",
        str(sample_rate),
        "-c:a",
        "pcm_s16le",
        str(output_audio),
    ], check=True)
    return output_audio


def extract_keyframes(video_path: Path, output_dir: Path, interval_seconds: int = 20) -> Path:
    """Export periodic reference frames for visual review and OCR."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    frame_pattern = output_dir / "frame_%04d.jpg"
    subprocess.run([
        ffmpeg_exe,
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps=1/{interval_seconds}",
        "-q:v",
        "2",
        str(frame_pattern),
    ], check=True)
    return output_dir


def normalize_video_path(video_path: Path) -> Path:
    return video_path.resolve()
