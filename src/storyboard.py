"""Create a structured storyboard from chapters and scenes."""

import json
from pathlib import Path
from typing import List

from .model import Chapter, Scene, TransformedScene


def generate_storyboard(chapters: List[Chapter], scenes: List[Scene]) -> List[TransformedScene]:
    storyboard: List[TransformedScene] = []
    for scene in scenes:
        chapter_index = 1
        for chapter in chapters:
            if chapter.start <= scene.start < chapter.end:
                chapter_index = int(chapter.id.split("_")[-1])
                break

        storyboard.append(
            TransformedScene(
                scene_id=scene.id,
                chapter_id=f"chapter_{chapter_index:02d}",
                narration=scene.transcript,
                visual_type="slide_or_screencast",
                visual_description="Use the original visual context as a reference and replace it with course-friendly graphics.",
                on_screen_text="".join(scene.transcript.split()[:8]),
            )
        )
    return storyboard


def save_storyboard(storyboard: List[TransformedScene], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [scene.to_dict() for scene in storyboard]
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path
