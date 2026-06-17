"""
Text-to-speech using gTTS (online) with pyttsx3 fallback (offline).
Primary: gTTS for natural Urdu/English speech.
Fallback: pyttsx3 for offline capability (English only, lower quality).
"""

import io
from pathlib import Path

try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False


def synthesize(text: str, language: str = "en", age_mode: str = "jawaan") -> dict:
    """
    Synthesize text to speech audio bytes.

    Args:
        text: Text to speak (Urdu, English, or mixed)
        language: "ur" (Urdu), "en" (English)
        age_mode: "bacha", "jawaan", "buzurg" (affects speech rate)

    Returns:
        {
            "audio_bytes": bytes (MP3),
            "source": "gtts" | "pyttsx3",
            "error": str or None
        }
    """
    if not text or len(text) == 0:
        return {"audio_bytes": b"", "source": "none", "error": "Empty text"}

    # Speed adjustments per age mode (gTTS doesn't support this, but for pyttsx3)
    speed_map = {"bacha": 1.05, "jawaan": 1.0, "buzurg": 0.85}
    speed = speed_map.get(age_mode, 1.0)

    # Try gTTS first (online, better quality, supports Urdu)
    if HAS_GTTS:
        try:
            lang_code = "ur" if language == "ur" else "en"
            tts = gTTS(text, lang=lang_code, slow=False)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            return {
                "audio_bytes": audio_buffer.getvalue(),
                "source": "gtts",
                "error": None,
            }
        except Exception as e:
            print(f"[tts] gTTS failed ({e}), trying pyttsx3...")

    # Fallback: pyttsx3 (offline, English only)
    if HAS_PYTTSX3:
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 200 * speed)  # Default 200 WPM
            engine.setProperty("volume", 1.0)

            # Save to bytes buffer (pyttsx3 saves to file, so use temp)
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

    return {
        "audio_bytes": b"",
        "source": "none",
        "error": "No TTS engine available (install gtts or pyttsx3)",
    }
