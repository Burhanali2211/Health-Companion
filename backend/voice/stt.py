"""
Speech-to-text using OpenAI Whisper (tiny model, offline).
Supports Urdu, English, Kashmiri Roman.
Includes robust hallucination filtering for field environments.
"""

import io
import whisper
import numpy as np
import scipy.io.wavfile as wavfile
from scipy.signal import resample_poly
from math import gcd

_MODEL = None

def load_model():
    """Load Whisper tiny model once (39MB, optimal for Pi 5 latency)."""
    global _MODEL
    if _MODEL is None:
        print("[stt] Loading Whisper 'tiny' model for fast offline inference...")
        try:
            _MODEL = whisper.load_model("tiny")
        except Exception as e:
            print(f"[stt] Fatal error loading Whisper model: {e}")
            _MODEL = None
    return _MODEL

def transcribe(audio_bytes: bytes, language: str = "auto") -> dict:
    """
    Transcribe audio bytes to text robustly.

    Args:
        audio_bytes: Raw audio data (WAV, MP3, etc.)
        language: "ur" (Urdu), "en" (English), "auto" (detect)

    Returns:
        {"text": str, "language": str, "confidence": float, "error": None/str}
    """
    # Graceful fallback for empty input
    if not audio_bytes or len(audio_bytes) < 100:
        return {"text": "", "language": "ur", "confidence": 0.0, "error": "Empty audio"}

    try:
        model = load_model()
        if model is None:
            return {"text": "", "language": "ur", "confidence": 0.0, "error": "Model failed to load"}

        # Whisper language codes mapping
        lang_map = {
            "ur": "ur",      # Urdu
            "en": "en",      # English
            "ks": "ur",      # Kashmiri phonetic overlap -> treat as Urdu
            "auto": None,    # Auto-detect
        }
        whisper_lang = lang_map.get(language, None)

        # Read wav bytes in memory and convert to float32 numpy array
        try:
            sr, audio_data = wavfile.read(io.BytesIO(audio_bytes))
        except Exception as e:
            return {"text": "", "language": "ur", "confidence": 0.0, "error": f"Invalid audio format: {e}"}

        if audio_data.ndim > 1:
            audio_data = audio_data[:, 0]  # Mono conversion
        
        # Normalize
        audio_float32 = audio_data.astype(np.float32) / 32768.0

        # Resample to 16kHz if needed
        if sr != 16000:
            g = gcd(sr, 16000)
            audio_float32 = resample_poly(audio_float32, 16000 // g, sr // g).astype(np.float32)

        # Strict silence/noise rejection (prevents Whisper hallucinating "Thank you")
        rms = float(np.sqrt(np.mean(audio_float32 ** 2)))
        if rms < 0.015:
            print("[stt] Audio too quiet, dropping to prevent hallucination.")
            return {"text": "", "language": whisper_lang or "ur", "confidence": 0.0, "error": None}

        # Transcribe with aggressive anti-hallucination settings
        try:
            result = model.transcribe(
                audio_float32,
                language=whisper_lang,
                fp16=False,
                condition_on_previous_text=False,
                temperature=(0.0, 0.2),  # Keep temperature low to avoid looping
                no_speech_threshold=0.6, # Stricter speech threshold
                compression_ratio_threshold=1.5,
                logprob_threshold=-1.0,
            )
        except Exception as e:
            return {"text": "", "language": "ur", "confidence": 0.0, "error": f"Transcription failed: {e}"}

        text = result.get("text", "").strip()
        detected_lang = result.get("language", whisper_lang or "ur")

        # Hallucination post-processing filters
        words = text.split()
        
        # 1. Filter out common English hallucinations if Urdu was requested/detected
        if detected_lang == "ur" and any(phrase in text.lower() for phrase in ["thank you", "subtitles", "amara.org", "watching"]):
            print(f"[stt] Dropped known hallucination: {text}")
            return {"text": "", "language": "ur", "confidence": 0.0, "error": None}

        # 2. Catch repetition loops
        if len(words) >= 6:
            # Single word repeating
            if len(set(words)) <= 3 and len(words) > 8:
                return {"text": "", "language": detected_lang, "confidence": 0.0, "error": None}
            # Multi-word phrase repeating
            chunk = " ".join(words[:3])
            if text.count(chunk) >= 3:
                return {"text": "", "language": detected_lang, "confidence": 0.0, "error": None}
        
        # 3. Correct common medical misspellings
        corrections = {
            "parasitolmol": "paracetamol",
            "parasitolom": "paracetamol",
            "parasitol": "paracetamol",
        }
        text_lower = text.lower()
        for wrong, right in corrections.items():
            if wrong in text_lower:
                text = text.replace(wrong, right).replace(wrong.capitalize(), right.capitalize())

        segments = result.get("segments", [])
        confidence = segments[0].get("confidence", 0.9) if segments else 0.9

        return {
            "text": text,
            "language": detected_lang,
            "confidence": confidence,
            "error": None
        }

    except Exception as e:
        print(f"[stt] Critical Error: {e}")
        return {"text": "", "language": "ur", "confidence": 0.0, "error": str(e)}
