"""Sprint 3 (visual generation): map every narration scene to an animated
scene archetype.

This is the layer that makes the visual generation a *system* rather than a
set of hand-authored scenes: for each storyboard scene, the LLM picks one of
the closed vocabulary of archetypes in llm.SCENE_ARCHETYPES (each backed by a
self-animating Remotion component) and fills in its text slots, driven by
what the narration actually says plus the OCR text of the slides on screen at
that moment.

Output (scene_visuals.json) is consumed directly by the renderer, so adding a
new archetype means adding one component + one vocabulary entry, never
per-scene code.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tqdm import tqdm

from . import llm
from .models import Scene, StoryboardScene


def _overlapping_ocr(scenes: list[Scene], start: float, end: float) -> str:
    overlapping = [s for s in scenes if s.start < end and s.end > start]
    return "\n".join(dict.fromkeys(s.ocr_text for s in overlapping if s.ocr_text))


def build_scene_visuals(
    storyboard: list[StoryboardScene],
    scenes: list[Scene],
    chapters_bounds: dict[str, tuple[float, float]],
    output_path: Path,
    resume: bool = False,
) -> dict[str, dict]:
    """Returns {scene_id: visual plan dict}, checkpointed per chapter."""
    plans: dict[str, dict] = {}
    if resume and output_path.exists():
        plans = json.loads(output_path.read_text(encoding="utf-8"))

    by_chapter: dict[str, list[StoryboardScene]] = {}
    for s in storyboard:
        by_chapter.setdefault(s.chapter_id, []).append(s)

    for chapter_id, chapter_scenes in tqdm(by_chapter.items(), desc="Planning scene visuals"):
        if all(s.scene_id in plans for s in chapter_scenes):
            continue

        start, end = chapters_bounds.get(chapter_id, (0.0, 0.0))
        ocr_text = _overlapping_ocr(scenes, start, end)
        indexed = [(i, s.narration) for i, s in enumerate(chapter_scenes)]

        chapter_plans = llm.generate_scene_visual_plans(indexed, ocr_text)

        for i, scene in enumerate(chapter_scenes):
            plan = chapter_plans[i]
            plans[scene.scene_id] = {
                "archetype": plan.archetype,
                "label": plan.label,
                "items": plan.items,
                "primary": plan.primary,
                "secondary": plan.secondary,
            }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(plans, f, ensure_ascii=False, indent=2)

    return plans


def main() -> None:
    parser = argparse.ArgumentParser(description="S2M scene visual planning")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--scenes", required=True, type=Path)
    parser.add_argument("--chapters", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("output/scene_visuals.json"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    storyboard = [
        StoryboardScene.model_validate(s)
        for s in json.loads(args.storyboard.read_text(encoding="utf-8"))
    ]
    scenes = [Scene.model_validate(s) for s in json.loads(args.scenes.read_text(encoding="utf-8"))]
    chapters = json.loads(args.chapters.read_text(encoding="utf-8"))
    bounds = {c["id"]: (c["start"], c["end"]) for c in chapters}

    plans = build_scene_visuals(storyboard, scenes, bounds, args.output, resume=args.resume)

    counts: dict[str, int] = {}
    for p in plans.values():
        counts[p["archetype"]] = counts.get(p["archetype"], 0) + 1

    print(f"\nDone. {len(plans)} scene visual plans written to {args.output}")
    for archetype, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {archetype:18s} {n}")


if __name__ == "__main__":
    main()
