"""
Lightweight TF-IDF retrieval over the project's own JSON data.
Implements Sophisticated Metadata-as-Text (MaT) chunking and Demographic Pre-filtering
to safely handle medication recommendations offline on a Raspberry Pi.
"""

import json
from pathlib import Path
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_DATA_DIR = Path(__file__).parent / "data"

# Standard unstructured data files
_SOURCE_FILES = [
    "diet_plans.json",
    "exercises.json",
    "seasons.json",
    "kashmir_general.json",
]

def _flatten_to_chunks(node) -> list[str]:
    """Walk unstructured JSON and extract string values."""
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
    elif isinstance(node, str) and len(node) > 2:
        chunks.append(node)
    return chunks

@lru_cache(maxsize=4) # Cache per age_mode
def _load_corpus(age_mode: str) -> tuple[str, ...]:
    chunks = []
    
    # 1. Load standard unstructured files
    for fname in _SOURCE_FILES:
        fpath = _DATA_DIR / fname
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            chunks.extend(_flatten_to_chunks(data))
        except FileNotFoundError:
            continue
            
    # 2. Load Sophisticated Knowledge Directories (Metadata-Enriched)
    knowledge_dir = _DATA_DIR / "knowledge"
    if knowledge_dir.exists():
        for fpath in knowledge_dir.rglob("*.json"):
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                
                # Handle Medication Knowledge Schema
                if data.get("resource_type") == "medication_knowledge":
                    for entry in data.get("entries", []):
                        # HYBRID PRE-FILTERING (Safety Guardrail)
                        if age_mode == "buzurg" and entry.get("safe_for_elderly") is False:
                            continue # Filter out unsafe meds for elderly
                        if age_mode == "bacha" and entry.get("safe_for_children") is False:
                            continue # Filter out unsafe meds for children
                            
                        # METADATA-AS-TEXT (MaT) Transformation
                        chunk_text = (
                            f"[MEDICATION: {entry.get('name', 'Unknown')}] "
                            f"Category: {entry.get('category', data.get('category', 'General'))}. "
                            f"Usage: {entry.get('usage', '')}. "
                            f"Contraindications: {entry.get('contraindications', 'None')}. "
                            f"Details: {entry.get('text_content', '')}"
                        )
                        chunks.append(chunk_text)
                
                # Handle General Knowledge Schema (Remedies, Contacts, etc.)
                elif data.get("resource_type") == "general_knowledge":
                    for entry in data.get("entries", []):
                        chunk_text = f"[{entry.get('category', 'General')}: {entry.get('title', 'Info')}] {entry.get('text_content', '')}"
                        chunks.append(chunk_text)
            except Exception as e:
                print(f"[RAG] Error loading structured knowledge {fpath}: {e}")

    return tuple(dict.fromkeys(chunks))

@lru_cache(maxsize=4)
def _build_index(age_mode: str):
    corpus = _load_corpus(age_mode)
    if not corpus:
        return None, None
    vectorizer = TfidfVectorizer(max_features=4000, stop_words='english')
    matrix = vectorizer.fit_transform(corpus)
    return vectorizer, matrix

def retrieve_context(query: str, top_k: int = 4, min_score: float = 0.20, age_mode: str = "jawaan") -> list[str]:
    # 1. Safety Guardrail: Check Symptom Triage Overrides First
    triage_alerts = []
    triage_file = _DATA_DIR / "knowledge" / "emergency" / "symptom_triage.json"
    if triage_file.exists():
        try:
            triage_data = json.loads(triage_file.read_text(encoding="utf-8"))
            if triage_data.get("resource_type") == "symptom_triage":
                query_lower = query.lower()
                for entry in triage_data.get("entries", []):
                    for kw in entry.get("keywords", []):
                        if kw.lower() in query_lower:
                            alert = f"[CRITICAL TRIAGE ALERT: {entry.get('category', 'WARNING')}] {entry.get('title', '')} - {entry.get('text_content', '')}"
                            if alert not in triage_alerts:
                                triage_alerts.append(alert)
        except Exception as e:
            print(f"[RAG] Triage error: {e}")

    # 2. Standard TF-IDF Retrieval
    corpus = _load_corpus(age_mode)
    vectorizer, matrix = _build_index(age_mode)
    if vectorizer is None:
        return triage_alerts
        
    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, matrix)[0]
    
    # Sort indices by score descending
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    
    # Return top K chunks meeting the minimum score
    standard_results = [corpus[i] for i in ranked[:top_k] if scores[i] >= min_score]
    
    # Combine: Alerts always take highest priority
    return triage_alerts + standard_results

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

    # TF-IDF match (Word-level to prevent hallucination)
    vectorizer = TfidfVectorizer(max_features=2000, analyzer='word', ngram_range=(1, 2), stop_words='english')
    try:
        matrix = vectorizer.fit_transform(corpus)
        query_vec = vectorizer.transform([query])
        scores = cosine_similarity(query_vec, matrix)[0]
        best_idx = scores.argmax()
        best_score = scores[best_idx]

        if best_score > 0.35:  # Engine re-checks at its own threshold; return actual score
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
