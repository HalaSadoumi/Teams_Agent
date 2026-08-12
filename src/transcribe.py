"""Transcribe audio and export JSON, readable text, and SRT captions."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from faster_whisper import WhisperModel

from .export_subtitles import export_srt

if os.environ.get("HF_HUB_DISABLE_SYMLINKS") is None:
    os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class TranscriptionResult:
    segments: List[dict]
    language: str
    language_probability: float


def transcribe(
    audio_path: Path,
    output_dir: Path,
    model_size: str = "medium",
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
) -> TranscriptionResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    model_cache = PROJECT_ROOT / ".cache" / "faster-whisper"
    model = WhisperModel(
        model_size,
        device="cpu",
        compute_type="int8",
        download_root=str(model_cache),
    )

    kwargs = {
        "beam_size": 5,
        "best_of": 5,
        "vad_filter": True,
        "vad_parameters": {
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 200,
        },
        "condition_on_previous_text": True,
        "temperature": [0.0, 0.2, 0.4],
        "compression_ratio_threshold": 2.4,
        "log_prob_threshold": -1.0,
        "no_speech_threshold": 0.6,
    }
    if language:
        kwargs["language"] = language
    if initial_prompt:
        kwargs["initial_prompt"] = initial_prompt

    segments_iter, info = model.transcribe(str(audio_path), **kwargs)
    records = [
        {"start": round(segment.start, 3), "end": round(segment.end, 3), "text": segment.text.strip()}
        for segment in segments_iter
    ]

    transcript = {
        "source_audio": str(audio_path),
        "language": info.language,
        "language_probability": round(info.language_probability, 4),
        "model": model_size,
        "corrected": False,
        "segments": records,
    }

    json_path = output_dir / "transcript.json"
    json_path.write_text(json.dumps(transcript, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "transcript.txt").write_text(
        "\n".join(f"[{segment['start']:08.2f} - {segment['end']:08.2f}] {segment['text']}" for segment in records),
        encoding="utf-8",
    )
    export_srt(json_path, output_dir / "captions.srt")

    return TranscriptionResult(
        segments=records,
        language=info.language,
        language_probability=float(info.language_probability),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/transcript"))
    parser.add_argument("--model", default="medium")
    parser.add_argument("--language", default=None)
    parser.add_argument("--initial-prompt", default=None)
    arguments = parser.parse_args()
    transcribe(
        arguments.audio,
        arguments.output_dir,
        arguments.model,
        language=arguments.language,
        initial_prompt=arguments.initial_prompt,
    )
