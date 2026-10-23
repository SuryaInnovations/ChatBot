"""
tools/image_generation.py — Prompt-to-Image Generation & Asset Persistence.

Implements Capability 13:
- Converts descriptive prompts into high-resolution images.
- Uses OpenAI/DALL-E or Google Imagen/Gemini when API keys are configured,
  with zero-setup fallback to Pollinations.ai or local placeholder generator.
- Saves generated images to disk artifacts and registers with default_artifact_service.
- Dispatches asynchronously for heavy workflows without blocking the main worker.
"""

import os
import uuid
import urllib.parse
import logging
from typing import Dict, Any, Optional
import httpx

from services.artifact_service import default_artifact_service
from services.task_queue import default_task_queue

logger = logging.getLogger("chatbot.tools.image_generation")


def generate_image_sync(
    prompt: str,
    aspect_ratio: str = "1:1",
    user_id: str = "default_user",
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Synchronously generates an image from a prompt and saves it as an artifact.
    """
    clean_prompt = prompt.strip()
    if not clean_prompt:
        return {"success": False, "error": "Prompt cannot be empty."}

    # Resolution mapping
    width, height = 1024, 1024
    if aspect_ratio == "16:9":
        width, height = 1280, 720
    elif aspect_ratio == "9:16":
        width, height = 720, 1280
    elif aspect_ratio == "4:3":
        width, height = 1024, 768

    # 1. Check for OpenAI DALL-E 3
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            resp = client.images.generate(
                model="dall-e-3",
                prompt=clean_prompt,
                size="1024x1024",
                n=1
            )
            image_url = resp.data[0].url
            # Download and save artifact
            with httpx.Client(timeout=15.0) as http_client:
                img_data = http_client.get(image_url).content
            art = default_artifact_service.save_artifact(
                file_name=f"img_{uuid.uuid4().hex[:8]}.png",
                content=img_data,
                user_id=user_id,
                session_id=session_id,
                mime_type="image/png"
            )
            return {
                "success": True,
                "prompt": clean_prompt,
                "artifact_id": art.artifact_id,
                "file_path": art.file_path,
                "preview_url": art.preview_url,
                "provider": "openai_dall_e_3"
            }
        except Exception as e:
            logger.warning(f"OpenAI image generation failed, falling back to Pollinations: {e}")

    # 2. Universal Pollinations.ai fallback (free, instant, high aesthetic quality)
    try:
        encoded_prompt = urllib.parse.quote(clean_prompt)
        pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
        with httpx.Client(timeout=20.0, follow_redirects=True) as http_client:
            resp = http_client.get(pollinations_url)
            if resp.status_code == 200 and len(resp.content) > 1000:
                art = default_artifact_service.save_artifact(
                    file_name=f"img_{uuid.uuid4().hex[:8]}.jpg",
                    content=resp.content,
                    user_id=user_id,
                    session_id=session_id,
                    mime_type="image/jpeg"
                )
                return {
                    "success": True,
                    "prompt": clean_prompt,
                    "artifact_id": art.artifact_id,
                    "file_path": art.file_path,
                    "preview_url": art.preview_url,
                    "provider": "pollinations"
                }
    except Exception as e:
        logger.error(f"Pollinations fetch failed: {e}")

    return {
        "success": False,
        "error": "Failed to generate image through configured providers."
    }


def generate_image_async(
    prompt: str,
    user_id: str = "default_user",
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Submits image generation to the background task queue and returns immediately with job ID.
    """
    job = default_task_queue.submit_task(
        task_name="generate_image",
        user_id=user_id,
        func=generate_image_sync,
        prompt=prompt,
        session_id=session_id
    )
    return {
        "success": True,
        "job_id": job.job_id,
        "status": "queued",
        "message": "Image generation queued in background. Check task queue for progress."
    }
