"""Content selection per cahier des charges section 5.4.

Classifies each ASR transcript segment within a chapter as "garder" (keep -
content to preserve, or borderline content worth keeping) or "couper" (cut -
hesitations, repetitions, silences, off-topic asides). Feeds the
original-voice narration pipeline (narration_original.py): the real
recording is trimmed according to these decisions, rather than an LLM
rewriting the text for a synthetic voice (cahier section 6.2, option 1).
"""

from __future__ import annotations

from . import llm
from .models import Chapter, TranscriptSegment


def classify_chapter_segments(
    chapter: Chapter, transcript_segments: list[TranscriptSegment]
) -> list[tuple[TranscriptSegment, str]]:
    """Returns [(segment, "garder"|"couper"), ...] for segments overlapping the chapter."""
    overlapping = [
        s for s in transcript_segments if s.start < chapter.end and s.end > chapter.start
    ]
    if not overlapping:
        return []

    indexed_texts = [
        (i, f"({s.start:.1f}s-{s.end:.1f}s) {s.text}") for i, s in enumerate(overlapping)
    ]
    decisions = llm.classify_segments(indexed_texts)

    # Default to "garder" for anything the model didn't return a decision
    # for - cahier section 5.4: the goal is not aggressive compression.
    return [(s, decisions.get(i, "garder")) for i, s in enumerate(overlapping)]
