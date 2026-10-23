"""
tests/test_speech_to_text.py — Unit tests for Speech-to-Text transcription.
"""

import os
import io
import wave
import pytest
from tools.speech_to_text import transcribe_audio, transcribe_audio_file


def test_transcribe_audio_empty_bytes():
    res = transcribe_audio(b"")
    assert res["success"] is False
    assert "empty" in res["error"].lower() or "short" in res["error"].lower()


def test_transcribe_audio_file_not_found():
    res = transcribe_audio_file("non_existent_file_xyz_123.wav")
    assert res["success"] is False
    assert "not found" in res["error"].lower()


def test_transcribe_audio_wav_silence():
    # Generate 1 second of silence in standard 16kHz mono WAV format
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00" * 32000)
    wav_bytes = wav_io.getvalue()

    res = transcribe_audio(wav_bytes)
    # Silence has no recognizable speech
    assert isinstance(res, dict)
    assert "success" in res


def test_transcribe_audio_mocked_google_stt(monkeypatch):
    import speech_recognition as sr

    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00" * 32000)
    wav_bytes = wav_io.getvalue()

    # Mock recognize_google on the Recognizer
    monkeypatch.setattr(sr.Recognizer, "recognize_google", lambda self, audio, language="en-US": "how to build a chatbot")

    res = transcribe_audio(wav_bytes)
    assert res["success"] is True
    assert res["text"] == "How to build a chatbot"
    assert res["raw_text"] == "how to build a chatbot"
    assert res["provider"] == "google_speech_recognition"


def test_clean_voice_transcript_fillers_and_stutters():
    from core.voice_understanding import clean_voice_transcript
    
    # Fillers and stutters
    raw = "um uh what what is Python?"
    cleaned = clean_voice_transcript(raw)
    assert cleaned == "What is Python?"

    # Phonetic corrections
    raw2 = "tell me about a p i and pie thon"
    cleaned2 = clean_voice_transcript(raw2)
    assert "API" in cleaned2
    assert "Python" in cleaned2

    # Trailing filler
    raw3 = "explain machine learning, you know"
    cleaned3 = clean_voice_transcript(raw3)
    assert cleaned3 == "Explain machine learning"


def test_resolve_incomplete_or_voice_query():
    from core.voice_understanding import resolve_incomplete_or_voice_query

    # Without history -> direct clarification question
    is_inc, q, clar = resolve_incomplete_or_voice_query("What is an...", history=[])
    assert is_inc is True
    assert clar == "What would you like to know about?"

    # With history containing API -> infers "What is an API?"
    history = [
        {"role": "user", "content": "Let's discuss REST APIs today."},
        {"role": "assistant", "content": "Sure, APIs are interfaces for systems to interact."}
    ]
    is_inc, resolved, clar = resolve_incomplete_or_voice_query("What is an...", history=history)
    assert is_inc is True
    assert clar is None
    assert resolved == "What is an API?"

    # Complete query -> no change
    is_inc, resolved, clar = resolve_incomplete_or_voice_query("What is Python?", history=[])
    assert is_inc is False
    assert resolved == "What is Python?"
    assert clar is None
