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
    "kashmir_health_qa.json",
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


def retrieve_qa_answer(query: str, language: str = "en") -> dict:
    """Search Kashmir QA dataset directly for exact answers. Returns high-confidence match."""
    qa_file = _DATA_DIR / "kashmir_health_qa.json"
    try:
        data = json.loads(qa_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"answer": "", "source": "", "confidence": 0.0}

    qa_pairs = data.get("qa_pairs", [])
    if not qa_pairs:
        return {"answer": "", "source": "", "confidence": 0.0}

    # Build searchable corpus from Q&A
    question_field = "question_en" if language == "en" else "question_ur"
    answer_field = "answer_en" if language == "en" else "answer_ur"

    corpus = [qa[question_field] for qa in qa_pairs if question_field in qa]
    if not corpus:
        return {"answer": "", "source": "", "confidence": 0.0}

    # TF-IDF match
    vectorizer = TfidfVectorizer(max_features=2000, analyzer='char', ngram_range=(2, 3))
    try:
        matrix = vectorizer.fit_transform(corpus)
        query_vec = vectorizer.transform([query])
        scores = cosine_similarity(query_vec, matrix)[0]
        best_idx = scores.argmax()
        best_score = scores[best_idx]

        if best_score > 0.3:  # Confidence threshold for QA matches
            matched_qa = qa_pairs[best_idx]
            return {
                "answer": matched_qa.get(answer_field, ""),
                "source": matched_qa.get("source", "Kashmir Health Data"),
                "confidence": float(best_score),
                "season": matched_qa.get("season", ""),
            }
    except Exception:
        pass

    return {"answer": "", "source": "", "confidence": 0.0}
