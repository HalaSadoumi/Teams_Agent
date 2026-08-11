"""Generate clean educational narration from transcript segments."""

import re
from typing import List

from .model import AudioTranscriptSegment, Chapter, Scene
from .nlp_utils import extract_keywords


FILLER_WORDS = {
    "uh", "um", "eh", "euh", "bon", "alors", "genre", "vous savez", "en fait",
    "donc", "voilà", "d'accord", "quoi", "hein", "c'est", "tu vois", "je veux dire",
}


def _clean_text(text: str) -> str:
    normalized = re.sub(r"[\r\n]+", " ", text)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    filler_pattern = r"\b(" + r"|".join(re.escape(word) for word in sorted(FILLER_WORDS, key=len, reverse=True)) + r")[,;:]*\b"
    cleaned = re.sub(filler_pattern, "", normalized, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    cleaned = re.sub(r"\b(\w+)\s+\1\b", r"\1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+([?.!,;:])", r"\1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"^\W+", "", cleaned)
    return cleaned


def _rewrite_scene(scene: Scene) -> Scene:
    narration = _clean_text(scene.transcript)
    if scene.ocr_text:
        slide_tips = _clean_text(scene.ocr_text)
        if slide_tips and slide_tips not in narration:
            narration = f"{narration} {slide_tips}"

    topic_keywords = extract_keywords(scene.transcript + " " + scene.ocr_text)
    topic = scene.topic or (topic_keywords[0] if topic_keywords else None)

    return Scene(
        id=scene.id,
        start=scene.start,
        end=scene.end,
        transcript=narration,
        speaker=scene.speaker,
        ocr_text=scene.ocr_text,
        visual_description=scene.visual_description,
        topic=topic,
        importance=scene.importance,
        keyframes=scene.keyframes,
    )


def create_narration_from_segments(segments: List[AudioTranscriptSegment]) -> List[Scene]:
    """Convert transcript segments into scene placeholders for script transformation."""
    scenes: List[Scene] = []
    for index, segment in enumerate(segments, start=1):
        scenes.append(
            Scene(
                id=f"scene_{index:03d}",
                start=segment.start,
                end=segment.end,
                transcript=segment.text,
                speaker=segment.speaker,
                ocr_text="",
                visual_description="",
                topic=None,
                importance=0.0,
                keyframes=[],
            )
        )
    return scenes


def rewrite_script(chapters: List[Chapter], scenes: List[Scene]) -> List[Scene]:
    """Rewrite raw scene transcripts into a cleaner course narration draft."""
    return [_rewrite_scene(scene) for scene in scenes]
