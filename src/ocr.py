"""Extract text and visual labels from reference frames."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

try:
    from PIL import Image, ImageEnhance, ImageOps
except ImportError:
    Image = None  # type: ignore
    ImageEnhance = None  # type: ignore
    ImageOps = None  # type: ignore

try:
    import pytesseract
except ImportError:
    pytesseract = None  # type: ignore

try:
    import easyocr
except ImportError:
    easyocr = None  # type: ignore

_easyocr_reader = None


def _parse_frame_time(frame_path: Path, interval_seconds: int) -> float:
    match = re.search(r"frame_(\d+)\.jpg$", frame_path.name)
    if not match:
        return 0.0
    try:
        index = int(match.group(1))
        return (index - 1) * interval_seconds
    except ValueError:
        return 0.0


def _tesseract_available() -> bool:
    if pytesseract is None:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _easyocr_available() -> bool:
    return easyocr is not None


def _load_easyocr_reader() -> Optional[object]:
    global _easyocr_reader
    if _easyocr_reader is None and easyocr is not None:
        try:
            _easyocr_reader = easyocr.Reader(["fr", "en"], gpu=False)
        except Exception:
            _easyocr_reader = None
    return _easyocr_reader


def _preprocess_image(image: "Image.Image") -> "Image.Image":
    gray = image.convert("L")
    if ImageOps is not None:
        gray = ImageOps.autocontrast(gray)
    if ImageEnhance is not None:
        gray = ImageEnhance.Sharpness(gray).enhance(1.5)
    return gray


def _extract_ocr_text(frame_path: Path) -> str:
    if Image is None:
        return ""

    try:
        image = Image.open(frame_path)
        processed = _preprocess_image(image)
    except Exception:
        return ""

    if _tesseract_available():
        try:
            return pytesseract.image_to_string(processed, lang="fra+eng").strip()
        except Exception:
            pass

    if _easyocr_available():
        reader = _load_easyocr_reader()
        if reader is not None:
            try:
                results = reader.readtext(str(frame_path), detail=0, paragraph=True)
                return "\n".join(results).strip()
            except Exception:
                pass

    return ""


def extract_ocr_from_frames(frame_dir: Path, interval_seconds: int = 20) -> List[Dict[str, object]]:
    """Extract OCR and visual labels from keyframe images."""
    if not frame_dir.is_dir():
        return []

    results: List[Dict[str, object]] = []
    for frame in sorted(frame_dir.glob("*.jpg")):
        frame_time = _parse_frame_time(frame, interval_seconds)
        ocr_text = _extract_ocr_text(frame)
        visual_label = "slide_or_screen_text" if ocr_text else "reference_frame"

        results.append(
            {
                "frame": str(frame),
                "frame_time": frame_time,
                "ocr_text": ocr_text,
                "visual_label": visual_label,
            }
        )
    return results
