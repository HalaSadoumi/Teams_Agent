"""End-to-end course builder: one command, raw video in, finished course out.

Runs every stage of the pipeline in order and hands each stage's output to
the next, so producing a course from a new recording is a single command
rather than six invocations with hand-copied paths:

    python -m s2m_pipeline.build_course --video ma_formation.mp4

Stages
  1. Ingestion        audio extraction + enhancement, ASR, subtitles,
                      visual scene detection, slide OCR
  2. Chaptering       semantic segmentation (threshold auto-calibrated to
                      this video) + title / summary / key points per chapter
  3. Narration        keep-or-cut classification, then the speaker's real
                      audio spliced accordingly
  4. Visual planning  an animated scene archetype, its labels, an icon and a
                      backdrop prompt for every scene
  5. Backdrops        the ambience image behind each scene
  6. Render           one video per chapter (Remotion)
  7. Assembly         full course video + chapter navigation metadata

Every stage is skipped when its output already exists, so an interrupted run
resumes where it stopped instead of redoing hours of work. Use --from to
force a restart at a given stage, and --skip-images / --skip-render to stop
before the expensive parts.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from s2m_pipeline.core import assemble
from s2m_pipeline.from_video import chaptering
from s2m_pipeline.from_video import content_selection
from s2m_pipeline.from_video import narration_original
from s2m_pipeline.from_video import pipeline
from s2m_pipeline.core import scene_images
from s2m_pipeline.core import scene_visuals as scene_visuals_mod
from s2m_pipeline.models import Chapter, Scene, StoryboardScene

STAGES = ["ingest", "chapters", "narration", "visuals", "images", "render", "assemble"]

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REMOTION_DIR = PROJECT_ROOT / "remotion"


@dataclass
class Paths:
    """Everything the run produces, under one directory per video."""

    root: Path

    @property
    def work(self) -> Path:
        return self.root / "work"

    @property
    def scenes(self) -> Path:
        return self.root / "scenes.json"

    @property
    def transcript(self) -> Path:
        return self.work / "transcript.json"

    @property
    def master_audio(self) -> Path:
        return self.work / "audio.wav"

    @property
    def chapters(self) -> Path:
        return self.root / "chapters.json"

    @property
    def storyboard(self) -> Path:
        return self.root / "storyboard.json"

    @property
    def narration_dir(self) -> Path:
        return self.work / "narration"

    @property
    def visuals(self) -> Path:
        return self.root / "scene_visuals.json"

    @property
    def backdrops(self) -> Path:
        return self.work / "backdrops"

    @property
    def course(self) -> Path:
        return self.root / "course"


def _step(n: int, total: int, title: str) -> None:
    print(f"\n{'=' * 62}\n[{n}/{total}] {title}\n{'=' * 62}")


def _done(message: str) -> None:
    print(f"  -> {message}")


def run_ingest(video: Path, paths: Paths) -> None:
    result = pipeline.run(video, paths.work)
    paths.scenes.parent.mkdir(parents=True, exist_ok=True)
    paths.scenes.write_text(
        json.dumps([s.model_dump() for s in result.scenes], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths.transcript.write_text(
        json.dumps(
            [s.model_dump() for s in result.transcript_segments], ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    from s2m_pipeline.from_video import subtitles

    subtitles.write_srt(result.transcript_segments, paths.work / "subtitles.srt")
    subtitles.write_vtt(result.transcript_segments, paths.work / "subtitles.vtt")
    _done(f"{len(result.scenes)} scenes, {len(result.transcript_segments)} transcript segments")


def run_chapters(paths: Paths) -> None:
    from s2m_pipeline.models import TranscriptSegment

    scenes = [Scene.model_validate(s) for s in json.loads(paths.scenes.read_text(encoding="utf-8"))]
    segments = [
        TranscriptSegment.model_validate(s)
        for s in json.loads(paths.transcript.read_text(encoding="utf-8"))
    ]
    chapters = chaptering.build_chapters(
        segments, scenes, checkpoint_path=paths.chapters, resume=True
    )
    _done(f"{len(chapters)} chapters")


def run_narration(paths: Paths) -> None:
    from s2m_pipeline.models import TranscriptSegment

    chapters = [
        Chapter.model_validate(c) for c in json.loads(paths.chapters.read_text(encoding="utf-8"))
    ]
    scenes = [Scene.model_validate(s) for s in json.loads(paths.scenes.read_text(encoding="utf-8"))]
    segments = [
        TranscriptSegment.model_validate(s)
        for s in json.loads(paths.transcript.read_text(encoding="utf-8"))
    ]

    all_scenes: list[StoryboardScene] = []
    done_ids: set[str] = set()
    if paths.storyboard.exists():
        existing = [
            StoryboardScene.model_validate(s)
            for s in json.loads(paths.storyboard.read_text(encoding="utf-8"))
        ]
        all_scenes.extend(existing)
        done_ids = {s.chapter_id for s in existing}

    for chapter in chapters:
        if chapter.id in done_ids:
            continue
        all_scenes.extend(
            narration_original.build_narration_scenes(
                chapter, segments, scenes, paths.master_audio, paths.narration_dir
            )
        )
        paths.storyboard.write_text(
            json.dumps([s.model_dump() for s in all_scenes], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    total = sum(s.duration for s in all_scenes)
    _done(f"{len(all_scenes)} narration scenes, {total / 60:.1f} min of original voice")


def run_visuals(paths: Paths) -> None:
    storyboard = [
        StoryboardScene.model_validate(s)
        for s in json.loads(paths.storyboard.read_text(encoding="utf-8"))
    ]
    scenes = [Scene.model_validate(s) for s in json.loads(paths.scenes.read_text(encoding="utf-8"))]
    chapters = json.loads(paths.chapters.read_text(encoding="utf-8"))
    bounds = {c["id"]: (c["start"], c["end"]) for c in chapters}

    plans = scene_visuals_mod.build_scene_visuals(
        storyboard, scenes, bounds, paths.visuals, resume=True
    )
    archetypes = {p["archetype"] for p in plans.values()}
    _done(f"{len(plans)} scene plans, {len(archetypes)} distinct archetypes")


def run_images(paths: Paths) -> None:
    plans: dict[str, dict] = json.loads(paths.visuals.read_text(encoding="utf-8"))
    paths.backdrops.mkdir(parents=True, exist_ok=True)

    pending = [
        (sid, p) for sid, p in plans.items() if not (paths.backdrops / f"{sid}.jpg").exists()
    ]
    print(f"  {len(plans) - len(pending)}/{len(plans)} already generated, {len(pending)} to go")

    from tqdm import tqdm

    failed = 0
    for scene_id, plan in tqdm(pending, desc="  backdrops"):
        prompt = plan.get("image_prompt") or plan.get("label") or "abstract professional background"
        seed = scene_images.seed_for(scene_id)
        if not scene_images.fetch_image(prompt, paths.backdrops / f"{scene_id}.jpg", seed):
            failed += 1

    present = sum(1 for s in plans if (paths.backdrops / f"{s}.jpg").exists())
    _done(f"{present}/{len(plans)} backdrops" + (f", {failed} failed (re-run to retry)" if failed else ""))


def _sync_remotion_inputs(paths: Paths) -> None:
    """Stage this run's data where the Remotion project reads it."""
    public = REMOTION_DIR / "public"
    (public / "audio").mkdir(parents=True, exist_ok=True)
    (public / "backdrops").mkdir(parents=True, exist_ok=True)

    shutil.copy(paths.storyboard, public / "storyboard.json")
    shutil.copy(paths.visuals, public / "scene_visuals.json")

    for src in paths.narration_dir.glob("*.wav"):
        dst = public / "audio" / src.name
        if not dst.exists():
            shutil.copy(src, dst)
    for src in paths.backdrops.glob("*.jpg"):
        dst = public / "backdrops" / src.name
        if not dst.exists():
            shutil.copy(src, dst)

    available = sorted(p.stem for p in (public / "backdrops").glob("*.jpg"))
    (public / "backdrops.json").write_text(json.dumps(available), encoding="utf-8")


