"""Create a structured storyboard from chapters and scenes."""

import json
from pathlib import Path
from typing import List

from .model import Chapter, Scene, TransformedScene
from .nlp_utils import extract_keywords


def _summarize_text(text: str, max_words: int = 10) -> str:
    words = [word for word in text.replace("\n", " ").split() if word]
    return " ".join(words[:max_words]).strip()


def _choose_visual_type(scene: Scene) -> str:
    text = " ".join([scene.ocr_text, scene.topic or "", scene.transcript]).lower()
    if any(keyword in text for keyword in ["process", "flow", "transaction", "flux", "schéma", "diagramme"]):
        return "animated_diagram"
    if any(keyword in text for keyword in ["carte", "terminal", "paiement", "autorisation", "TPE"]):
        return "process_flow"
    if any(keyword in text for keyword in ["slide", "diapositive", "écran", "écran", "gros"]):
        return "slide_graphic"
    if any(keyword in text for keyword in ["question", "conclusion", "résumé", "prise de décision"]):
        return "bullet_summary"
    return "concept_card"


def _describe_visual(scene: Scene, keywords: List[str]) -> str:
    if scene.ocr_text:
        return "Present the slide or screen text visually while emphasizing the key points."
    if scene.topic:
        return f"Visualize the concept of {scene.topic} with supporting icons and diagrams."
    if keywords:
        return f"Use animated visuals to highlight {', '.join(keywords[:3])}."
    return "Create an engaging course visual that supports the narration."


def generate_storyboard(chapters: List[Chapter], scenes: List[Scene]) -> List[TransformedScene]:
    storyboard: List[TransformedScene] = []
    chapter_lookup = {chapter.id: chapter for chapter in chapters}

    for scene in scenes:
        chapter_id = "chapter_01"
        for chapter in chapters:
            if chapter.start <= scene.start < chapter.end:
                chapter_id = chapter.id
                break

        keywords = extract_keywords(scene.transcript + " " + scene.ocr_text)
        visual_type = _choose_visual_type(scene)
        on_screen_text = _summarize_text(scene.ocr_text or scene.transcript, max_words=12)
        if not on_screen_text:
            on_screen_text = f"Key concepts: {', '.join(keywords[:3])}" if keywords else ""

        storyboard.append(
            TransformedScene(
                scene_id=scene.id,
                chapter_id=chapter_id,
                narration=scene.transcript,
                visual_type=visual_type,
                visual_description=_describe_visual(scene, keywords),
                on_screen_text=on_screen_text,
                transition="fade" if scene.start == chapter_lookup[chapter_id].start else "slide",
            )
        )
    return storyboard


def save_storyboard(storyboard: List[TransformedScene], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [scene.to_dict() for scene in storyboard]
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path
