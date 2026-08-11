"""Generate chapter boundaries and metadata from scenes."""

from typing import List

from .model import Chapter, Scene


def _format_chapter_title(index: int, scene: Scene) -> str:
    if scene.ocr_text:
        headline = scene.ocr_text.splitlines()[0].strip()
        if 3 <= len(headline.split()) <= 12:
            return headline
    return f"Chapter {index:02d}"


def detect_chapters(scenes: List[Scene], chapter_duration: int = 300) -> List[Chapter]:
    """Create an initial chapter structure from the scene timeline."""
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
