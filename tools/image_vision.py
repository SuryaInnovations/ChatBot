"""
tools/image_vision.py — Multimodal Image Understanding & Safe Optimization.

Implements Capability 05:
- Ingests screenshots, architecture diagrams, charts, UI mockups, and error photos.
- Uses Pillow to safely validate, downscale (max 1920x1080), and compress images.
- Connects to multimodal vision models with specialized task modes.
- Prevents memory exhaustion from oversized image bombs.
"""

import os
import logging
from typing import Dict, Any
from PIL import Image

from core.vision import analyze_image_multimodal

logger = logging.getLogger("chatbot.tools.image_vision")

MAX_DIMENSION = 1920
MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB limit


def optimize_image_for_vision(image_path: str, max_dimension: int = MAX_DIMENSION) -> str:
    """
    Validates and optimizes an image (resizing if oversized, converting RGBA to RGB if saving JPEG).
    Returns path to optimized image.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    size = os.path.getsize(image_path)
    if size > MAX_IMAGE_BYTES:
        raise ValueError(f"Image exceeds maximum size of 20 MB ({round(size / 1024 / 1024, 2)} MB).")

    with Image.open(image_path) as img:
        width, height = img.size
        if width <= max_dimension and height <= max_dimension and size < 2 * 1024 * 1024:
            return image_path  # Already optimal

        # Calculate new dimensions preserving aspect ratio
        ratio = min(max_dimension / width, max_dimension / height)
        new_size = (int(width * ratio), int(height * ratio))
        resized = img.resize(new_size, Image.Resampling.LANCZOS)

        base_dir = os.path.dirname(image_path)
        opt_path = os.path.join(base_dir, f"opt_{os.path.basename(image_path)}")
        if resized.mode in ("RGBA", "P"):
            resized = resized.convert("RGB")
        resized.save(opt_path, "JPEG", quality=85, optimize=True)
        return opt_path


def analyze_image(
    image_path: str,
    prompt: str = "Explain what is shown in this image in detail.",
    task_mode: str = "general"
) -> Dict[str, Any]:
    """
    Analyzes an image with multimodal LLM after safe optimization.
    Task modes: "general", "code_diagram", "error_screenshot", "chart_analysis".
    """
    try:
        opt_path = optimize_image_for_vision(image_path)
        logger.info(f"Analyzing image '{opt_path}' with prompt: {prompt[:80]}")
        res = analyze_image_multimodal(opt_path, prompt=prompt, task_mode=task_mode)
        return res
    except Exception as e:
        logger.error(f"Failed to analyze image {image_path}: {e}")
        return {
            "success": False,
            "error": str(e),
            "explanation": f"Unable to process image: {str(e)}"
        }
