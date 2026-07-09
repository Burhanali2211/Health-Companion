"""
Speech-to-text using OpenAI Whisper (tiny model, 39MB, offline).
Supports Urdu, English, Kashmiri Roman.
"""

import io
from pathlib import Path
import whisper

_MODEL = None

def load_model():
    """Load Whisper tiny model once (39MB, fast)."""
    global _MODEL
    if _MODEL is None:
        print("[stt] Loading Whisper tiny model...")
        _MODEL = whisper.load_model("tiny")
    return _MODEL

def transcribe(audio_bytes: bytes, language: str = "auto") -> dict:
    """
    Transcribe audio bytes to text.

    Args:
        audio_bytes: Raw audio data (WAV, MP3, etc.)
        language: "ur" (Urdu), "en" (English), "auto" (detect)

    Returns:
        {"text": str, "language": str, "confidence": float}
    """
    try:
        model = load_model()

        # Whisper language codes
        lang_map = {
            "ur": "ur",      # Urdu
            "en": "en",      # English
            "ks": "ur",      # Kashmiri → treat as Urdu
            "auto": None,    # Auto-detect
        }
        whisper_lang = lang_map.get(language, None)

        import tempfile
        import os
        import imageio_ffmpeg
        
        # Inject bundled ffmpeg into PATH so Whisper can find it
        os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
        
        # Whisper requires a filepath or np.ndarray. Writing to a temp file is safest.
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            # Transcribe
            result = model.transcribe(
                tmp_path,
                language=whisper_lang,
                fp16=False  # CPU only, no CUDA
            )
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        return {
            "text": result["text"].strip(),
            "language": result.get("language", "ur"),
            "confidence": result.get("segments", [{}])[0].get("confidence", 0.9) if result.get("segments") else 0.9,
        }
    except Exception as e:
        print(f"[stt] Error: {e}")
        return {"text": "", "language": "en", "confidence": 0.0}
