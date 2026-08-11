"""Lightweight NLP utilities for semantic segmentation and keyword extraction."""

import re
from collections import Counter
from typing import List

STOPWORDS = {
    "et", "une", "des", "les", "pour", "avec", "dans", "que", "qui", "sur", "par", "est", "le", "la",
    "du", "de", "un", "au", "aux", "se", "ce", "ces", "son", "ses", "mais", "pas", "plus", "ou",
    "nous", "vous", "ils", "elles", "il", "elle", "on", "a", "ont", "être", "avoir", "faire", "comme",
    "tout", "tous", "toutes", "cette", "ça", "ici", "là", "aussi", "donc", "si", "aujourd", "hui",
    "très", "bien", "peut", "quel", "quelle", "quels", "quelles", "même", "encore", "entre", "avant",
    "après", "sans", "sous", "cette", "celui", "celle", "dont", "leur", "leurs", "mon", "ton", "nos",
    "vos", "leurs", "à", "d", "l", "n", "j", "t", "qu", "ai", "as", "nous", "cest", "cest", "nous",
    "vous", "ils", "elles", "ceci", "cela", "ça", "ça", "cette", "cet", "ces",
}


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s'-]", " ", text)
    return text


def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    normalized = normalize_text(text)
    tokens = [token for token in normalized.split() if len(token) >= 4 and token.isalpha() and token not in STOPWORDS]
    counts = Counter(tokens)
    return [token for token, _ in counts.most_common(top_n)]


def topic_similarity(keywords_a: List[str], keywords_b: List[str]) -> float:
    if not keywords_a or not keywords_b:
        return 0.0

    set_a = set(keywords_a)
    set_b = set(keywords_b)
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def merge_keywords(*keyword_lists: List[str], max_keywords: int = 15) -> List[str]:
    merged = []
    seen = set()
    for keywords in keyword_lists:
        for kw in keywords:
            if kw not in seen:
                merged.append(kw)
                seen.add(kw)
            if len(merged) >= max_keywords:
                return merged
    return merged
