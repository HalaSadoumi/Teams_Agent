"""Speech recognition wrapper for the transformation pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .model import AudioTranscriptSegment
from .transcribe import transcribe


@dataclass
class TranscriptionBundle:
    segments: List[AudioTranscriptSegment]
    language: str
    language_probability: float


def transcribe_audio(
    audio_path: Path,
    output_dir: Path,
    model_size: str = "medium",
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
) -> TranscriptionBundle:
    """Transcribe the audio and return timestamped segments."""
    result = transcribe(
        audio_path,
        output_dir,
        model_size=model_size,
        language=language,
        initial_prompt=initial_prompt,
    )
    return TranscriptionBundle(
        segments=[
            AudioTranscriptSegment(
                start=float(segment["start"]),
                end=float(segment["end"]),
                text=segment["text"].strip(),
                speaker=None,
            )
            for segment in result.segments
        ],
        language=result.language,
        language_probability=result.language_probability,
    )


def load_transcript_segments(transcript_path: Path) -> List[AudioTranscriptSegment]:
    with transcript_path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return [
        AudioTranscriptSegment(
            start=float(segment["start"]),
            end=float(segment["end"]),
            text=segment["text"].strip(),
            speaker=segment.get("speaker"),
        )
        for segment in data.get("segments", [])
    ]
