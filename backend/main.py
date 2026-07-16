"""
HealthCompanion — FastAPI Backend
Kashmir-specific offline-first health companion.
Optimized for Raspberry Pi 5 and Windows.
Serves all APIs offline-first with JSON data bundles.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path

import asyncio
import json as _json
import concurrent.futures

import ollama
from seasonal_engine import get_context, get_all_districts
from diet_engine import get_diet_plan, get_meal_types
from exercise_engine import get_exercises, get_season_lock, get_exercise_types
from companion_engine import get_companion_response, stream_companion_response, warm_up_model, _resolve_language, OLLAMA_MODEL

_stream_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


# ─── Startup / Shutdown Lifecycle ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm up the Ollama model so first query is fast
    warm_up_model()
    yield
    # Shutdown: nothing needed


app = FastAPI(
    title="HealthCompanion API",
    version="1.0.0",
    description="Kashmir-specific offline-first health companion kiosk",
    lifespan=lifespan,
)


# ─── CORS — allow dev and kiosk origins ──────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Kiosk mode needs flexible origins
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Serve built frontend if dist/ exists ────────────────────────────
_static = Path(__file__).parent / "static"
if _static.exists():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")


# ─── Health Check ────────────────────────────────────────────────────
@app.get("/")
async def health_check() -> dict:
    return {"status": "ok", "app": "Health Wellness Companion", "version": "1.0.0", "offline": True}


# ─── Season & Context ───────────────────────────────────────────────
@app.get("/api/context/{district}")
async def context(district: str) -> dict:
    try:
        ctx = get_context(district_id=district)
        return {"status": "ok", "data": ctx}
    except Exception as e:
        return {"status": "error", "data": None, "message": str(e)}


@app.get("/api/districts")
async def districts() -> dict:
    return {"status": "ok", "data": get_all_districts()}


# ─── Diet ────────────────────────────────────────────────────────────
@app.get("/api/diet/{season}/{age}/{meal}")
async def diet(season: str, age: str, meal: str) -> dict:
    items = get_diet_plan(season, age, meal)
    return {"status": "ok", "data": items}


@app.get("/api/diet/meals")
async def diet_meals() -> dict:
    return {"status": "ok", "data": get_meal_types()}


# ─── Exercise ────────────────────────────────────────────────────────
@app.get("/api/exercise/{season}/{age}/{type}")
async def exercise(season: str, age: str, type: str) -> dict:
    lock = get_season_lock(season)
    items = get_exercises(season, age, type)
    return {
        "status": "ok",
        "data": items,
        "outdoor_locked": not lock.get("outdoor", True),
        "lock_reason_ur": lock.get("reason_ur", ""),
        "lock_reason_en": lock.get("reason_en", ""),
    }


@app.get("/api/exercise/types")
async def exercise_types() -> dict:
    return {"status": "ok", "data": get_exercise_types()}


# ─── Companion (Rule Engine + Cloud/Local LLM) ────────────────────────
@app.post("/api/companion/ask")
async def companion_ask(body: dict) -> dict:
    query = body.get("query", "").strip()
    age_mode = body.get("age_mode", "jawaan")
    district = body.get("district", "srinagar")
    page_context = body.get("page_context", "")
    language = body.get("language", "auto")

    if not query:
        return {
            "status": "ok",
            "data": {
                "response_text": "Ask me anything about your health!",
                "source": "empty",
                "confidence": 0.0
            }
        }

    # Get current season from local context
    ctx = get_context(district_id=district)
    season = ctx["season"]["id"]

    chat_history = body.get("chat_history", [])
    response_data = get_companion_response(query, age_mode, district, season, page_context, language, chat_history)

    return {"status": "ok", "data": response_data}


@app.post("/api/companion/stream")
async def companion_stream(body: dict):
    query = body.get("query", "").strip()
    age_mode = body.get("age_mode", "jawaan")
    district = body.get("district", "srinagar")
    page_context = body.get("page_context", "")
    language = body.get("language", "auto")
    chat_history = body.get("chat_history", [])

    if not query:
        async def _empty():
            yield f"data: {_json.dumps({'text': 'Ask me anything about your health!'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(_empty(), media_type="text/event-stream")

    ctx = get_context(district_id=district)
    season = ctx["season"]["id"]

    temperature = float(body.get("temperature", _settings.get("temperature", 0.35)))
    max_tokens = int(body.get("max_tokens", _settings.get("max_tokens", 150)))

    async def _generate():
        gen = stream_companion_response(query, age_mode, district, season, page_context, language, chat_history, temperature, max_tokens)
        loop = asyncio.get_event_loop()

        def _next():
            try:
                return next(gen), False
            except StopIteration:
                return None, True

        while True:
            token, done = await loop.run_in_executor(_stream_executor, _next)
            if done:
                yield "data: [DONE]\n\n"
                break
            yield f"data: {_json.dumps({'text': token})}\n\n"
            await asyncio.sleep(0)

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# ─── Voice (STT placeholder — Whisper integration Week 3) ───────────
@app.post("/api/voice/stt")
async def voice_stt(file: UploadFile = File(...)) -> dict:
    from voice.stt import transcribe
    try:
        audio_bytes = await file.read()
        result = transcribe(audio_bytes, language="auto")
        return {
            "status": "ok",
            "data": {
                "transcript": result["text"],
                "language_detected": result["language"],
                "confidence": result["confidence"],
            }
        }
    except Exception as e:
        print(f"[stt] Error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ─── Voice (TTS Endpoint using fallback-aware synthesize) ───────────
from io import BytesIO
from fastapi.responses import StreamingResponse
import re

@app.post("/api/voice/tts")
async def voice_tts(body: dict):
    text = body.get("text", "").strip()
    language = body.get("language", "auto")
    age_mode = body.get("age_mode", "jawaan")
    
    if not text:
        return {"status": "error", "message": "No text provided"}
        
    try:
        # Auto-resolve language based on the text contents
        resolved_lang = language
        if language == "auto" or not language or language == "en":
            if re.search(r'[؀-ۿ]', text):
                resolved_lang = "ur"
            elif re.search(r'\b(kya|hai|hain|nahi|kar|kheyn|sehat|chhu|chhi|karan|kyah|sardi|ilaj)\b', text, re.IGNORECASE):
                resolved_lang = "ur"  # Roman Urdu/Kashmiri gets Urdu/Hindi voice
            else:
                resolved_lang = "en"

        from voice.tts import synthesize
        res = synthesize(text, language=resolved_lang, age_mode=age_mode)
        
        if res["audio_bytes"]:
            media_type = "audio/wav" if res["source"] in ("coqui", "pyttsx3") else "audio/mpeg"
            return StreamingResponse(BytesIO(res["audio_bytes"]), media_type=media_type)
        else:
            raise Exception(res.get("error") or "Audio generation failed")
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─── Chat History (in-memory, session-scoped) ───────────────────────
from datetime import datetime, timezone

_chat_history: list[dict] = []

@app.post("/api/chats/save")
async def save_chat(body: dict) -> dict:
    entry = {
        "id": len(_chat_history) + 1,
        "query": body.get("query", ""),
        "responsePreview": body.get("responsePreview", ""),
        "ageMode": body.get("ageMode", "jawaan"),
        "source": body.get("source", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _chat_history.insert(0, entry)
    if len(_chat_history) > 50:
        _chat_history.pop()
    return {"status": "ok", "data": entry}


@app.get("/api/chats")
async def get_chats() -> dict:
    return {"status": "ok", "data": _chat_history}


@app.delete("/api/chats")
async def clear_chats() -> dict:
    _chat_history.clear()
    return {"status": "ok"}


# ─── Models (Ollama) ────────────────────────────────────────────────
import subprocess

@app.get("/api/models")
async def list_models() -> dict:
    try:
        result = ollama.list()
        models = []
        for m in result.get("models", []):
            name = m.get("name", m.get("model", "unknown"))
            size_bytes = m.get("size", 0)
            size_gb = round(size_bytes / (1024 ** 3), 2) if size_bytes else None
            is_active = name.split(":")[0] == OLLAMA_MODEL.split(":")[0] or name == OLLAMA_MODEL
            models.append({
                "name": name,
                "size_bytes": size_bytes,
                "size_gb": size_gb,
                "size_label": f"{size_gb} GB" if size_gb else "Unknown",
                "is_active": is_active,
                "digest": m.get("digest", "")[:12],
            })
        return {"status": "ok", "data": {"models": models, "active_model": OLLAMA_MODEL}}
    except Exception as e:
        return {"status": "error", "data": {"models": [], "active_model": OLLAMA_MODEL}, "message": str(e)}


@app.post("/api/models/pull")
async def pull_model(body: dict) -> dict:
    model_name = body.get("model", "").strip()
    if not model_name:
        return {"status": "error", "message": "model name required"}
    try:
        ollama.pull(model_name)
        return {"status": "ok", "data": {"pulled": model_name}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/models/set-active")
async def set_active_model(body: dict) -> dict:
    global OLLAMA_MODEL
    model_name = body.get("model", "").strip()
    if not model_name:
        return {"status": "error", "message": "model name required"}
    import companion_engine
    companion_engine.OLLAMA_MODEL = model_name
    OLLAMA_MODEL = model_name
    return {"status": "ok", "data": {"active_model": model_name}}


@app.delete("/api/models/{model_name:path}")
async def delete_model(model_name: str) -> dict:
    try:
        ollama.delete(model_name)
        return {"status": "ok", "data": {"deleted": model_name}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─── RAG ────────────────────────────────────────────────────────────
import companion_engine as _ce

@app.get("/api/rag/status")
async def rag_status() -> dict:
    from rag_engine import _load_corpus
    try:
        corpus = _load_corpus("jawaan")
        chunk_count = len(corpus)
        data_dir = Path(__file__).parent / "data"
        total_bytes = sum(
            f.stat().st_size for f in data_dir.rglob("*.json") if f.is_file()
        )
        size_mb = round(total_bytes / (1024 * 1024), 1)
        return {
            "status": "ok",
            "data": {
                "enabled": True,
                "chunk_count": chunk_count,
                "size_mb": size_mb,
                "size_label": f"{size_mb} MB",
                "source_files": [
                    "diet_plans.json", "exercises.json",
                    "seasons.json", "kashmir_general.json"
                ],
                "knowledge_dir": str(data_dir / "knowledge"),
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


_rag_enabled: bool = True

@app.get("/api/rag/toggle")
async def get_rag_toggle() -> dict:
    return {"status": "ok", "data": {"enabled": _rag_enabled}}

@app.post("/api/rag/toggle")
async def set_rag_toggle(body: dict) -> dict:
    global _rag_enabled
    _rag_enabled = bool(body.get("enabled", True))
    import companion_engine as ce
    ce._RAG_ENABLED = _rag_enabled
    return {"status": "ok", "data": {"enabled": _rag_enabled}}


@app.post("/api/rag/rebuild")
async def rebuild_rag() -> dict:
    try:
        from rag_engine import _load_corpus
        _load_corpus.cache_clear()
        for mode in ["jawaan", "bacha", "buzurg"]:
            _load_corpus(mode)
        return {"status": "ok", "data": {"message": "RAG corpus rebuilt"}}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─── Settings ───────────────────────────────────────────────────────
_settings: dict = {
    "temperature": 0.7,
    "max_tokens": 200,
    "language": "auto",
    "age_mode": "jawaan",
    "district": "srinagar",
    "voice_speed": 1.0,
}

@app.get("/api/settings")
async def get_settings() -> dict:
    return {"status": "ok", "data": _settings}

@app.post("/api/settings")
async def update_settings(body: dict) -> dict:
    global _settings
    for k in ["temperature", "max_tokens", "language", "age_mode", "district", "voice_speed"]:
        if k in body:
            _settings[k] = body[k]
    return {"status": "ok", "data": _settings}


# ─── Performance Stats ───────────────────────────────────────────────
_perf_stats: dict = {"last_response_ms": None, "tokens_per_sec": None, "total_queries": 0}

@app.get("/api/stats")
async def get_stats() -> dict:
    return {"status": "ok", "data": _perf_stats}


# ─── Kangri Safety ──────────────────────────────────────────────────
@app.get("/api/kangri/safety")
async def kangri_safety() -> dict:
    ctx = get_context()
    return {
        "status": "ok",
        "data": {
            "alert_active": ctx["kangri_alert"],
            "season": ctx["season"]["id"],
            "message_ur": "کانگڑی استعمال کرتے وقت کمرہ ہوادار رکھیں۔ CO گیس خطرناک ہے۔"
                          if ctx["kangri_alert"] else ""
        }
    }
