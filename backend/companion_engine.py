"""
HealthCompanion Engine — Rule-first, Ollama (primary), Gemini (fallback).
RAG-grounded responses from Kashmir health data.
Rules match in <1ms (instant). Ollama LLM on CPU, offline-capable.
Gemini API fallback only on Ollama error, not for quality.
"""

import json
import re
import os
import time
from pathlib import Path
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
import ollama
from rag_engine import retrieve_context, retrieve_qa_answer

load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    try:
        from google import genai
        from google.genai import types as genai_types
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except ImportError:
        gemini_client = None
        genai_types = None
        print("[companion] google-genai not installed. Falling back to Ollama.")
else:
    gemini_client = None
    genai_types = None

def _no_thinking_config(temperature: float, max_output_tokens: int):
    """Plain dicts don't reliably apply nested thinking_config on this SDK
    version, leaving the 'thinking' budget to silently eat the whole
    max_output_tokens and truncate replies. Typed config objects do."""
    return genai_types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )

# ─── Simple In-Memory Rate Limiter ───────────────────────────────────
class RateLimiter:
    def __init__(self, max_requests, time_window_seconds):
        self.max_requests = max_requests
        self.time_window = time_window_seconds
        self.requests = []

    def can_proceed(self):
        now = time.time()
        # Clean up old requests outside the time window
        self.requests = [req for req in self.requests if now - req < self.time_window]
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False

# Limit to 10 requests per minute to stay safely within free tiers (e.g. Gemini's 15 RPM)
api_limiter = RateLimiter(max_requests=10, time_window_seconds=60)


# ─── Data Loading ────────────────────────────────────────────────────
_RULES_PATH = Path(__file__).parent / "data" / "companion_rules.json"

@lru_cache(maxsize=1)
def _load_rules() -> list[dict]:
    try:
        data = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
        return data.get("rules", [])
    except FileNotFoundError:
        return []


# ─── Rule Matching Engine (Instant, Offline) ─────────────────────────
def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r'[?.!,;:\'"(){}[\]]+', ' ', text)
    return text

def _trigger_hits(trigger: str, normalized: str) -> bool:
    """Whole-word match so short/ambiguous triggers (e.g. 'CO', 'BP') don't
    fire on unrelated words ('cold', 'comfort'). Multi-word phrases still
    match as substrings since they're specific enough."""
    t = trigger.strip().lower()
    if not t:
        return False
    if " " in t or len(t) > 12:
        return t in normalized
    return re.search(rf'(?<!\w){re.escape(t)}(?!\w)', normalized, flags=re.UNICODE) is not None

def _match_rules(query: str, season: str, age_mode: str) -> Optional[dict]:
    rules = _load_rules()
    normalized = _normalize(query)
    best_match = None
    best_score = 0

    for rule in rules:
        triggers = rule.get("triggers", [])
        if not triggers: continue
        if rule.get("seasons") and season not in rule.get("seasons"): continue
        if rule.get("age_modes") and age_mode not in rule.get("age_modes"): continue

        score = sum(1 for t in triggers if _trigger_hits(t, normalized))
        if score > best_score:
            best_score = score
            best_match = rule

    # Require a real signal: either 2+ distinct trigger hits, or a single hit
    # that covers most of a short query (avoids one stray keyword hijacking
    # an otherwise unrelated, more nuanced question that deserves the LLM).
    if best_match:
        word_count = max(len(normalized.split()), 1)
        if best_score >= 2 or (best_score == 1 and word_count <= 4):
            return best_match
    return None


# ─── Language Handling ───────────────────────────────────────────────
_LANGUAGE_NAMES = {
    "ur": "Roman Urdu",
    "en": "English",
    "ks": "Koshur (Kashmiri) written in Roman/Urdu script",
    "auto": None,  # resolved per-query
}

_URDU_SCRIPT_RE = re.compile(r'[؀-ۿ]')

