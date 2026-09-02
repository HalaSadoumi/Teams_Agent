"""Speaker diarization via pyannote.audio, with a graceful single-speaker fallback.

pyannote.audio + a Hugging Face token are an optional extra (see
requirements-diarization.txt and .env.example). If unavailable, every
segment is labelled "speaker_1" so the rest of the pipeline still runs
end-to-end — Sprint 1's goal is a working ingestion pipeline, not a
perfect one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from s2m_pipeline.config import settings


@dataclass
class SpeakerTurn:
    start: float
    end: float
    speaker: str


def diarize(audio_path: Path) -> list[SpeakerTurn]:
    if not settings.hf_token:
        return []

    try:
        from pyannote.audio import Pipeline
    except ImportError:
        return []

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1", use_auth_token=settings.hf_token
    )
    diarization = pipeline(str(audio_path))

    turns = []
    for turn, _, speaker_label in diarization.itertracks(yield_label=True):
        turns.append(SpeakerTurn(start=turn.start, end=turn.end, speaker=speaker_label))
    return turns


def speaker_at(turns: list[SpeakerTurn], timestamp: float) -> str:
    """Look up which speaker is talking at a given timestamp."""
    for turn in turns:
        if turn.start <= timestamp <= turn.end:
            return turn.speaker
    return "speaker_1"
