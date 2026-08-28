"""Sprint 2: semantic comprehension + automatic chaptering.

Cahier des charges section 5.3: chapter boundaries must come from semantic
rupture (topic change), not from time or visual cuts. Sprint 1 confirmed why
visual cuts alone can't do it: on the real training video, a single visual
scene ran uninterrupted for over 30 minutes while the topic clearly moved on.

Approach (matches the tech stack table, section 9):
  1. Group the fine-grained ASR transcript into fixed-duration windows.
  2. Embed each window (Sentence-Transformers) and flag windows whose
     similarity to the previous window drops below a threshold as
     candidate chapter starts.
  3. Merge candidate chapters that end up too short (noisy boundaries).
  4. For each resulting chapter, call Gemini with the transcript excerpt,
     OCR text, and representative frame(s) to generate a title, summary,
     and key points.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

from . import embeddings, llm
from .config import settings
from .models import Chapter, Scene, TranscriptSegment


@dataclass
class _Window:
    start: float
    end: float
    text: str


def _group_into_windows(
    segments: list[TranscriptSegment], window_seconds: float
) -> list[_Window]:
    if not segments:
        return []

    windows: list[_Window] = []
    window_start = segments[0].start
    bucket: list[TranscriptSegment] = []

    for seg in segments:
        if seg.start - window_start >= window_seconds and bucket:
            windows.append(
                _Window(
                    start=window_start,
                    end=bucket[-1].end,
                    text=" ".join(s.text for s in bucket).strip(),
                )
            )
            bucket = []
            window_start = seg.start
        bucket.append(seg)

    if bucket:
        windows.append(
            _Window(
                start=window_start,
                end=bucket[-1].end,
                text=" ".join(s.text for s in bucket).strip(),
            )
        )
    return windows


def _boundaries_at(sims: list[float], threshold: float) -> list[int]:
    boundaries = [0]
    for i, sim in enumerate(sims):
        if i == 0:
            continue
        if sim < threshold:
            boundaries.append(i)
    return boundaries


def _merge_short_chapters(
    boundaries: list[int], windows: list[_Window], min_seconds: float
) -> list[int]:
    if len(boundaries) <= 1:
        return boundaries

    merged = [boundaries[0]]
    for b in boundaries[1:]:
        chapter_start_time = windows[merged[-1]].start
        candidate_duration = windows[b - 1].end - chapter_start_time
        if candidate_duration < min_seconds:
            continue  # too short: fold into the chapter being accumulated
        merged.append(b)

    if len(merged) > 1:
        last_duration = windows[-1].end - windows[merged[-1]].start
        if last_duration < min_seconds:
            merged.pop()

    return merged


def calibrate(windows: list[_Window]) -> tuple[list[int], float, float]:
    """Pick the similarity threshold that best fits this particular video.

    A fixed threshold only ever suits the recording it was tuned on: the same
    value that yields 17 chapters on a 95-minute lecture yields one or two on
    a 10-minute clip. Instead, derive a target number of chapters from the
    video's own length (aiming for `chapter_target_seconds` per chapter,
    within sane bounds) and sweep the threshold for the value landing closest
    to it. Embeddings are computed once, so the sweep costs no API calls and
    is negligible next to the rest of the pipeline.

    Returns the chosen boundaries plus the threshold and minimum length used,
    so callers can report what was actually applied.
    """
    total_seconds = windows[-1].end - windows[0].start if windows else 0.0
    target_count = round(total_seconds / settings.chapter_target_seconds)
    target_count = max(settings.chapter_count_min, min(settings.chapter_count_max, target_count))

    # Keep short chapters from collapsing the structure, but scale the floor
    # with the video so a short recording can still be split at all.
    min_seconds = min(settings.chapter_min_seconds, total_seconds / (target_count * 2))

    texts = [w.text or "(silence)" for w in windows]
    sims = embeddings.similarity_drops(texts)

    best: tuple[list[int], float] | None = None
    best_distance: float | None = None
    for step in range(0, 41):
        threshold = 0.30 + step * 0.0125  # 0.30 .. 0.80
        boundaries = _merge_short_chapters(_boundaries_at(sims, threshold), windows, min_seconds)
        distance = abs(len(boundaries) - target_count)
        if best_distance is None or distance < best_distance:
            best, best_distance = (boundaries, threshold), distance
        if distance == 0:
            break

    assert best is not None
    boundaries, threshold = best
    return boundaries, threshold, min_seconds


def _overlapping_text(segments: list[TranscriptSegment], start: float, end: float) -> str:
    return " ".join(s.text for s in segments if s.start < end and s.end > start).strip()


def _overlapping_scenes(scenes: list[Scene], start: float, end: float) -> list[Scene]:
    return [s for s in scenes if s.start < end and s.end > start]


def _representative_frames(overlapping_scenes: list[Scene], max_frames: int = 3) -> list[Path]:
    paths = [Path(s.frame_path) for s in overlapping_scenes if s.frame_path]
    if len(paths) <= max_frames:
        return paths
    step = len(paths) / max_frames
    return [paths[int(i * step)] for i in range(max_frames)]


def build_chapters(
    transcript_segments: list[TranscriptSegment],
    scenes: list[Scene],
    checkpoint_path: Path | None = None,
    resume: bool = False,
) -> list[Chapter]:
    """Build chapters, LLM call per candidate boundary.

    If `checkpoint_path` is given, chapters generated so far are written to
    it after each successful LLM call — so a late failure (rate limit,
    transient 5xx that outlasts the retry budget) doesn't lose the calls
    that already succeeded; the run can be resumed/inspected from there.

    If `resume` is True and `checkpoint_path` already contains chapters
    (e.g. from a run that hit a quota limit partway through), those are
    reused instead of re-spending LLM calls on them — only missing chapter
    indices are generated. This assumes the window/threshold settings are
    unchanged between runs (otherwise chapter indices won't line up).
    """
    windows = _group_into_windows(transcript_segments, settings.chapter_window_seconds)
    if not windows:
        return []

    boundaries, _threshold, _min_seconds = calibrate(windows)

    existing_by_id: dict[str, Chapter] = {}
    if resume and checkpoint_path is not None and checkpoint_path.exists():
        existing_data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        existing_by_id = {c["id"]: Chapter.model_validate(c) for c in existing_data}

    chapters: list[Chapter] = []
    for i, boundary_idx in enumerate(tqdm(boundaries, desc="Generating chapters")):
        chapter_id = f"chapter_{i:02d}"
        start = windows[boundary_idx].start
        end_idx = boundaries[i + 1] - 1 if i + 1 < len(boundaries) else len(windows) - 1
        end = windows[end_idx].end

        if chapter_id in existing_by_id:
            chapters.append(existing_by_id[chapter_id])
        else:
            transcript_text = _overlapping_text(transcript_segments, start, end)
            overlapping_scenes = _overlapping_scenes(scenes, start, end)
            ocr_text = "\n".join(
                dict.fromkeys(s.ocr_text for s in overlapping_scenes if s.ocr_text)
            )
            frames = _representative_frames(overlapping_scenes)

            content = llm.generate_chapter_content(transcript_text, ocr_text, frames)

            chapters.append(
                Chapter(
                    id=chapter_id,
                    title=content.title,
                    start=start,
                    end=end,
                    summary=content.summary,
                    key_points=content.key_points,
                )
            )

        if checkpoint_path is not None:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump([c.model_dump() for c in chapters], f, ensure_ascii=False, indent=2)

    return chapters


def _print_boundary_preview(transcript_segments: list[TranscriptSegment]) -> None:
    """Print candidate chapter time ranges without calling the LLM.

    Lets chapter_similarity_threshold / chapter_min_seconds be tuned quickly
    (no API calls, no wait) before committing to a full run.
    """
    windows = _group_into_windows(transcript_segments, settings.chapter_window_seconds)
    boundaries, _threshold, _min_seconds = calibrate(windows)

    print(
        f"{len(windows)} windows, {len(boundaries)} candidate chapters "
        f"(threshold={settings.chapter_similarity_threshold}, "
        f"min_seconds={settings.chapter_min_seconds})"
    )
    for i, boundary_idx in enumerate(boundaries):
        start = windows[boundary_idx].start
        end_idx = boundaries[i + 1] - 1 if i + 1 < len(boundaries) else len(windows) - 1
        end = windows[end_idx].end
        preview = windows[boundary_idx].text[:80]
        print(f"  [{start:7.1f}s - {end:7.1f}s] ({(end - start) / 60:4.1f} min) {preview}")


def main() -> None:
    parser = argparse.ArgumentParser(description="S2M Sprint 2 chaptering")
    parser.add_argument("--scenes", required=True, type=Path, help="Path to scenes.json")
    parser.add_argument("--transcript", required=True, type=Path, help="Path to transcript.json")
    parser.add_argument(
        "--output", type=Path, default=Path("output/chapters.json"), help="Output JSON path"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print candidate chapter boundaries only, skip LLM calls (for threshold tuning)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse chapters already present in --output (e.g. after a quota error) "
        "instead of re-generating them",
    )
    args = parser.parse_args()

    scenes_data = json.loads(args.scenes.read_text(encoding="utf-8"))
    transcript_data = json.loads(args.transcript.read_text(encoding="utf-8"))

    scenes = [Scene.model_validate(s) for s in scenes_data]
    transcript_segments = [TranscriptSegment.model_validate(s) for s in transcript_data]

    if args.dry_run:
        _print_boundary_preview(transcript_segments)
        return

    chapters = build_chapters(
        transcript_segments, scenes, checkpoint_path=args.output, resume=args.resume
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump([c.model_dump() for c in chapters], f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(chapters)} chapters written to {args.output}")
    for c in chapters:
        print(f"  [{c.start:7.1f}s - {c.end:7.1f}s] {c.title}")


if __name__ == "__main__":
    main()
