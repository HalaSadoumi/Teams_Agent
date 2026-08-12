"""Generate clean educational narration from transcript segments."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from .model import Chapter, Scene
from .nlp_utils import extract_keywords

FILLER_WORDS = {
    "uh", "um", "eh", "euh", "bon", "alors", "genre", "vous savez", "en fait",
    "donc", "voilà", "d'accord", "quoi", "hein", "c'est", "tu vois", "je veux dire",
    "you know", "like", "basically", "actually", "sort of", "kind of",
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
        if slide_tips and slide_tips.lower() not in narration.lower():
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


def rewrite_script(chapters: List[Chapter], scenes: List[Scene]) -> List[Scene]:
    """Rewrite raw scene transcripts into a cleaner course narration draft."""
    return [_rewrite_scene(scene) for scene in scenes]


def export_chapter_scripts(chapters: List[Chapter], scenes: List[Scene], output_dir: Path) -> Path:
    """Write one narration text file per detected chapter."""
    output_dir.mkdir(parents=True, exist_ok=True)
    scene_lookup = {scene.id: scene for scene in scenes}

    for chapter in chapters:
        chapter_scenes = [scene_lookup[scene_id] for scene_id in chapter.scenes if scene_id in scene_lookup]
        narration = "\n\n".join(scene.transcript for scene in chapter_scenes if scene.transcript.strip())
        script_path = output_dir / f"{chapter.id}_narration.txt"
        script_path.write_text(f"{chapter.title}\n\n{narration}\n", encoding="utf-8")

    return output_dir
