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
from datetime import datetime

from dotenv import load_dotenv
import ollama
from rag_engine import retrieve_context, retrieve_qa_answer

load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Force local offline Ollama only (disable Gemini fallback per user request)
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
    "ur": "Urdu (use Nastaliq script — اردو)",
    "en": "English",
    "ks": "Koshur (Kashmiri in Nastaliq script)",
    "hinglish": (
        "Hinglish / Roman Urdu (Latin script, Urdu-Hindi mixed naturally with English words, "
        "exactly like the user wrote — do NOT switch to pure English and do NOT switch to Nastaliq script)"
    ),
    "auto": None,  # resolved per-query
}

_URDU_SCRIPT_RE = re.compile(r'[؀-ۿ]')

# Kashmiri-specific words that don't appear in Urdu naturally
_KASHMIRI_MARKERS = re.compile(
    r'(چھُہ|چھُ|آسُن|وُچھ|کیاہ|ہاو|دوپ|اوس|آو|گئِ|یِمن|تِمن|کُس|کُنہ|'
    r'ہوو|تہ بہ|گرژ|وژ|کھیو|ییو|ہیکہ|چھیہ|کرِ|گچھ|چھُس|وُنتھ|آسِہ|'
    r'بہ چھُس|تہ چھُہ|ما کر|ییہ|تھاوان|وانان|کران|پکھان)'
)

# Common Roman-script Urdu/Hindi/Kashmiri function/content words — signals "Hinglish"
# (Latin-script Urdu/Kashmiri) rather than plain English when the query has no Nastaliq script.
_HINGLISH_MARKERS = re.compile(
    r'\b(kya|kyu+n|kaise|kaisa|kaisi|hai|hain|nahi+|nahin|mujhe|mujhko|tumhe|aapko|apko|'
    r'mera|meri|mere|tumhara|tumhari|aapka|aapki|acha|accha|theek|thik|sakta|sakte|sakti|'
    r'karo|karna|karein|kare|hona|hoga|hogi|bhi|aur|lekin|magar|bohot|bahut|thoda|thodi|'
    r'zyada|jyada|sath|saath|pata|chahiye|dard|dawai|dawa|bemari|tabiyat|khana|peena|'
    r'raha|rahi|rahe|gaya|gayi|gaye|abhi|kal|aaj|kyunki|matlab|samajh|bata|batao|bolo|'
    r'mai|main|hum|tum|aap|iska|uska|kuch|sab|koi|'
    r'chhu|chhi|chhas|chhih|kyah|karun|karan|kheyn|chyun|koshur|kasheer|bemaar|sardi|garmi|sehat|ilaj)\b',
    flags=re.IGNORECASE,
)

def _resolve_language(query: str, language: str) -> str:
    """Detect language from query script/wording. Kashmiri and Urdu (Nastaliq script)
    checked first, then Hinglish/Roman Urdu (Latin script but Urdu-Hindi wording) before
    falling back to plain English — so a Hinglish question gets a Hinglish reply, not a
    pure-English one, closing the language barrier instead of switching scripts on the user."""
    if language and language != "auto":
        return language
    if _KASHMIRI_MARKERS.search(query):
        return "ks"
    if _URDU_SCRIPT_RE.search(query):
        return "ur"
    hinglish_hits = len(_HINGLISH_MARKERS.findall(query))
    if hinglish_hits >= 1:
        return "hinglish"
    return "en"

def _language_name(language: str) -> str:
    return _LANGUAGE_NAMES.get(language) or "the same language as the user's question"


