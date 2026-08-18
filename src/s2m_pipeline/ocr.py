"""OCR of on-screen text (slides, shared screens) via Tesseract."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytesseract
from PIL import Image

from .config import PROJECT_ROOT

# On Windows, a fresh shell may not have PATH updated right after a winget
# install. Fall back to the default UB-Mannheim install location if the
# `tesseract` binary isn't already resolvable.
if shutil.which("tesseract") is None:
    _default_win_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if _default_win_path.exists():
        pytesseract.pytesseract.tesseract_cmd = str(_default_win_path)

# The stock Windows install only ships the English language pack. French is
# required (bilingual FR/EN support, cahier des charges section 10), so a
# project-local tessdata dir with fra.traineddata + eng.traineddata is used
# instead of the system one (see README for how it's populated).
_local_tessdata = PROJECT_ROOT / ".tessdata"
if _local_tessdata.exists():
    os.environ["TESSDATA_PREFIX"] = str(_local_tessdata)


def extract_text(frame_path: Path, lang: str = "fra+eng") -> str:
    """Run OCR on a single frame image, returning cleaned text."""
    image = Image.open(frame_path)
    text = pytesseract.image_to_string(image, lang=lang)
    return text.strip()
