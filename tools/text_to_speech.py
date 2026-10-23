"""
tools/text_to_speech.py — Text-to-Speech Audio Synthesis Engine.

Implements Capability 14 (TTS):
- Converts chatbot response text into natural spoken audio (.mp3).
- Supports edge-tts (Microsoft neural voices, zero-cost, no API key),
  or OpenAI TTS (tts-1) when configured.
- Saves synthesized speech as an artifact for UI playback.
"""

import os
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional

from services.artifact_service import default_artifact_service

logger = logging.getLogger("chatbot.tools.text_to_speech")


def synthesize_speech(
    text: str,
    voice: str = "en-US-AriaNeural",
    user_id: str = "default_user",
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Synthesizes speech audio from text.
    Uses edge-tts or OpenAI TTS and returns artifact metadata.
    """
    clean_text = text.strip()
    if not clean_text:
        return {"success": False, "error": "No text provided for speech synthesis."}

    # Truncate text if too long for a single audio turn
    synthesized_text = clean_text[:2000]
    out_fname = f"speech_{uuid.uuid4().hex[:8]}.mp3"
    out_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, out_fname)

    # 1. Try edge-tts (neural quality, no credentials required)
    try:
        import edge_tts

        async def _run_edge_tts():
            communicate = edge_tts.Communicate(synthesized_text, voice)
            await communicate.save(out_path)

        asyncio.run(_run_edge_tts())

        if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
            with open(out_path, "rb") as f:
                art = default_artifact_service.save_artifact(
                    file_name=out_fname,
                    content=f.read(),
                    user_id=user_id,
                    session_id=session_id,
                    mime_type="audio/mpeg"
                )
            return {
                "success": True,
                "file_path": out_path,
                "artifact_id": art.artifact_id,
                "download_url": art.preview_url,
                "voice": voice,
                "provider": "edge_tts"
            }
    except Exception as e:
        logger.warning(f"edge-tts synthesis failed: {e}")

    # 2. Try OpenAI TTS if configured
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            resp = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=synthesized_text
            )
            resp.stream_to_file(out_path)
            with open(out_path, "rb") as f:
                art = default_artifact_service.save_artifact(
                    file_name=out_fname,
                    content=f.read(),
                    user_id=user_id,
                    session_id=session_id,
                    mime_type="audio/mpeg"
                )
            return {
                "success": True,
                "file_path": out_path,
                "artifact_id": art.artifact_id,
                "download_url": art.preview_url,
                "provider": "openai_tts"
            }
        except Exception as e:
            logger.warning(f"OpenAI TTS synthesis failed: {e}")

    return {
        "success": False,
        "error": "Failed to synthesize speech. Ensure edge-tts or openai is configured."
    }