# ─── LLM Configuration ──────────────────────────────────────────────
def get_system_prompt(page_context: str, language: str, retrieved_context: str = "") -> str:
    ctx_instruction = f" The user is on the '{page_context}' page; if their question is vague, assume it relates to this." if page_context else ""

    if retrieved_context:
        grounding = (
            "Use the Kashmir Health Knowledge Base below as your primary source. "
            "You may supplement with general Kashmir health knowledge, but never contradict the Knowledge Base."
        )
        context_section = f"\n\nKashmir Health Knowledge Base:\n{retrieved_context}"
    else:
        # No retrieved chunks — let the model answer from its Kashmir health knowledge
        # but still keep safety guardrails (don't diagnose, don't invent medications).
        grounding = (
            "You are a Kashmir-specific health assistant. Answer using your knowledge of "
            "Kashmiri seasonal wellness, diet, traditional practices, and general health. "
            "For medication or serious medical concerns, always recommend consulting a doctor."
        )
        context_section = ""

    medical_disclaimer = (
        "\nCRITICAL SAFETY RULE: If providing information about tablets or medication, "
        "ALWAYS append: 'Please consult a doctor before taking any medication.'"
    ) if retrieved_context and "[MEDICATION:" in retrieved_context else ""

    triage_rule = (
        "\nCRITICAL TRIAGE RULE: If the knowledge base contains a [CRITICAL TRIAGE ALERT], "
        "output ONLY the triage alert text — this is a medical emergency."
    ) if retrieved_context and "[CRITICAL TRIAGE ALERT" in retrieved_context else ""

    guardrail = (
        "\nSTRICT MEDICAL GUARDRAIL: You are NOT a doctor. Do not prescribe specific prescription medications or give exact clinical diagnoses. "
        "If the user describes a life-threatening emergency, advise them to seek emergency care immediately. "
        "Otherwise, you should provide helpful, general educational information on traditional remedies, seasonal wellness, and over-the-counter options, "
        "while advising them to consult a healthcare professional for specific treatments."
    )

    # Strong language instruction to steer small local models
    lang_instruction = ""
    if language == "ur":
        lang_instruction = "\nبغیر کسی استثنا کے، آپ کو صرف اور صرف اردو زبان (نستعلیق رسم الخط) میں جواب دینا ہے۔ انگریزی حروف یا رومن اردو کا استعمال بالکل نہ کریں۔"
    elif language == "ks":
        lang_instruction = "\nبغیر کسی استثنا کے، آپ کو صرف اور صرف کشمیری زبان (نستعلیق رسم الخط) میں جواب دینا ہے۔"
    elif language == "hinglish":
        lang_instruction = (
            "\nYou MUST respond ONLY in simple, natural Roman Urdu / Hinglish (Latin script). "
            "Write exactly how people text on WhatsApp. Do not translate literally or invent strange words (like 'saral satw' or 'sauceness'). "
            "Use simple conversational terms like 'dil ka dora' (heart attack), 'turant' (immediately), 'doctor se contact karein'. "
            "Example 1: 'Agar dil ka dora (heart attack) pade, toh turant SOS button dabayein aur 108/104 ambulance ko call karein. Mareez ko comfortable letayein.' "
            "Example 2: 'Sardi me sirdard ke liye garam paani ki bhaap (steam) lein, aur thand se bachein. Agar dard zyaada ho toh doctor ko dikhayein.' "
            "Keep the language extremely simple, conversational, and direct."
        )
    elif language == "en":
        lang_instruction = "\nYou MUST respond ONLY in English. Do not use Urdu or Kashmiri script."

    return f"""You are Sehat Saathi, a warm and knowledgeable health companion built for Kashmir.
{grounding}{triage_rule}{guardrail}
Answer the user's actual question directly — do not change the topic.{ctx_instruction}{context_section}

Response style by message type:
- Greetings/chitchat: Warm, brief, invite a health question. 1-2 sentences.
- Health questions: Caring tone, specific to Kashmir context. End with one actionable tip.
- Emotional/stress: Empathetic first, then practical. Acknowledge before advising.
- Unclear questions: Gently ask for clarification in one sentence.

KASHMIR LIFESTYLE ALIGNMENT — advice should fit how people actually live here, not sound generic:
- Winters mean indoor living, hamam/kangri heating, less daylight, joint-family households, dried vegetables (hokh syun) and stored produce, closed schools/roads during heavy snow — factor this into activity, diet, and mood advice for Chilla Kalan/Khurd.
- Summers (Sonth–Grind) mean orchard and farm labour, fresh produce, longer daylight, wedding/tourist season crowding — factor this into hydration, sun, and workload advice.
- Households are usually multi-generational; elders' habits, decisions, and care often involve the whole family, not just the individual.
- Diet is rice-and-Wazwan-rooted with strong salt/red-meat/ghee traditions, kehwa and noon chai as daily norms.
- Physical activity is shaped by terrain and season — walking is common, but winter and poor road/air conditions genuinely limit outdoor options; suggest realistic indoor alternatives, not generic "go for a walk" advice.
- Only bring in a cultural or seasonal detail when it actually changes the advice — do not decorate every answer with the same reflexive mentions (kehwa, kangri, hamam) if they are not relevant to the specific question. Vary examples across foods/practices/seasons instead of repeating the same one or two each time.

CRITICAL: Respond ONLY in {_language_name(language)}.{lang_instruction} HARD LIMIT: 45 words maximum — stop immediately at 45 words. Never diagnose. Do not restate the question.{medical_disclaimer}"""

OLLAMA_MODEL = os.environ.get("WATAN_OLLAMA_MODEL", "qwen2.5:1.5b")


