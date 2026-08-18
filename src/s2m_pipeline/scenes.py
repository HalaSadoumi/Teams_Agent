"""Visual scene boundary detection (PySceneDetect) and representative frame extraction."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from scenedetect import ContentDetector, SceneManager, open_video

from .config import settings


@dataclass
class VisualScene:
    start: float
    end: float


def detect_scenes(video_path: Path) -> list[VisualScene]:
    """Detect visual scene boundaries via content-based shot change detection.

    Falls back to a single whole-video scene if no cuts are detected (e.g. a
    single static screen-share for the entire recording).
    """
    video = open_video(str(video_path))
    scene_manager = SceneManager()
    scene_manager.add_detector(
        ContentDetector(
            threshold=settings.scene_detect_threshold,
            min_scene_len=int(settings.min_scene_len_seconds * video.frame_rate),
        )
    )
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()

    if not scene_list:
        duration = video.duration.get_seconds()
        return [VisualScene(start=0.0, end=duration)]

    return [
        VisualScene(start=start.get_seconds(), end=end.get_seconds())
        for start, end in scene_list
    ]


def extract_frame(video_path: Path, timestamp: float, output_path: Path) -> Path:
    """Extract a single representative frame at `timestamp` seconds."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(timestamp),
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed:\n{result.stderr}")

    return output_path
