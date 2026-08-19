"""Subtitle file generation (SRT / WebVTT) from ASR transcript segments.

Not an MVP requirement per the cahier des charges (section 14 lists subtitles
as a post-MVP feature), but since timestamped transcript segments already
exist as a byproduct of transcription, exporting them as subtitles is nearly
free and useful for reviewing pipeline output.
"""

from __future__ import annotations

from pathlib import Path

from .models import TranscriptSegment


def _format_srt_timestamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_vtt_timestamp(seconds: float) -> str:
    return _format_srt_timestamp(seconds).replace(",", ".")


def write_srt(segments: list[TranscriptSegment], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{_format_srt_timestamp(seg.start)} --> {_format_srt_timestamp(seg.end)}")
        lines.append(seg.text)
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def write_vtt(segments: list[TranscriptSegment], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["WEBVTT", ""]
    for seg in segments:
        lines.append(f"{_format_vtt_timestamp(seg.start)} --> {_format_vtt_timestamp(seg.end)}")
        lines.append(seg.text)
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
