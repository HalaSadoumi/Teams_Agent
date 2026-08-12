"""Orchestrator for the AI-powered training transformation pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from .analysis import build_scenes
from .asr import transcribe_audio
from .audio_enhancement import enhance_audio, generate_asr_version
from .assemble import assemble_course
from .chapterize import detect_chapters
from .export_subtitles import export_srt
from .ingest import extract_audio, extract_keyframes, normalize_video_path
from .model import CoursePackage
from .ocr import extract_ocr_from_frames
from .script import export_chapter_scripts, rewrite_script
from .storyboard import generate_storyboard, save_storyboard
from .transcript_correction import (
    build_initial_prompt,
    correct_transcript_segments,
    save_transcript_json,
)


def build_course_package(
    video_path: Path,
    output_dir: Path,
    sample_rate: int = 48000,
    keyframe_interval_seconds: int = 20,
    chapter_duration: int = 300,
    model_size: str = "medium",
    language: Optional[str] = None,
    denoise: bool = True,
) -> CoursePackage:
    video_path = normalize_video_path(video_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_path = output_dir / "audio" / "audio.wav"
    extract_audio(video_path, audio_path, sample_rate=sample_rate)

    enhanced_audio_dir = output_dir / "enhanced_audio"
    enhanced_audio_path = enhance_audio(audio_path, enhanced_audio_dir, denoise=denoise)

    keyframes_dir = output_dir / "keyframes"
    extract_keyframes(video_path, keyframes_dir, interval_seconds=keyframe_interval_seconds)

    ocr_results = extract_ocr_from_frames(keyframes_dir, interval_seconds=keyframe_interval_seconds)
    initial_prompt = build_initial_prompt(ocr_results)

    asr_audio_dir = output_dir / "asr_audio"
    asr_audio_path = generate_asr_version(enhanced_audio_path, asr_audio_dir)

    transcript_dir = output_dir / "transcript"
    transcription = transcribe_audio(
        asr_audio_path,
        transcript_dir,
        model_size=model_size,
        language=language,
        initial_prompt=initial_prompt,
    )

    corrected_segments = correct_transcript_segments(transcription.segments, ocr_results)
    corrected_json = transcript_dir / "transcript_corrected.json"
    save_transcript_json(
        corrected_segments,
        corrected_json,
        source_audio=str(asr_audio_path),
        language=transcription.language,
        language_probability=transcription.language_probability,
        corrected=True,
    )
    export_srt(corrected_json, transcript_dir / "captions_corrected.srt")
    (transcript_dir / "transcript_corrected.txt").write_text(
        "\n".join(
            f"[{segment.start:08.2f} - {segment.end:08.2f}] {segment.text}"
            for segment in corrected_segments
        ),
        encoding="utf-8",
    )

    scenes = build_scenes(
        corrected_segments,
        ocr_results,
        interval_seconds=keyframe_interval_seconds,
    )
    chapters = detect_chapters(scenes, chapter_duration=chapter_duration)
    scenes = rewrite_script(chapters, scenes)
    storyboard = generate_storyboard(chapters, scenes)
    export_chapter_scripts(chapters, scenes, output_dir / "scripts")

    output_video_path = output_dir / "final_course.mp4"
    package = CoursePackage(
        source_video=str(video_path),
        source_audio=str(audio_path),
        enhanced_audio=str(enhanced_audio_path),
        audio_asr=str(asr_audio_path),
        assembled_video=str(output_video_path),
        transcript=str(corrected_json),
        chapters=chapters,
        scenes=scenes,
        storyboard=storyboard,
    )

    assemble_course(
        source_video=video_path,
        narration_audio=enhanced_audio_path,
        captions_path=transcript_dir / "captions_corrected.srt",
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
    parser.add_argument("--model", default="medium", help="Whisper model size (tiny, base, small, medium, large-v3).")
    parser.add_argument("--language", default=None, help="Force transcription language (fr, en). Auto-detect if omitted.")
    parser.add_argument("--no-denoise", action="store_true", help="Skip denoising and only normalize audio.")
    args = parser.parse_args()

    package = build_course_package(
        args.video,
        args.output_dir,
        keyframe_interval_seconds=args.keyframe_interval,
        chapter_duration=args.chapter_duration,
        model_size=args.model,
        language=args.language,
        denoise=not args.no_denoise,
    )

    storyboard_path = args.output_dir / "storyboard.json"
    save_storyboard(package.storyboard, storyboard_path)
    print(f"Course package created: {args.output_dir / 'course_package.json'}")
    print(f"Corrected subtitles: {args.output_dir / 'transcript' / 'captions_corrected.srt'}")
    print(f"Chapter scripts: {args.output_dir / 'scripts'}")
    print(f"Final video: {args.output_dir / 'final_course.mp4'}")
    print(f"Storyboard saved: {storyboard_path}")


if __name__ == "__main__":
    main()
