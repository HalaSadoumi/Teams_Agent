"""Central configuration loaded from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"


@dataclass(frozen=True)
class Settings:
    hf_token: str | None = os.getenv("HF_TOKEN") or None
    whisper_model_size: str = os.getenv("WHISPER_MODEL_SIZE", "small")
    whisper_language: str | None = os.getenv("WHISPER_LANGUAGE") or None

    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None
    # gemini-3.6-flash's free tier is capped at 20 requests/day, too low for
    # a full video (one call per chapter, more later for script/storyboard).
    # gemini-flash-lite-latest has a separate, more generous free quota.
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

    # edge-tts voice for narration (Sprint 3). Free, no API key required.
    tts_voice: str = os.getenv("TTS_VOICE", "fr-FR-DeniseNeural")

    # Visual scene detection sensitivity (PySceneDetect ContentDetector threshold).
    # Lower = more sensitive (more scenes detected).
    scene_detect_threshold: float = 27.0

    # Minimum scene length in seconds, to avoid a flood of sub-second scenes.
    min_scene_len_seconds: float = 2.0

    # Chaptering (Sprint 2): transcript is grouped into fixed windows before
    # embedding, since embedding individual few-second ASR segments is too
    # noisy to detect topic shifts reliably.
    chapter_window_seconds: float = 60.0
    # Chaptering is expressed as a goal, not a fixed threshold: the pipeline
    # aims for chapters of roughly this length and searches for the
    # similarity threshold that achieves it on the video at hand (see
    # chaptering.calibrate). A hardcoded threshold would only ever suit the
    # recording it was tuned on.
    chapter_target_seconds: float = 330.0  # ~5.5 min, typical e-learning chapter
    chapter_count_min: int = 3
    chapter_count_max: int = 30
    # Upper bound on the "merge chapters shorter than this" floor; it is
    # scaled down for short videos so they can still be split at all.
    chapter_min_seconds: float = 180.0


settings = Settings()
