"""Narration synthesis via edge-tts — free, no API key required.

Cahier des charges section 6.2, option 2 ("Narration IA / TTS"): generate
narration from the rewritten pedagogical script for consistency and clarity,
rather than reusing the (noisy, hesitation-filled) original recording.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import edge_tts

from .config import settings


async def _synthesize_async(text: str, output_path: Path, voice: str) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def synthesize(text: str, output_path: Path, voice: str | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_synthesize_async(text, output_path, voice or settings.tts_voice))
    return output_path


def audio_duration_seconds(audio_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed:\n{result.stderr}")
    return float(result.stdout.strip())
