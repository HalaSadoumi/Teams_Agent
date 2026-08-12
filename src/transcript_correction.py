"""Correct ASR errors using OCR context and domain vocabulary."""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set

from .model import AudioTranscriptSegment

COMMON_REPLACEMENTS = {
    "teh": "the",
    "adn": "and",
    "hte": "the",
    "taht": "that",
    "whith": "with",
    "wich": "which",
    "becaus": "because",
    "securité": "sécurité",
    "securite": "sécurité",
    "données": "données",
    "donnees": "données",
}


def _normalize_token(token: str) -> str:
    return re.sub(r"[^\w'-]", "", token).strip("'-").lower()


def _extract_ocr_vocabulary(ocr_results: Sequence[Dict[str, object]]) -> Set[str]:
    vocabulary: Set[str] = set()
    for frame in ocr_results:
        text = str(frame.get("ocr_text", "")).strip()
        if not text:
            continue
        for line in text.splitlines():
            line = line.strip()
            if len(line) >= 3:
                vocabulary.add(line)
            for token in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9][A-Za-zÀ-ÖØ-öø-ÿ0-9'-]{2,}", line):
                vocabulary.add(token)
                vocabulary.add(token.lower())
    return vocabulary


def build_initial_prompt(ocr_results: Sequence[Dict[str, object]], max_terms: int = 120) -> str:
    """Build a Whisper initial prompt from OCR slide/screen vocabulary."""
    terms = sorted(_extract_ocr_vocabulary(ocr_results), key=len, reverse=True)
    selected = terms[:max_terms]
    if not selected:
        return "Formation professionnelle, présentation, cours e-learning."
    return " ".join(selected)


def _best_ocr_match(word: str, vocabulary: Set[str], cutoff: float = 0.78) -> str | None:
    clean = _normalize_token(word)
    if not clean or len(clean) < 4 or clean in vocabulary:
        return None

    candidates = sorted({term for term in vocabulary if len(term) >= 3})
    matches = difflib.get_close_matches(clean, candidates, n=1, cutoff=cutoff)
    if matches:
        return matches[0]

    lower_map = {term.lower(): term for term in candidates}
    matches = difflib.get_close_matches(clean, list(lower_map), n=1, cutoff=cutoff)
    if matches:
        return lower_map[matches[0]]
    return None


def _correct_word(word: str, vocabulary: Set[str]) -> str:
    match = re.match(r"^([^\w'-]*)([\w'-]+)([^\w'-]*)$", word)
    if not match:
        return word

    prefix, bare, suffix = match.groups()
    normalized = _normalize_token(bare)
    replacement = COMMON_REPLACEMENTS.get(normalized, bare)
    ocr_match = _best_ocr_match(replacement, vocabulary)
    if ocr_match:
        replacement = ocr_match
    return f"{prefix}{replacement}{suffix}"


def _correct_text(text: str, vocabulary: Set[str]) -> str:
    if not text.strip():
        return text
    corrected = " ".join(_correct_word(word, vocabulary) for word in text.split())
    return re.sub(r"\s+", " ", corrected).strip()


def correct_transcript_segments(
    segments: List[AudioTranscriptSegment],
    ocr_results: Sequence[Dict[str, object]],
) -> List[AudioTranscriptSegment]:
    """Apply OCR-aware corrections to transcript segments."""
    vocabulary = _extract_ocr_vocabulary(ocr_results)
    return [
        AudioTranscriptSegment(
            start=segment.start,
            end=segment.end,
            text=_correct_text(segment.text, vocabulary),
            speaker=segment.speaker,
            tags=list(segment.tags),
        )
        for segment in segments
    ]


def save_transcript_json(
    segments: Iterable[AudioTranscriptSegment],
    destination: Path,
    *,
    source_audio: str,
    language: str,
    language_probability: float,
    corrected: bool = False,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_audio": source_audio,
        "language": language,
        "language_probability": round(language_probability, 4),
        "corrected": corrected,
        "segments": [
            {
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
                "text": segment.text.strip(),
            }
            for segment in segments
        ],
    }
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
