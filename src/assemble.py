"""Assemble transformed course assets into a renderable output."""

from pathlib import Path
from typing import Optional

from .render_video import render_baseline


def assemble_course(
    source_video: Path,
    narration_audio: Optional[Path],
    captions_path: Optional[Path],
    output_video: Path,
) -> Path:
    """Render a baseline course output using captions and optional narration."""
    if narration_audio is None or captions_path is None:
        raise ValueError("Both narration_audio and captions_path are required for baseline assembly.")
    output_video.parent.mkdir(parents=True, exist_ok=True)
    render_baseline(source_video, narration_audio, captions_path, output_video)
    return output_video
