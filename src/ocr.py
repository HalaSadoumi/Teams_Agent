"""Extract text and visual labels from reference frames."""

from pathlib import Path
import re
from typing import Dict, List

try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None  # type: ignore
    pytesseract = None  # type: ignore


def _parse_frame_time(frame_path: Path, interval_seconds: int) -> float:
    match = re.search(r"frame_(\d+)\.jpg$", frame_path.name)
    if not match:
        return 0.0
    try:
        index = int(match.group(1))
        return (index - 1) * interval_seconds
    except ValueError:
        return 0.0


def _extract_ocr_text(frame_path: Path) -> str:
    if Image is None or pytesseract is None:
        return ""
    try:
        image = Image.open(frame_path)
        return pytesseract.image_to_string(image, lang="eng+fra").strip()
    except Exception:
        return ""


def extract_ocr_from_frames(frame_dir: Path, interval_seconds: int = 20) -> List[Dict[str, object]]:
    """Extract OCR and visual labels from keyframe images."""
    if not frame_dir.is_dir():
        return []

    results: List[Dict[str, object]] = []
    for frame in sorted(frame_dir.glob("*.jpg")):
        frame_time = _parse_frame_time(frame, interval_seconds)
        ocr_text = _extract_ocr_text(frame)
        visual_label = "reference_frame"
        if ocr_text:
            visual_label = "slide_or_screen_text"

        results.append(
            {
                "frame": str(frame),
                "frame_time": frame_time,
                "ocr_text": ocr_text,
                "visual_label": visual_label,
            }
        )
    return results
