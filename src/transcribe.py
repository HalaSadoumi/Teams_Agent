"""Transcribe audio and export JSON, readable text, and SRT captions."""

import argparse
import json
import os
from pathlib import Path
from faster_whisper import WhisperModel
from .export_subtitles import export_srt

if os.environ.get("HF_HUB_DISABLE_SYMLINKS") is None:
    os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def transcribe(audio_path: Path, output_dir: Path, model_size: str = "small") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    model_cache = PROJECT_ROOT / ".cache" / "faster-whisper"
    model = WhisperModel(model_size, device="cpu", compute_type="int8", download_root=str(model_cache))
    segments, info = model.transcribe(str(audio_path), beam_size=5, vad_filter=True)
    records = [{"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip()} for s in segments]
    transcript = {"source_audio": str(audio_path), "language": info.language, "language_probability": round(info.language_probability, 4), "segments": records}
    json_path = output_dir / "transcript.json"
    json_path.write_text(json.dumps(transcript, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "transcript.txt").write_text("\n".join(f"[{s['start']:08.2f} - {s['end']:08.2f}] {s['text']}" for s in records), encoding="utf-8")
    export_srt(json_path, output_dir / "captions.srt")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/transcripts"))
    parser.add_argument("--model", default="small")
    arguments = parser.parse_args()
    transcribe(arguments.audio, arguments.output_dir, arguments.model)
