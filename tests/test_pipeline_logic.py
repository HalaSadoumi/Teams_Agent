"""Tests for the decision logic at the heart of the pipeline.

These four functions are where the system decides how a recording is cut up
and how it is put back together. They are the ones a future maintainer will
want to change, and they are the ones whose regressions are invisible in the
finished video — a subtitle that drifts or a scene that ends up two seconds
long only shows up on playback, hours after the mistake was made.

All of them are pure: no network, no model, no API key needed. `pytest` runs
the whole file in well under a second.
"""

from __future__ import annotations

import pytest

from s2m_pipeline import chaptering, narration_original
from s2m_pipeline.chapter_subtitles import match_scene_segments
from s2m_pipeline.llm import _clip_on_word
from s2m_pipeline.models import TranscriptSegment


def segment(start: float, end: float, text: str) -> TranscriptSegment:
    return TranscriptSegment(start=start, end=end, text=text)


def window(start: float, end: float, text: str = "x") -> chaptering._Window:
    return chaptering._Window(start=start, end=end, text=text)


# --------------------------------------------------------------------------
# Chaptering: the threshold is calibrated per video, never hardcoded
# --------------------------------------------------------------------------

def test_calibration_adapts_the_cut_to_the_video_length(monkeypatch):
    """The number of chapters must follow the recording, not a fixed setting.

    This is the anti-overfitting property of the whole system: a threshold
    tuned on one video suits only that video. Here a graded similarity curve —
    ruptures of varying depth, as in real speech — is fed at two durations, and
    each must come out near its own target of one chapter per 5 min 30.
    """
    graded = [1.0] + [(0.35 + (i % 7) * 0.07) for i in range(1, 200)]
    monkeypatch.setattr(chaptering.embeddings, "similarity_drops", lambda texts: graded[: len(texts)])

    long_windows = [window(i * 60.0, (i + 1) * 60.0) for i in range(90)]   # 90 min
    short_windows = [window(i * 60.0, (i + 1) * 60.0) for i in range(20)]  # 20 min

    long_boundaries, _, _ = chaptering.calibrate(long_windows)
    short_boundaries, _, _ = chaptering.calibrate(short_windows)

    assert len(long_boundaries) > len(short_boundaries)
    # each lands near its own target: 90/5.5 ≈ 16, 20/5.5 ≈ 4
    assert abs(len(long_boundaries) - 16) <= 4
    assert abs(len(short_boundaries) - 4) <= 2


def test_calibration_respects_the_chapter_count_bounds(monkeypatch):
    """Even a recording with a rupture at every window stays within bounds."""
    monkeypatch.setattr(chaptering.embeddings, "similarity_drops", lambda texts: [0.0] * len(texts))
    windows = [window(i * 60.0, (i + 1) * 60.0) for i in range(200)]

    boundaries, _, _ = chaptering.calibrate(windows)

    assert len(boundaries) <= chaptering.settings.chapter_count_max


def test_short_chapters_are_merged_away():
    """Noisy boundaries must not produce chapters of a few seconds."""
    windows = [window(i * 60.0, (i + 1) * 60.0) for i in range(10)]
    merged = chaptering._merge_short_chapters([0, 1, 2, 5], windows, min_seconds=180.0)

    assert merged == [0, 5]


# --------------------------------------------------------------------------
# Narration: scene rhythm
# --------------------------------------------------------------------------

def test_scenes_shorter_than_the_floor_are_merged():
    """A two-second scene reads as a jump cut, whatever caused the split."""
    groups = [
        [segment(0.0, 2.0, "a")],      # trop courte
        [segment(2.5, 9.5, "b")],
        [segment(10.0, 30.0, "c")],
    ]
    merged = narration_original._merge_short_groups(groups)

    durations = [narration_original._group_seconds(g) for g in merged]
    assert all(d >= narration_original._MIN_SCENE_SECONDS for d in durations)
    assert len(merged) == 2


def test_merging_never_exceeds_the_ceiling():
    """Smoothing the rhythm must not create one long static shot."""
    groups = [[segment(i * 31.0, i * 31.0 + 30.0, "x")] for i in range(4)]
    merged = narration_original._merge_short_groups(groups)

    assert len(merged) == 4
    for group in merged:
        assert narration_original._group_seconds(group) <= narration_original._MAX_SCENE_SECONDS


def test_no_merge_across_a_long_removed_passage():
    """Splicing two moments separated by minutes of cut content would jar."""
    gap = narration_original._MERGE_MAX_GAP_SECONDS + 10
    groups = [
        [segment(0.0, 5.0, "a")],
        [segment(5.0 + gap, 10.0 + gap, "b")],
    ]
    merged = narration_original._merge_short_groups(groups)

    assert len(merged) == 2


