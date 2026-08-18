"""Sprint 1 orchestrator: video in -> list[Scene] (multimodal representation) out.

Pipeline (cahier des charges, section 7 / figure 1 - ingestion half):
  video -> audio extraction -> ASR transcription
        -> visual scene detection -> representative frame per scene -> OCR
  -> merge into Scene objects, keyed on visual scene boundaries, each carrying
     the transcript text and speaker(s) that overlap that time window.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tqdm import tqdm

from . import audio, diarization, ocr, scenes, transcription
from .models import Scene, TranscriptSegment


def _overlapping_transcript(
    segments: list[TranscriptSegment], start: float, end: float
) -> tuple[str, list[TranscriptSegment]]:
    overlapping = [seg for seg in segments if seg.start < end and seg.end > start]
    text = " ".join(seg.text for seg in overlapping).strip()
    return text, overlapping


def _majority_speaker(segments: list[TranscriptSegment]) -> str | None:
    labelled = [seg.speaker for seg in segments if seg.speaker]
    if not labelled:
        return None
    return max(set(labelled), key=labelled.count)


def run(video_path: Path, work_dir: Path) -> list[Scene]:
    frames_dir = work_dir / "frames"
    audio_path = work_dir / "audio.wav"
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] Extracting audio from {video_path.name} ...")
    audio.extract_audio(video_path, audio_path)

    print("[2/5] Transcribing audio (faster-whisper, CPU) ...")
    transcript_segments = transcription.transcribe(audio_path)
    print(f"      -> {len(transcript_segments)} transcript segments")

    print("[3/5] Diarizing speakers ...")
    speaker_turns = diarization.diarize(audio_path)
    if speaker_turns:
        for seg in transcript_segments:
            midpoint = (seg.start + seg.end) / 2
            seg.speaker = diarization.speaker_at(speaker_turns, midpoint)
        print(f"      -> {len(speaker_turns)} speaker turns")
    else:
        print("      -> no diarization available, using single-speaker fallback")

    print("[4/5] Detecting visual scene boundaries ...")
    visual_scenes = scenes.detect_scenes(video_path)
    print(f"      -> {len(visual_scenes)} visual scenes")

    print("[5/5] Extracting representative frames + running OCR ...")
    result: list[Scene] = []
    for i, vscene in enumerate(tqdm(visual_scenes)):
        scene_id = f"scene_{i:03d}"
        midpoint = (vscene.start + vscene.end) / 2
        frame_path = frames_dir / f"{scene_id}.jpg"
        scenes.extract_frame(video_path, midpoint, frame_path)
        ocr_text = ocr.extract_text(frame_path)

        transcript_text, overlapping = _overlapping_transcript(
            transcript_segments, vscene.start, vscene.end
        )
        speaker = _majority_speaker(overlapping)

        result.append(
            Scene(
                id=scene_id,
                start=vscene.start,
                end=vscene.end,
                speaker=speaker,
                transcript=transcript_text,
                ocr_text=ocr_text,
                frame_path=str(frame_path),
            )
        )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="S2M Sprint 1 ingestion pipeline")
    parser.add_argument("--video", required=True, type=Path, help="Path to the source video")
    parser.add_argument(
        "--output", type=Path, default=Path("output/scenes.json"), help="Output JSON path"
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Working directory for intermediate files (audio, frames). "
        "Defaults to output/<video_stem>/",
    )
    args = parser.parse_args()

    work_dir = args.work_dir or (args.output.parent / args.video.stem)
    scenes_result = run(args.video, work_dir)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump([s.model_dump() for s in scenes_result], f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(scenes_result)} scenes written to {args.output}")


if __name__ == "__main__":
    main()
