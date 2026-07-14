"""
Text-to-speech using Coqui TTS (offline Urdu VITS) with graceful fallbacks.
Primary: Coqui TTS (True offline, neural, supports Urdu natively)
Fallback 1: gTTS (Online, good quality)
Fallback 2: pyttsx3 (Offline, English only, low quality)
"""

import io
from pathlib import Path
import warnings

# Suppress noisy library warnings
warnings.filterwarnings("ignore")

# 1. Try Coqui TTS (Primary Offline)
try:
    from TTS.api import TTS
    HAS_COQUI = True
    _COQUI_MODEL = None
except ImportError:
    HAS_COQUI = False

# 2. Try gTTS (Secondary Online)
try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False

# 3. Try pyttsx3 (Tertiary Offline)
try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False


def _get_coqui_model():
    global _COQUI_MODEL
    if _COQUI_MODEL is None and HAS_COQUI:
        try:
            print("[tts] Loading Coqui TTS model (offline)...")
            # Using a generic multilingual model for Urdu/English, or fallback to standard
            # In a real deployed Pi environment, a finetuned VITS model path would be here.
            _COQUI_MODEL = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        except Exception as e:
            print(f"[tts] Coqui model load failed: {e}")
            _COQUI_MODEL = False # Mark as failed
    return _COQUI_MODEL


def synthesize(text: str, language: str = "ur", age_mode: str = "jawaan") -> dict:
    """
    Synthesize text to speech audio bytes with robust fallbacks.

    Args:
        text: Text to speak
        language: "ur" (Urdu), "en" (English), "ks" (Koshur)
        age_mode: "bacha", "jawaan", "buzurg" (affects speech rate)

    Returns:
        {
            "audio_bytes": bytes (WAV/MP3),
            "source": "coqui" | "gtts" | "pyttsx3" | "none",
            "error": str or None
        }
    """
    if not text or len(text.strip()) == 0:
        return {"audio_bytes": b"", "source": "none", "error": "Empty text"}

    # Language mapping
    lang_code = "ur" if language in ["ur", "ks"] else "en"
    
    # Speed multipliers (slower for Buzurg)
    speed_map = {"bacha": 1.05, "jawaan": 1.0, "buzurg": 0.85}
    speed = speed_map.get(age_mode, 1.0)
    
    is_buzurg = (age_mode == "buzurg")

    # PRIMARY: Coqui TTS (Offline Neural)
    if HAS_COQUI:
        model = _get_coqui_model()
        if model:
            try:
                temp_file = Path("/tmp/coqui_out.wav")
                # Generate audio
                model.tts_to_file(text=text, file_path=str(temp_file), language=lang_code, speed=speed)
                
                if temp_file.exists():
                    audio_bytes = temp_file.read_bytes()
                    temp_file.unlink()
                    return {
                        "audio_bytes": audio_bytes,
                        "source": "coqui",
                        "error": None
                    }
            except Exception as e:
                print(f"[tts] Coqui synthesis failed: {e}. Falling back...")

    # FALLBACK 1: gTTS (Online)
    if HAS_GTTS:
        try:
            # gTTS supports slow=True for Buzurg mode
            tts = gTTS(text, lang=lang_code, slow=is_buzurg)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            return {
                "audio_bytes": audio_buffer.getvalue(),
                "source": "gtts",
                "error": None,
            }
        except Exception as e:
            print(f"[tts] gTTS failed ({e}). Falling back to pyttsx3...")

    # FALLBACK 2: pyttsx3 (Offline English-only backup)
    if HAS_PYTTSX3:
        try:
            engine = pyttsx3.init()
            # Default rate is 200, apply multiplier
            base_rate = 150 if is_buzurg else 200
            engine.setProperty("rate", int(base_rate * speed))
            engine.setProperty("volume", 1.0)

            temp_file = Path("/tmp/tts_output.wav")
            engine.save_to_file(text, str(temp_file))
            engine.runAndWait()

            if temp_file.exists():
                audio_bytes = temp_file.read_bytes()
                temp_file.unlink()
                return {
                    "audio_bytes": audio_bytes,
                    "source": "pyttsx3",
                    "error": None,
                }
        except Exception as e:
            print(f"[tts] pyttsx3 failed: {e}")

    # ERROR: All engines failed
    return {
        "audio_bytes": b"",
        "source": "none",
        "error": "All TTS engines failed. Check dependencies (coqui-tts, gtts, pyttsx3) or internet connection."
    }