def test_a_leading_short_group_is_absorbed_by_the_next():
    """The opening had no previous scene to fold into and stayed at 2 s."""
    groups = [[segment(0.0, 2.0, "a")], [segment(2.0, 20.0, "b")]]
    merged = narration_original._merge_short_groups(groups)

    assert len(merged) == 1
    assert narration_original._group_seconds(merged[0]) == pytest.approx(20.0)


# --------------------------------------------------------------------------
# Subtitles: matching narration back to the real speech timings
# --------------------------------------------------------------------------

def test_narration_is_matched_back_to_its_segments():
    segments = [
        segment(0.0, 2.0, "Bonjour tout le monde"),
        segment(2.0, 5.0, "voici la seance du jour"),
        segment(5.0, 8.0, "on commence"),
    ]
    run, cursor = match_scene_segments("Bonjour tout le monde voici la seance du jour", segments, 0)

    assert [s.text for s in run] == ["Bonjour tout le monde", "voici la seance du jour"]
    assert cursor == 2


def test_matching_skips_the_segments_that_were_cut_out():
    """Merged scenes span a dropped passage, so the run is not contiguous.

    Requiring adjacency made every merged scene fall back to a single cue
    covering the whole scene — half a minute of text on screen at once.
    """
    segments = [
        segment(0.0, 2.0, "premiere partie gardee"),
        segment(2.0, 6.0, "euh euh passage coupe"),
        segment(6.0, 9.0, "seconde partie gardee"),
    ]
    run, _ = match_scene_segments("premiere partie gardee seconde partie gardee", segments, 0)

    assert [s.text for s in run] == ["premiere partie gardee", "seconde partie gardee"]


def test_matching_reports_failure_rather_than_guessing():
    segments = [segment(0.0, 2.0, "rien a voir")]
    run, cursor = match_scene_segments("un texte absent de la transcription", segments, 0)

    assert run == []
    assert cursor == 0


def test_search_resumes_after_the_previous_scene():
    """A repeated phrase must match its own occurrence, not the first one."""
    segments = [
        segment(0.0, 2.0, "merci beaucoup"),
        segment(2.0, 4.0, "autre chose"),
        segment(4.0, 6.0, "merci beaucoup"),
    ]
    run, _ = match_scene_segments("merci beaucoup", segments, 2)

    assert run[0].start == 4.0


# --------------------------------------------------------------------------
# Fallback card: never cut a sentence mid-word on screen
# --------------------------------------------------------------------------

def test_clipping_falls_on_a_word_boundary():
    text = "ça concerne la protection des données contre tout accès au début de l'exercice"
    clipped = _clip_on_word(text, limit=60)

    assert clipped.endswith("…")
    assert not clipped[:-1].endswith(" ")
    assert clipped[:-1] in text


def test_short_text_is_left_alone():
    assert _clip_on_word("phrase courte", limit=60) == "phrase courte"


def test_whitespace_is_normalised():
    assert _clip_on_word("  deux   espaces  ", limit=60) == "deux espaces"


# --------------------------------------------------------------------------
# Reproductibilité : relancer le système doit redonner le même résultat
# --------------------------------------------------------------------------

def test_backdrop_seed_is_stable_across_processes():
    """The seed must not move between runs.

    It used to be `hash(scene_id)`, which Python randomises per process: three
    runs gave 20468, 8410 and 54640 for the same scene, so every execution
    fetched a fresh set of images while the comment claimed the opposite.
    """
    from s2m_pipeline.scene_images import seed_for

    # Valeur figée : si elle change, les arrière-plans de tous les cours
    # déjà produits ne seraient plus reproductibles.
    assert seed_for("chapter_00_scene_00") == 15188
    assert seed_for("chapter_00_scene_00") == seed_for("chapter_00_scene_00")
    assert seed_for("chapter_00_scene_00") != seed_for("chapter_00_scene_01")
    assert 0 <= seed_for("chapter_12_scene_07") < 100_000


def test_every_model_call_is_forced_to_temperature_zero():
    """Sampling made the pipeline give a different edit on each run.

    The temperature is applied in `_generate_content`, the single entry point,
    so a call site added later cannot forget it.
    """
    from s2m_pipeline import llm

    class FakeConfig:
        temperature = None

    class FakeClient:
        class models:
            @staticmethod
            def generate_content(**kwargs):
                return kwargs

    config = FakeConfig()
    llm._generate_content(FakeClient(), model="x", contents=[], config=config)

    assert config.temperature == 0.0


def test_an_explicit_temperature_is_left_alone():
    """A call that deliberately asks for sampling keeps its own setting."""
    from s2m_pipeline import llm

    class FakeConfig:
        temperature = 0.8

    class FakeClient:
        class models:
            @staticmethod
            def generate_content(**kwargs):
                return kwargs

    config = FakeConfig()
    llm._generate_content(FakeClient(), model="x", contents=[], config=config)

    assert config.temperature == 0.8
