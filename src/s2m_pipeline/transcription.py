"""ASR transcription via faster-whisper (local, CPU)."""

from __future__ import annotations

from pathlib import Path

from faster_whisper import WhisperModel

from .config import settings
from .models import TranscriptSegment

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(settings.whisper_model_size, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: Path) -> list[TranscriptSegment]:
    """Transcribe audio into timestamped segments.

    Uses int8 quantization for reasonable CPU speed, per the project's
    no-GPU constraint (cahier des charges, section 10).
    """
    model = _get_model()
    segments, _info = model.transcribe(
        str(audio_path),
        language=settings.whisper_language,
        vad_filter=True,
    )

    return [
        TranscriptSegment(start=seg.start, end=seg.end, text=seg.text.strip())
        for seg in segments
    ]
