"""Export timestamped Faster-Whisper JSON as a standards-compliant SRT file."""

import json
from pathlib import Path

def srt_timestamp(value: float) -> str:
    milliseconds = round(max(0, value) * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

def export_srt(transcript_json: Path, output_srt: Path) -> None:
    data = json.loads(transcript_json.read_text(encoding="utf-8"))
    lines: list[str] = []
    for number, segment in enumerate(data["segments"], start=1):
        text = segment["text"].strip()
        if text:
            lines.extend([str(number), f"{srt_timestamp(segment['start'])} --> {srt_timestamp(segment['end'])}", text, ""])
    output_srt.parent.mkdir(parents=True, exist_ok=True)
    output_srt.write_text("\n".join(lines), encoding="utf-8")
