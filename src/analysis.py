"""Analyze multimodal inputs and build structured scenes."""

from typing import Dict, List
from pathlib import Path

from .model import AudioTranscriptSegment, Scene


def _parse_frame_time(frame_path: Path, interval_seconds: int) -> float:
    name = frame_path.stem
    if name.startswith("frame_"):
        try:
            index = int(name.split("_")[-1])
            return (index - 1) * interval_seconds
        except ValueError:
            return 0.0
    return 0.0


def _select_frame_for_time(frames: List[Dict[str, object]], reference_time: float) -> Dict[str, object]:
    if not frames:
        return {"frame": "", "frame_time": 0.0, "ocr_text": "", "visual_label": "reference_frame"}
    return min(frames, key=lambda item: abs(float(item.get("frame_time", 0.0)) - reference_time))


def build_scenes(
    segments: List[AudioTranscriptSegment],
    ocr_frames: List[Dict[str, object]],
    interval_seconds: int = 20,
    max_gap_seconds: float = 10.0,
) -> List[Scene]:
    """Build scene objects by grouping segments and attaching OCR/visual context."""
    if not segments:
        return []

    scenes: List[Scene] = []
    bucket: List[AudioTranscriptSegment] = []
    scene_index = 1

    for segment in segments:
        if bucket and segment.start - bucket[-1].end > max_gap_seconds:
            scenes.append(_scene_from_bucket(scene_index, bucket, ocr_frames, interval_seconds))
            scene_index += 1
            bucket = []
        bucket.append(segment)

    if bucket:
        scenes.append(_scene_from_bucket(scene_index, bucket, ocr_frames, interval_seconds))

    return scenes


def _scene_from_bucket(
    index: int,
    bucket: List[AudioTranscriptSegment],
    ocr_frames: List[Dict[str, object]],
    interval_seconds: int,
) -> Scene:
    start = bucket[0].start
    end = bucket[-1].end
    transcript = " ".join(segment.text for segment in bucket).strip()
    mid_time = (start + end) / 2
    frame = _select_frame_for_time(ocr_frames, mid_time)
    ocr_text = str(frame.get("ocr_text", "")).strip()
    visual_description = str(frame.get("visual_label", "reference_frame")).strip()
    keyframes = [str(frame.get("frame", ""))] if frame.get("frame") else []

    if not visual_description and ocr_text:
        visual_description = "Slide or screen content captured in the reference frame."

    return Scene(
        id=f"scene_{index:03d}",
        start=start,
        end=end,
        transcript=transcript,
        speaker=bucket[0].speaker,
        ocr_text=ocr_text,
        visual_description=visual_description,
        topic=None,
        importance=0.0,
        keyframes=keyframes,
    )
