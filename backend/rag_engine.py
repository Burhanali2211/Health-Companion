"""
Lightweight TF-IDF retrieval over the project's own JSON data, used to
ground LLM replies in real Kashmir health/diet/exercise/general-knowledge
content instead of letting a small local model hallucinate. No embeddings
model / torch dependency — keeps the offline Pi build under the storage
budget in CLAUDE.md.
"""

import json
from pathlib import Path
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_DATA_DIR = Path(__file__).parent / "data"
_SOURCE_FILES = [
    "companion_rules.json",
    "diet_plans.json",
    "exercises.json",
    "seasons.json",
    "kashmir_general.json",
]


def _flatten_to_chunks(node) -> list[str]:
    """Walk any JSON structure; each dict with string-valued fields becomes
    one searchable text chunk so this works across differently-shaped files
    without per-file schema code."""
    chunks = []
    if isinstance(node, dict):
        text_parts = [v for v in node.values() if isinstance(v, str) and len(v) > 2]
        if text_parts:
            chunks.append(" | ".join(text_parts))
        for v in node.values():
            chunks.extend(_flatten_to_chunks(v))
    elif isinstance(node, list):
        for item in node:
            chunks.extend(_flatten_to_chunks(item))
    return chunks


@lru_cache(maxsize=1)
def _load_corpus() -> tuple[str, ...]:
    chunks = []
    for fname in _SOURCE_FILES:
        fpath = _DATA_DIR / fname
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            chunks.extend(_flatten_to_chunks(data))
        except FileNotFoundError:
            continue
    return tuple(dict.fromkeys(chunks))


@lru_cache(maxsize=1)
def _build_index():
    corpus = _load_corpus()
    if not corpus:
        return None, None
    vectorizer = TfidfVectorizer(max_features=4000)
    matrix = vectorizer.fit_transform(corpus)
    return vectorizer, matrix


def retrieve_context(query: str, top_k: int = 4, min_score: float = 0.08) -> list[str]:
    corpus = _load_corpus()
    vectorizer, matrix = _build_index()
    if vectorizer is None:
        return []
    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, matrix)[0]
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return [corpus[i] for i in ranked[:top_k] if scores[i] >= min_score]
