"""Generate chapter boundaries and metadata from scenes."""

from collections import Counter
from typing import List, Optional

from .model import Chapter, Scene
from .nlp_utils import extract_keywords, merge_keywords, topic_similarity


def _format_chapter_title(index: int, scene: Scene, keywords: Optional[List[str]] = None) -> str:
    if scene.ocr_text:
        headline = scene.ocr_text.splitlines()[0].strip()
        if 3 <= len(headline.split()) <= 12:
            return headline

    if keywords:
        candidate = " · ".join(keyword.capitalize() for keyword in keywords[:3])
        if len(candidate.split()) <= 6:
            return candidate

    return f"Chapter {index:02d}"


def _build_chapter(chapter_index: int, scenes: List[Scene]) -> Chapter:
    first_scene = scenes[0]
    keywords = extract_keywords(first_scene.transcript + " " + first_scene.ocr_text)
    title = _format_chapter_title(chapter_index, first_scene, keywords)
    summary = (
        f"Covers {title.lower()}." if first_scene.ocr_text else "Contains the next segment of the transformed course."
    )
    return Chapter(
        id=f"chapter_{chapter_index:02d}",
        title=title,
        start=first_scene.start,
        end=scenes[-1].end,
        summary=summary,
        key_points=keywords[:5],
        scenes=[scene.id for scene in scenes],
    )


def _semantic_chapters(scenes: List[Scene], chapter_duration: int) -> List[Chapter]:
    chapters: List[Chapter] = []
    if not scenes:
        return chapters

    current_scenes: List[Scene] = [scenes[0]]
    current_keywords = extract_keywords(scenes[0].transcript + " " + scenes[0].ocr_text)
    current_start = scenes[0].start
    chapter_index = 1

    for scene in scenes[1:]:
        scene_keywords = extract_keywords(scene.transcript + " " + scene.ocr_text)
        similarity = topic_similarity(current_keywords, scene_keywords)
        elapsed = scene.end - current_start

        if (elapsed >= chapter_duration and similarity < 0.25) or elapsed >= chapter_duration * 1.5:
            chapters.append(_build_chapter(chapter_index, current_scenes))
            chapter_index += 1
            current_scenes = [scene]
            current_keywords = scene_keywords
            current_start = scene.start
        else:
            current_scenes.append(scene)
            if scene_keywords:
                current_keywords = merge_keywords(current_keywords, scene_keywords)

    if current_scenes:
        chapters.append(_build_chapter(chapter_index, current_scenes))

    return chapters


def detect_chapters(scenes: List[Scene], chapter_duration: int = 300, semantic: bool = True) -> List[Chapter]:
    """Create chapter structure by grouping scenes with similar topics."""
    if semantic:
        return _semantic_chapters(scenes, chapter_duration)

    chapters: List[Chapter] = []
    if not scenes:
        return chapters

    current_start = scenes[0].start
    current_scenes: List[Scene] = []
    chapter_index = 1

    for scene in scenes:
        current_scenes.append(scene)
        if scene.end - current_start >= chapter_duration:
            title = _format_chapter_title(chapter_index, current_scenes[0])
            summary = "Contains the next segment of the transformed course." \
                if not scene.ocr_text else f"Covers {title.lower()}."
            chapters.append(
                Chapter(
                    id=f"chapter_{chapter_index:02d}",
                    title=title,
                    start=current_start,
                    end=scene.end,
                    summary=summary,
                    key_points=[],
                    scenes=[item.id for item in current_scenes],
                )
            )
            chapter_index += 1
            current_start = scene.end
            current_scenes = []

    if current_scenes:
        title = _format_chapter_title(chapter_index, current_scenes[0])
        summary = "Final section of the transformed course." \
            if not current_scenes[0].ocr_text else f"Final section covering {title.lower()}."
        chapters.append(
            Chapter(
                id=f"chapter_{chapter_index:02d}",
                title=title,
                start=current_start,
                end=current_scenes[-1].end,
                summary=summary,
                key_points=[],
                scenes=[item.id for item in current_scenes],
            )
        )

    return chapters
