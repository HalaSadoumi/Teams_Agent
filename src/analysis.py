"""Analyze multimodal inputs and build structured scenes."""

from pathlib import Path
from typing import Dict, List

from .model import AudioTranscriptSegment, Scene
from .nlp_utils import extract_keywords, merge_keywords, topic_similarity


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


def _split_bucket_by_topic(
    bucket: List[AudioTranscriptSegment],
    min_scene_duration: float = 60.0,
    max_scene_duration: float = 300.0,
    similarity_threshold: float = 0.25,
) -> List[List[AudioTranscriptSegment]]:
    if len(bucket) < 3:
        return [bucket]

    groups: List[List[AudioTranscriptSegment]] = []
    current_group: List[AudioTranscriptSegment] = [bucket[0]]
    current_keywords = extract_keywords(bucket[0].text)
    group_start = bucket[0].start

    for segment in bucket[1:]:
        segment_keywords = extract_keywords(segment.text)
        similarity = topic_similarity(current_keywords, segment_keywords)
        elapsed = segment.end - group_start

        if elapsed >= max_scene_duration or (elapsed >= min_scene_duration and similarity < similarity_threshold):
            groups.append(current_group)
            current_group = [segment]
            current_keywords = segment_keywords
            group_start = segment.start
        else:
            current_group.append(segment)
            if segment_keywords:
                current_keywords = merge_keywords(current_keywords, segment_keywords)

    if current_group:
        groups.append(current_group)

    return groups


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
            for split_bucket in _split_bucket_by_topic(bucket):
                scenes.append(_scene_from_bucket(scene_index, split_bucket, ocr_frames, interval_seconds))
                scene_index += 1
            bucket = []
        bucket.append(segment)

    if bucket:
        for split_bucket in _split_bucket_by_topic(bucket):
            scenes.append(_scene_from_bucket(scene_index, split_bucket, ocr_frames, interval_seconds))
            scene_index += 1

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

    keywords = extract_keywords(transcript + " " + ocr_text)
    topic = keywords[0] if keywords else None

    return Scene(
        id=f"scene_{index:03d}",
        start=start,
        end=end,
        transcript=transcript,
        speaker=bucket[0].speaker,
        ocr_text=ocr_text,
        visual_description=visual_description,
        topic=topic,
        importance=0.0,
        keyframes=keyframes,
    )