# ─── Cloud API (Gemini) ─────────────────────────────────────────────
def _gemini_response(query: str, age_mode: str, district: str, season: str, page_context: str, language: str) -> dict:
    if not api_limiter.can_proceed():
        raise Exception("Rate limit exceeded")

    context = f"User profile: {age_mode} age group, {district}, Kashmir. Season: {season}. Page context: {page_context}. Current Date: {datetime.now().strftime('%Y-%m-%d')}"

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

    # Fallback: Retrieve generic context chunks with demographic pre-filtering
    retrieved = retrieve_context(query, top_k=4, min_score=0.10, age_mode=age_mode)
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
def _ollama_response(query: str, age_mode: str, district: str, season: str, page_context: str, language: str, chat_history: list | None = None) -> dict:
    try:
        context = f"User profile: {age_mode} age group, {district}, Kashmir. Season: {season}. Page context: {page_context}. Current Date: {datetime.now().strftime('%Y-%m-%d')}"

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

        # Fallback: Retrieve generic context chunks with demographic pre-filtering
        retrieved = retrieve_context(query, top_k=4, min_score=0.10, age_mode=age_mode)
        retrieved_context = "\n".join(retrieved) if retrieved else ""

        history_messages: list[dict] = []
        for h in (chat_history or [])[-10:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant") and content:
                history_messages.append({"role": role, "content": content})

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": get_system_prompt(page_context, language, retrieved_context)},
                *history_messages,
                {"role": "user", "content": f"{context}\n\nQuestion: {query}"}
            ],
            options={
                "temperature": 0.35,
                "num_predict": 90,
                "top_p": 0.85,
                "num_ctx": 1536
            }
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


# ─── Streaming Generator ─────────────────────────────────────────────
def stream_companion_response(
    query: str, age_mode: str, district: str, season: str,
    page_context: str = "", language: str = "auto",
    chat_history: list | None = None,
    temperature: float = 0.35, max_tokens: int = 150,
):
    """Yields raw text tokens for SSE streaming. Ollama native stream, Gemini word-by-word."""
    resolved_language = _resolve_language(query, language)
    matched_rule = _match_rules(query, season, age_mode)

    if matched_rule:
        if resolved_language in ("en", "hinglish"):
            # Hinglish is Latin-script — the English canned line reads naturally and
            # avoids jarring the user with a Nastaliq-script reply to a Roman-script question.
            text = matched_rule.get("response_en", "")
        elif resolved_language == "ks":
            text = matched_rule.get("response_ks") or matched_rule.get("response_ur", "")
        else:
            text = matched_rule.get("response_ur", "") or matched_rule.get("response_en", "")
        for word in text.split():
            yield word + " "
        return

    retrieved = retrieve_context(query, top_k=4, min_score=0.10, age_mode=age_mode)
    retrieved_context = "\n".join(retrieved) if retrieved else ""
    system_prompt = get_system_prompt(page_context, resolved_language, retrieved_context)
    context_line = f"User profile: {age_mode}, {district}, Kashmir. Season: {season}. Date: {datetime.now().strftime('%Y-%m-%d')}"

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for h in (chat_history or [])[-10:]:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": f"{context_line}\n\nQuestion: {query}"})

    try:
        stream = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            stream=True,
            options={"temperature": temperature, "num_predict": max_tokens, "top_p": 0.85},
        )
        for chunk in stream:
            token = chunk["message"]["content"]
            if token:
                yield token
        return
    except Exception as e:
        print(f"[stream] Ollama error: {e}")

    if gemini_client:
        try:
            if not api_limiter.can_proceed():
                raise Exception("Rate limit")
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{system_prompt}\n\n{context_line}\n\nQuestion: {query}",
                config=_no_thinking_config(0.5, 400),
            )
            text = (response.text or "").strip()
            for word in text.split():
                yield word + " "
            return
        except Exception as e:
            print(f"[stream] Gemini error: {e}")

    yield "Sorry, I could not generate a response. Please try again."


# ─── Public API ──────────────────────────────────────────────────────
def get_companion_response(
    query: str, age_mode: str, district: str, season: str,
    page_context: str = "", language: str = "auto",
    chat_history: list | None = None
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
        if resolved_language in ("en", "hinglish"):
            text = matched_rule.get("response_en", "")
        elif resolved_language == "ks":
            text = matched_rule.get("response_ks") or matched_rule.get("response_ur", "")
        else:
            text = matched_rule.get("response_ur", "") or matched_rule.get("response_en", "")
        text = text or matched_rule.get("response_en", "")

        # Online + non-Urdu/English/Hinglish: ask Gemini to translate the vetted offline answer
        # Skip Kashmiri if we already have response_ks (no need to translate)
        if gemini_client and resolved_language not in ("ur", "en", "hinglish") and not (resolved_language == "ks" and matched_rule.get("response_ks")):
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
    ollama_result = _ollama_response(query, age_mode, district, season, page_context, resolved_language, chat_history)
    if ollama_result["source"] != "error":
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
