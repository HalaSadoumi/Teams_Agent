"""Shared data models for the AI transformation pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AudioTranscriptSegment:
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Scene:
    id: str
    start: float
    end: float
    transcript: str
    speaker: Optional[str] = None
    ocr_text: str = ""
    visual_description: str = ""
    topic: Optional[str] = None
    importance: float = 0.0
    keyframes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Chapter:
    id: str
    title: str
    start: float
    end: float
    summary: str = ""
    key_points: List[str] = field(default_factory=list)
    scenes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TransformedScene:
    scene_id: str
    chapter_id: str
    narration: str
    visual_type: str
    visual_description: str
    on_screen_text: str
    transition: str = "fade"
    tts_audio: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CoursePackage:
    source_video: str
    source_audio: str
    transcript: str
    enhanced_audio: Optional[str] = None
    assembled_video: Optional[str] = None
    chapters: List[Chapter] = field(default_factory=list)
    scenes: List[Scene] = field(default_factory=list)
    storyboard: List[TransformedScene] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "source_video": self.source_video,
            "source_audio": self.source_audio,
            "transcript": self.transcript,
            "chapters": [chapter.to_dict() for chapter in self.chapters],
            "scenes": [scene.to_dict() for scene in self.scenes],
            "storyboard": [scene.to_dict() for scene in self.storyboard],
        }
        if self.enhanced_audio is not None:
            data["enhanced_audio"] = self.enhanced_audio
        if self.assembled_video is not None:
            data["assembled_video"] = self.assembled_video
        return data

    def save_json(self, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
