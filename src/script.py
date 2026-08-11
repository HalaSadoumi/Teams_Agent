"""Generate clean educational narration from transcript segments."""

from typing import List

from .model import AudioTranscriptSegment, Chapter, Scene


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
    rewritten: List[Scene] = []
    for scene in scenes:
        narration = scene.transcript.replace("uh", "").replace("um", "").strip()
        rewritten.append(
            Scene(
                id=scene.id,
                start=scene.start,
                end=scene.end,
                transcript=narration,
                speaker=scene.speaker,
                ocr_text=scene.ocr_text,
                visual_description=scene.visual_description,
                topic=scene.topic,
                importance=scene.importance,
                keyframes=scene.keyframes,
            )
        )
    return rewritten
