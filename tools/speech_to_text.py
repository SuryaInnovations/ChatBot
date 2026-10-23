"""
tools/speech_to_text.py — Speech-to-Text Audio Transcription Engine.

Implements Capability 14 (STT):
- Transcribes audio from in-memory bytes or audio files (wav, mp3, m4a, ogg, webm).
- Uses Google Speech Recognition (free, no API key), Google Gemini multimodal STT,
  Groq Whisper, OpenAI Whisper, or local faster-whisper.
- Handles audio streams, chunking, and language detection.
"""

import os
import io
import tempfile
import logging
from typing import Dict, Any, Optional

from core.voice_understanding import clean_voice_transcript

logger = logging.getLogger("chatbot.tools.speech_to_text")


def _format_success_result(raw_text: str, provider: str, detected_language: Optional[str] = None) -> Dict[str, Any]:
    raw = raw_text.strip()
    cleaned = clean_voice_transcript(raw)
    res = {
        "success": True,
        "text": cleaned if cleaned else raw,
        "raw_text": raw,
        "provider": provider
    }
    if detected_language:
        res["detected_language"] = detected_language
    return res


def transcribe_audio(
    audio_bytes: bytes,
    language: Optional[str] = None,
    mime_type: str = "audio/wav"
) -> Dict[str, Any]:
    """
    Transcribes raw audio bytes into text.
    Tries multiple providers in order of speed and availability:
    1. Google Speech Recognition (free, keyless)
    2. Google Gemini multimodal audio transcription
    3. Groq Whisper API
    4. OpenAI Whisper API
    5. Local faster-whisper
    """
    if not audio_bytes or len(audio_bytes) < 100:
        return {"success": False, "error": "Audio recording is empty or too short."}

    # 1. Try Google Speech Recognition via speech_recognition (free, keyless, fast)
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        
        # AudioFile accepts file-like objects (BytesIO) containing WAV/AIFF/FLAC
        try:
            with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                audio_data = recognizer.record(source)
                recognized_text = recognizer.recognize_google(audio_data, language=language or "en-US")
                if recognized_text and recognized_text.strip():
                    return _format_success_result(recognized_text, "google_speech_recognition")
        except sr.UnknownValueError:
            logger.info("SpeechRecognition: No speech detected in audio stream.")
        except Exception as sr_err:
            logger.debug(f"Direct BytesIO speech_recognition failed: {sr_err}")
    except ImportError:
        logger.debug("SpeechRecognition library not installed.")
    except Exception as e:
        logger.warning(f"Google speech_recognition error: {e}")

    # 2. Try Google Gemini Multimodal Audio Transcription
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=gemini_key)
            part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type or "audio/wav")
            prompt = (
                "You are an accurate speech-to-text transcriber. Transcribe the following spoken audio "
                "verbatim into text. Return ONLY the transcribed words with natural capitalization and punctuation. "
                "Do NOT include any preamble, explanations, timestamps, or quotes. If there is no speech, return an empty string."
            )
            # Try configured models
            for model_name in [os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"), "gemini-flash-lite-latest", "gemini-2.0-flash"]:
                try:
                    resp = client.models.generate_content(
                        model=model_name,
                        contents=[part, prompt]
                    )
                    text = resp.text.strip() if resp and resp.text else ""
                    if text.startswith('"') and text.endswith('"'):
                        text = text[1:-1].strip()
                    if text:
                        return _format_success_result(text, f"gemini_{model_name}")
                    break
                except Exception as m_err:
                    logger.debug(f"Gemini model {model_name} STT failed: {m_err}")
                    continue
        except Exception as e:
            logger.warning(f"Gemini audio transcription failed: {e}")

    # 3. Try Groq Whisper (ultra-fast cloud Whisper)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            transcription = client.audio.transcriptions.create(
                file=("recording.wav", audio_bytes),
                model="whisper-large-v3",
                language=language
            )
            if transcription.text and transcription.text.strip():
                return _format_success_result(transcription.text, "groq_whisper")
        except Exception as e:
            logger.warning(f"Groq whisper transcription failed: {e}")

    # 4. Try OpenAI Whisper
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            audio_io = io.BytesIO(audio_bytes)
            audio_io.name = "recording.wav"
            resp = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_io,
                language=language
            )
            if resp.text and resp.text.strip():
                return _format_success_result(resp.text, "openai_whisper")
        except Exception as e:
            logger.warning(f"OpenAI whisper transcription failed: {e}")

    # 5. Try local faster-whisper via temp file
    try:
        from faster_whisper import WhisperModel
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            segments, info = model.transcribe(tmp_path, beam_size=2, language=language)
            text = " ".join([seg.text.strip() for seg in segments])
            if text.strip():
                return _format_success_result(text, "faster_whisper_local", detected_language=info.language)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        logger.debug(f"Local faster-whisper unavailable: {e}")

    return {
        "success": False,
        "error": "No speech detected or transcription provider unavailable. Please speak clearly into the microphone."
    }


def transcribe_audio_file(
    audio_path: str,
    language: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transcribes an audio recording file from disk into text.
    """
    if not os.path.exists(audio_path):
        return {"success": False, "error": f"Audio file not found: {audio_path}"}

    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        
        # Determine mime type from extension
        ext = os.path.splitext(audio_path)[1].lower()
        mime_map = {
            ".wav": "audio/wav",
            ".mp3": "audio/mp3",
            ".ogg": "audio/ogg",
            ".webm": "audio/webm",
            ".m4a": "audio/mp4",
        }
        mime_type = mime_map.get(ext, "audio/wav")

        return transcribe_audio(audio_bytes=audio_bytes, language=language, mime_type=mime_type)
    except Exception as e:
        logger.error(f"Failed to read audio file {audio_path}: {e}")
        return {"success": False, "error": str(e)}
