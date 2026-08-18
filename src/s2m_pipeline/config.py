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

    # Visual scene detection sensitivity (PySceneDetect ContentDetector threshold).
    # Lower = more sensitive (more scenes detected).
    scene_detect_threshold: float = 27.0

    # Minimum scene length in seconds, to avoid a flood of sub-second scenes.
    min_scene_len_seconds: float = 2.0


settings = Settings()