def run_render(paths: Paths, out_name: str = "out") -> None:
    """Render one video per chapter.

    `out_name` lets a second course render beside the first instead of
    overwriting it: the slide-deck pipeline writes to remotion/out_pdf."""
    _sync_remotion_inputs(paths)
    out_dir = REMOTION_DIR / out_name
    out_dir.mkdir(exist_ok=True)

    chapters = json.loads(paths.chapters.read_text(encoding="utf-8"))
    npx = shutil.which("npx") or "npx"

    for i, chapter in enumerate(chapters, start=1):
        chapter_id = chapter["id"]
        target = out_dir / f"{chapter_id}.mp4"
        if target.exists() and target.stat().st_size > 0:
            print(f"  [{i}/{len(chapters)}] {chapter_id} — already rendered")
            continue

        print(f"  [{i}/{len(chapters)}] {chapter_id} — rendering...")
        composition_id = chapter_id.replace("_", "-")
        result = subprocess.run(
            [
                npx, "remotion", "render", "src/index.ts", composition_id,
                str(Path(out_name) / f"{chapter_id}.mp4"),
                "--log=error",
                # The generated backdrops are blurred and composited, so a
                # frame can take well over Remotion's 30s default on a busy
                # CPU-only machine; a long per-frame budget avoids losing a
                # whole chapter to one slow frame.
                "--timeout=180000",
                # Leave a core free so the machine stays usable during the
                # multi-hour batch.
                "--concurrency=50%",
            ],
            cwd=REMOTION_DIR,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            target.unlink(missing_ok=True)
            print(f"      FAILED:\n{result.stderr[-1500:]}")
        else:
            print(f"      done ({target.stat().st_size // 1_000_000} MB)")


def run_assemble(paths: Paths) -> None:
    chapters = [
        Chapter.model_validate(c) for c in json.loads(paths.chapters.read_text(encoding="utf-8"))
    ]
    paths.course.mkdir(parents=True, exist_ok=True)

    rendered = assemble.measure_chapters(chapters, REMOTION_DIR / "out")
    metadata = assemble._write_ffmetadata(rendered, paths.course / "chapters.ffmetadata")
    assemble._write_vtt(rendered, paths.course / "chapters.vtt")
    assemble._write_json(rendered, paths.course / "course_chapters.json")
    course = assemble.concat_chapters(rendered, metadata, paths.course / "course_full.mp4")

    total = rendered[-1].end if rendered else 0.0
    _done(f"{course} ({total / 60:.1f} min, {len(rendered)} chapters)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a complete e-learning course from a raw training video"
    )
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Defaults to output/<video name>/",
    )
    parser.add_argument("--from", dest="from_stage", choices=STAGES, default=None,
                        help="Re-run starting at this stage, ignoring existing output")
    parser.add_argument("--skip-images", action="store_true", help="Skip backdrop generation")
    parser.add_argument("--skip-render", action="store_true", help="Stop before rendering video")
    args = parser.parse_args()

    if not args.video.exists():
        sys.exit(f"Video not found: {args.video}")

    root = args.output_dir or (PROJECT_ROOT / "output" / args.video.stem)
    paths = Paths(root=root)
    paths.work.mkdir(parents=True, exist_ok=True)

    start_index = STAGES.index(args.from_stage) if args.from_stage else 0

    def should_run(stage: str, produced: Path) -> bool:
        index = STAGES.index(stage)
        if index < start_index:
            return False
        # An explicit --from means "redo this stage", even though its output
        # is already on disk; every other stage is skipped once produced.
        if args.from_stage is not None and index == start_index:
            return True
        if produced.exists():
            print(f"  (already done — {produced.name})")
            return False
        return True

    print(f"Course build: {args.video.name}\nOutput: {root}")
    total = len(STAGES)

    _step(1, total, "Ingestion — audio, transcription, scenes, OCR")
    if should_run("ingest", paths.scenes):
        run_ingest(args.video, paths)

    _step(2, total, "Chaptering — semantic segmentation + chapter content")
    if should_run("chapters", paths.chapters):
        run_chapters(paths)

    _step(3, total, "Narration — keep/cut selection, original voice")
    if should_run("narration", paths.storyboard):
        run_narration(paths)

    _step(4, total, "Visual planning — archetype, labels, icon per scene")
    if should_run("visuals", paths.visuals):
        run_visuals(paths)

    _step(5, total, "Backdrops — ambience image per scene")
    if args.skip_images:
        print("  (skipped)")
    elif STAGES.index("images") >= start_index:
        run_images(paths)

    _step(6, total, "Render — one video per chapter")
    if args.skip_render:
        print("  (skipped)")
    elif STAGES.index("render") >= start_index:
        run_render(paths)

    _step(7, total, "Assembly — full course + chapter navigation")
    if args.skip_render:
        print("  (skipped — needs rendered chapters)")
    elif STAGES.index("assemble") >= start_index:
        run_assemble(paths)

    print(f"\n{'=' * 62}\nCourse build finished — {root}\n{'=' * 62}")


if __name__ == "__main__":
    main()