def _resolve_language(query: str, language: str) -> str:
    """If the caller didn't pin a language, detect it from the query script
    so the reply matches what the user actually typed/spoke."""
    if language and language != "auto":
        return language
    return "ur" if _URDU_SCRIPT_RE.search(query) else "en"

def _language_name(language: str) -> str:
    return _LANGUAGE_NAMES.get(language) or "the same language as the user's question"


# ─── LLM Configuration ──────────────────────────────────────────────
def get_system_prompt(page_context: str, language: str, retrieved_context: str = "") -> str:
    ctx_instruction = f" The user is on the '{page_context}' page; if their question is vague, assume it relates to this." if page_context else ""
    context_section = f"\n\nKashmir Health Knowledge Base (ONLY use this for answers):\n{retrieved_context}" if retrieved_context else ""

    fallback_text = "If the knowledge base has no answer, respond: 'Main yeh sawaal samajh nahi aaya. Kya aap alag tarah se pooch sakte ho?' (I don't understand this question. Can you ask differently?)" if not context_section else ""

    return f"""You are Sehat Saathi, a health assistant for Kashmir.
CRITICAL: You MUST ONLY use the Kashmir Health Knowledge Base provided. Do NOT make up health information.
If the knowledge base doesn't contain relevant information, decline to answer rather than hallucinate.
Answer the user's actual question directly and specifically — do not change the topic.{ctx_instruction}{context_section}
Respond in {_language_name(language)}, under 50 words, plain and factual. End with one actionable tip. Never diagnose. Do not restate the question.
{fallback_text}"""

OLLAMA_MODEL = os.environ.get("WATAN_OLLAMA_MODEL", "qwen2.5:1.5b")


# ─── Cloud API (Gemini) ─────────────────────────────────────────────
def _gemini_response(query: str, age_mode: str, district: str, season: str, page_context: str, language: str) -> dict:
    if not api_limiter.can_proceed():
        raise Exception("Rate limit exceeded")

    context = f"User profile: {age_mode} age group, {district}, Kashmir. Season: {season}. Page context: {page_context}"

    # First, try direct QA match for high-confidence Kashmir answers
    resolved_language = _resolve_language(query, language)
    qa_match = retrieve_qa_answer(query, language=resolved_language)

    if qa_match["confidence"] > 0.3:
        return {
            "response_text": qa_match["answer"],
            "response_koshur": "",
            "source": f"qa_database ({qa_match.get('source', 'Kashmir Health Data')})",
            "confidence": qa_match["confidence"],
            "navigate_to": None
        }

    # Fallback: Retrieve generic context chunks
    retrieved = retrieve_context(query, top_k=4, min_score=0.08)
    retrieved_context = "\n".join(retrieved) if retrieved else ""

    system_prompt = get_system_prompt(page_context, language, retrieved_context)

    response = gemini_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=f"{system_prompt}\n\n{context}\n\nQuestion: {query}",
        config=_no_thinking_config(0.5, 400)
    )

    text = (response.text or "").strip()
    if not text:
        raise Exception("Empty response from Gemini")

    return {
        "response_text": text,
        "response_koshur": "",
        "source": "gemini",
        "confidence": 0.9,
        "navigate_to": None
    }


