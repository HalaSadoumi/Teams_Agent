"""Orchestrator for the AI-powered training transformation pipeline."""

import argparse
from pathlib import Path
from typing import List

from .analysis import build_scenes
from .asr import transcribe_audio
from .audio_enhancement import enhance_audio
from .assemble import assemble_course
from .chapterize import detect_chapters
from .ingest import extract_audio, extract_keyframes, normalize_video_path
from .model import CoursePackage
from .ocr import extract_ocr_from_frames
from .script import rewrite_script
from .storyboard import generate_storyboard, save_storyboard


def build_course_package(
    video_path: Path,
    output_dir: Path,
    sample_rate: int = 48000,
    keyframe_interval_seconds: int = 20,
    chapter_duration: int = 300,
) -> CoursePackage:
    video_path = normalize_video_path(video_path)
    audio_path = output_dir / "audio" / "audio.wav"
    extract_audio(video_path, audio_path, sample_rate=sample_rate)
    enhanced_audio_dir = output_dir / "enhanced_audio"
    enhanced_audio_path = enhance_audio(audio_path, enhanced_audio_dir)
    extract_keyframes(video_path, output_dir / "keyframes", interval_seconds=keyframe_interval_seconds)

    transcript_segments = transcribe_audio(enhanced_audio_path, output_dir / "transcript")
    ocr_results = extract_ocr_from_frames(output_dir / "keyframes", interval_seconds=keyframe_interval_seconds)
    scenes = build_scenes(transcript_segments, ocr_results, interval_seconds=keyframe_interval_seconds)

    chapters = detect_chapters(scenes, chapter_duration=chapter_duration)
    scenes = rewrite_script(chapters, scenes)
    storyboard = generate_storyboard(chapters, scenes)

    output_video_path = output_dir / "final_course.mp4"
    package = CoursePackage(
        source_video=str(video_path),
        source_audio=str(audio_path),
        enhanced_audio=str(enhanced_audio_path),
        assembled_video=str(output_video_path),
        transcript=str(output_dir / "transcript" / "transcript.json"),
        chapters=chapters,
        scenes=scenes,
        storyboard=storyboard,
    )

    assemble_course(
        source_video=video_path,
        narration_audio=enhanced_audio_path,
        captions_path=output_dir / "transcript" / "captions.srt",
        output_video=output_video_path,
    )

    package.save_json(output_dir / "course_package.json")
    return package


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI training transformation pipeline.")
    parser.add_argument("video", type=Path, help="Path to the input training video.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"), help="Directory for pipeline artifacts.")
    parser.add_argument("--chapter-duration", type=int, default=300, help="Fallback chapter length in seconds.")
    parser.add_argument("--keyframe-interval", type=int, default=20, help="Seconds between extracted keyframes.")
    args = parser.parse_args()

    package = build_course_package(
        args.video,
        args.output_dir,
        keyframe_interval_seconds=args.keyframe_interval,
        chapter_duration=args.chapter_duration,
    )

    storyboard_path = args.output_dir / "storyboard.json"
    save_storyboard(package.storyboard, storyboard_path)
    print(f"Course package created: {args.output_dir / 'course_package.json'}")
    print(f"Storyboard saved: {storyboard_path}")


if __name__ == "__main__":
    main()
