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

    # Visual scene detection sensitivity (PySceneDetect ContentDetector threshold).
    # Lower = more sensitive (more scenes detected).
    scene_detect_threshold: float = 27.0

    # Minimum scene length in seconds, to avoid a flood of sub-second scenes.
    min_scene_len_seconds: float = 2.0

    # Chaptering (Sprint 2): transcript is grouped into fixed windows before
    # embedding, since embedding individual few-second ASR segments is too
    # noisy to detect topic shifts reliably.
    chapter_window_seconds: float = 60.0
    # Below this cosine similarity between consecutive windows, a new
    # chapter is proposed to start. Tuned empirically on the real S2M test
    # video: 0.45 under-triggers (one 37-minute chapter), 0.60+ over-triggers
    # (many chapters clamped to the minimum length below). 0.55 gave 17
    # chapters of 3-10 min on a 95-minute video, matching the cahier's own
    # Coursera-style example (~10 min/chapter average).
    chapter_similarity_threshold: float = 0.55
    # Candidate chapters shorter than this are merged into a neighbour, to
    # avoid a flood of near-empty chapters from noisy boundaries.
    chapter_min_seconds: float = 180.0


settings = Settings()