# ─── Ollama LLM Fallback ────────────────────────────────────────────
def _ollama_response(query: str, age_mode: str, district: str, season: str, page_context: str, language: str) -> dict:
    try:
        context = f"User profile: {age_mode} age group, {district}, Kashmir. Season: {season}. Page context: {page_context}"

        # First, try direct QA match for high-confidence Kashmir answers
        try:
            resolved_language = _resolve_language(query, language)
            qa_match = retrieve_qa_answer(query, language=resolved_language)
            print(f"[companion] QA match: conf={qa_match['confidence']:.3f}, answer_len={len(qa_match.get('answer',''))}")

            if qa_match["confidence"] > 0.3 and qa_match["answer"]:
                print(f"[companion] Returning QA answer!")
                return {
                    "response_text": qa_match["answer"],
                    "response_koshur": "",
                    "source": f"qa_database ({qa_match.get('source', 'Kashmir Health Data')})",
                    "confidence": qa_match["confidence"],
                    "navigate_to": None
                }
        except Exception as qa_err:
            print(f"[companion] QA lookup error: {qa_err}")

        # Fallback: Retrieve generic context chunks
        retrieved = retrieve_context(query, top_k=4, min_score=0.08)
        retrieved_context = "\n".join(retrieved) if retrieved else ""

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": get_system_prompt(page_context, language, retrieved_context)},
                {"role": "user", "content": f"{context}\n\nQuestion: {query}"}
            ],
            options={"temperature": 0.3, "num_predict": 220, "top_p": 0.85}
        )
        return {
            "response_text": response['message']['content'].strip(),
            "response_koshur": "",
            "source": "ollama",
            "confidence": 0.75,
            "navigate_to": None
        }
    except Exception as e:
        print(f"[companion] Ollama error: {e}")
        fallback = {
            "en": "I don't have information about this. Please ask a health-related question.",
            "ur": "Mujhe ismein jaankari nahi hai. Kripya sehat ke baare mein poochiye.",
        }
        return {
            "response_text": fallback.get(language, fallback["en"]),
            "response_koshur": "",
            "source": "error",
            "confidence": 0.0,
            "navigate_to": None
        }


# ─── Public API ──────────────────────────────────────────────────────
def get_companion_response(
    query: str, age_mode: str, district: str, season: str,
    page_context: str = "", language: str = "auto"
) -> dict:
    """
    Main entry point. Priority:
    1. Rule match (instant, offline) — only for high-confidence matches
    2. Gemini Cloud API (if key exists & rate limits allow)
    3. Local Ollama Fallback (fully offline)
    """
    resolved_language = _resolve_language(query, language)
    matched_rule = _match_rules(query, season, age_mode)

    if matched_rule:
        text = matched_rule.get("response_en") if resolved_language == "en" else matched_rule.get("response_ur")
        text = text or matched_rule.get("response_ur") or matched_rule.get("response_en", "")

        # Online + non-Urdu/English request: ask Gemini to translate the
        # vetted offline answer instead of forcing it into Urdu.
        if gemini_client and resolved_language not in ("ur", "en"):
            try:
                if not api_limiter.can_proceed():
                    raise Exception("Rate limit exceeded")
                translated = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"Translate the following Kashmiri health advice into {_language_name(resolved_language)}. Keep it concise, do not add commentary:\n\n{text}",
                    config=_no_thinking_config(0.3, 400)
                )
                if translated.text and translated.text.strip():
                    text = translated.text.strip()
            except Exception as e:
                print(f"[companion] Rule translation failed ({e}). Returning default language text.")

        return {
            "response_text": text,
            "response_en": matched_rule.get("response_en", ""),
            "response_koshur": "",
            "source": "rule",
            "confidence": matched_rule.get("confidence", 0.9),
            "tip": matched_rule.get("tip_ur", ""),
            "navigate_to": matched_rule.get("navigate_to", None),
            "rule_id": matched_rule.get("id", "")
        }

    # Local model is primary (fast, no quota/rate limits). Gemini only
    # kicks in if Ollama itself errors out, so there's still a cloud
    # fallback rather than a hard failure.
    ollama_result = _ollama_response(query, age_mode, district, season, page_context, resolved_language)
    if ollama_result["source"] == "ollama":
        return ollama_result

    if gemini_client:
        try:
            return _gemini_response(query, age_mode, district, season, page_context, resolved_language)
        except Exception as e:
            print(f"[companion] Gemini API failed or rate limited ({e}). Returning Ollama error result.")

    return ollama_result


def warm_up_model():
    try:
        print(f"[companion] Warming up Ollama model: {OLLAMA_MODEL}...")
        ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": "hello"}], options={"num_predict": 1})
    except Exception as e:
        print(f"[companion] Model warm-up failed (is Ollama running?): {e}")
