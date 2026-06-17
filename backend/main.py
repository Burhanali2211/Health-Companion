"""
Watan Sehat — FastAPI Backend
Optimized for Raspberry Pi 5 and Windows.
Serves all APIs offline-first with JSON data bundles.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path

from seasonal_engine import get_context, get_all_districts
from diet_engine import get_diet_plan, get_meal_types
from exercise_engine import get_exercises, get_season_lock, get_exercise_types
from companion_engine import get_companion_response, warm_up_model


# ─── Startup / Shutdown Lifecycle ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm up the Ollama model so first query is fast
    warm_up_model()
    yield
    # Shutdown: nothing needed


app = FastAPI(
    title="Watan Sehat API",
    version="1.0.0",
    description="Kashmir-specific offline-first health companion",
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
    return {"status": "ok", "app": "Watan Sehat", "version": "1.0.0", "offline": True}


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

    response_data = get_companion_response(query, age_mode, district, season, page_context, language)

    return {"status": "ok", "data": response_data}


# ─── Voice (STT placeholder — Whisper integration Week 3) ───────────
@app.post("/api/voice/stt")
async def voice_stt() -> dict:
    return {
        "status": "ok",
        "data": {
            "transcript": "",
            "language_detected": "ur",
            "confidence": 0.0,
            "message": "Whisper STT will be integrated in Week 3"
        }
    }


# ─── Voice (TTS placeholder — Coqui integration Week 3) ─────────────
from io import BytesIO
from fastapi.responses import StreamingResponse
from gtts import gTTS

@app.post("/api/voice/tts")
async def voice_tts(body: dict):
    text = body.get("text", "")
    language = body.get("language", "ur")
    
    if not text:
        return {"status": "error", "message": "No text provided"}
        
    try:
        # Generate speech using Google TTS (works instantly)
        # Use 'hi' for better pronunciation of Roman Urdu/Hindi if 'ur' sounds robotic
        lang_code = 'hi' if language == 'ur' else language
        tts = gTTS(text=text, lang=lang_code)
        mp3_fp = BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        
        return StreamingResponse(mp3_fp, media_type="audio/mpeg")
    except Exception as e:
        return {"status": "error", "message": str(e)}


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
