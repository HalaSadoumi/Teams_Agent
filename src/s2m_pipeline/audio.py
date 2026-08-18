"""Audio extraction from the source video, via FFmpeg."""

from __future__ import annotations

import subprocess
from pathlib import Path


def extract_audio(video_path: Path, output_wav_path: Path, sample_rate: int = 16000) -> Path:
    """Extract mono PCM audio at `sample_rate` Hz, suitable for ASR models."""
    output_wav_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-c:a",
        "pcm_s16le",
        str(output_wav_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed:\n{result.stderr}")

    return output_wav_path
