"""Speech recognition wrapper for the transformation pipeline."""

from pathlib import Path
from typing import List

from .transcribe import transcribe
from .model import AudioTranscriptSegment


def transcribe_audio(audio_path: Path, output_dir: Path, model_size: str = "small") -> List[AudioTranscriptSegment]:
    """Transcribe the audio and return timestamped segments."""
    transcribe(audio_path, output_dir, model_size)
    transcript_path = output_dir / "transcript.json"
    if not transcript_path.is_file():
        raise FileNotFoundError(f"Transcript JSON not found: {transcript_path}")

    import json

    with transcript_path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    return [
        AudioTranscriptSegment(
            start=float(segment["start"]),
            end=float(segment["end"]),
            text=segment["text"].strip(),
            speaker=None,
        )
        for segment in data.get("segments", [])
    ]
