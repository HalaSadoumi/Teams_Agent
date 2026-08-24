"""Narration synthesis via edge-tts — free, no API key required.

Cahier des charges section 6.2, option 2 ("Narration IA / TTS"): generate
narration from the rewritten pedagogical script for consistency and clarity,
rather than reusing the (noisy, hesitation-filled) original recording.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

from .audio import audio_duration_seconds  # re-exported for existing callers
from .config import settings

__all__ = ["synthesize", "audio_duration_seconds"]


async def _synthesize_async(text: str, output_path: Path, voice: str) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def synthesize(text: str, output_path: Path, voice: str | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_synthesize_async(text, output_path, voice or settings.tts_voice))
    return output_path
