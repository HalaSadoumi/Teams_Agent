"""Create an editable time-based storyboard from a transcript."""

import json
from pathlib import Path

def create_storyboard(transcript_json: Path, output_markdown: Path, scene_seconds: int = 30) -> None:
    data = json.loads(transcript_json.read_text(encoding="utf-8"))
    scenes: dict[int, list[str]] = {}
    for segment in data["segments"]:
        scenes.setdefault(int(segment["start"] // scene_seconds), []).append(segment["text"].strip())
    lines = ["# Training Video Storyboard", "", "Review visual directions before final rendering.", ""]
    for bucket, texts in scenes.items():
        start, end = bucket * scene_seconds, (bucket + 1) * scene_seconds
        lines.extend([f"## {start // 60:02}:{start % 60:02}–{end // 60:02}:{end % 60:02}", f"- Narration: {' '.join(texts)}", "- Visual: Preserve the matching original slide or screen recording; add a callout only when it improves clarity.", "- On-screen text: Review key terms from narration.", ""])
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.write_text("\n".join(lines), encoding="utf-8")
