"""Embedding-based topic-rupture detection for chaptering.

Cahier des charges section 9 specifies Sentence-Transformers
(all-MiniLM-L6-v2) for this: a lightweight, CPU-friendly way to find where
the *topic* changes, as opposed to relying on time (arbitrary N-minute
chunks) or visual cuts (which, per section 5.3, often don't correlate with
topic changes at all — confirmed by Sprint 1's own results on the real
video, where a single visual scene ran uninterrupted for 30+ minutes).
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed(texts: list[str]) -> np.ndarray:
    model = _get_model()
    return np.asarray(model.encode(texts, normalize_embeddings=True, show_progress_bar=False))


def similarity_drops(texts: list[str]) -> list[float]:
    """Cosine similarity between each text window and the one before it.

    `similarities[0]` is always 1.0 (nothing precedes the first window).
    A low value at index i means window i likely starts a new topic.
    """
    if len(texts) < 2:
        return [1.0] * len(texts)

    vectors = embed(texts)
    sims = [1.0]
    for i in range(1, len(vectors)):
        sims.append(float(np.dot(vectors[i - 1], vectors[i])))
    return sims
