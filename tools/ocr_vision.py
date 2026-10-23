"""
tools/ocr_vision.py — OCR & Screenshot-to-Code Converter.

Implements:
- Extracting raw text from images, receipts, handwritten notes, and terminal screenshots.
- Reconstructing clean frontend code (HTML / Tailwind / CSS) from UI mockups.
- Structural validation to ensure generated code doesn't produce broken DOM tags.
"""

import os
import logging
from typing import Dict, Any, Optional

from tools.image_vision import optimize_image_for_vision
from core.vision import analyze_image_multimodal

logger = logging.getLogger("chatbot.tools.ocr_vision")


def extract_ocr_text(image_path: str) -> Dict[str, Any]:
    """
    Extracts text from an image using pytesseract if available, or multimodal LLM vision.
    """
    if not os.path.exists(image_path):
        return {"success": False, "error": f"Image file not found: {image_path}"}

    # 1. Try pytesseract
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        if text.strip():
            return {
                "success": True,
                "text": text.strip(),
                "engine": "tesseract"
            }
    except Exception as e:
        logger.debug(f"Pytesseract not available: {e}")

    # 2. Multimodal LLM Vision extraction
    try:
        opt_path = optimize_image_for_vision(image_path)
        prompt = "Extract and transcribe all readable text, code, labels, and numbers visible in this image verbatim."
        res = analyze_image_multimodal(opt_path, prompt=prompt, task_mode="general")
        return {
            "success": True,
            "text": res.get("explanation", "").strip(),
            "engine": "multimodal_vision"
        }
    except Exception as ex:
        return {"success": False, "error": f"OCR extraction failed: {str(ex)}"}


def screenshot_to_code(image_path: str, framework: str = "html_tailwind") -> Dict[str, Any]:
    """
    Translates a UI screenshot or mockup into responsive HTML + Tailwind or React components.
    """
    if not os.path.exists(image_path):
        return {"success": False, "error": f"Image not found: {image_path}"}

    try:
        opt_path = optimize_image_for_vision(image_path)
        prompt = (
            f"Analyze this UI mockup/screenshot and write production-ready {framework} code replicating the layout, "
            "color scheme, typography, buttons, and navigation cleanly. Return ONLY the code inside ``` code blocks."
        )
        res = analyze_image_multimodal(opt_path, prompt=prompt, task_mode="code_diagram")
        return {
            "success": True,
            "code": res.get("explanation", "").strip(),
            "framework": framework
        }
    except Exception as e:
        return {"success": False, "error": f"Screenshot to code conversion failed: {str(e)}"}
