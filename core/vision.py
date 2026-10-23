"""
Multimodal Vision & Screenshot Understanding Engine.
Analyzes code error screenshots, handwritten math, diagrams, and UI wireframes
using Google Gemini / OpenAI vision models with fallback to local OCR.
"""

import os
import base64
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("chatbot.vision")


def encode_image_to_base64(image_path: str) -> Optional[str]:
    """Encodes a local image file to base64 string."""
    if not os.path.exists(image_path):
        return None
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.warning(f"Error reading image: {e}")
        return None


def get_image_mime_type(image_path: str) -> str:
    """Returns MIME type based on extension."""
    ext = os.path.splitext(image_path)[1].lower()
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif"
    }
    return mapping.get(ext, "image/png")


def analyze_image_multimodal(
    image_path: str,
    prompt: str = "Analyze this image in detail.",
    task_mode: str = "general"
) -> Dict[str, Any]:
    """
    Analyzes an image using available multimodal LLMs.
    task_mode options:
    - 'code_error': Screenshot of terminal error or code editor bug.
    - 'handwritten_math': Handwritten equations / assignment problems.
    - 'diagram': System architecture, flowchart, or ER diagram.
    - 'general': General image description and text extraction.
    """
    if not os.path.exists(image_path):
        return {"success": False, "error": f"Image file not found: {image_path}"}

    b64_data = encode_image_to_base64(image_path)
    if not b64_data:
        return {"success": False, "error": "Could not read image data."}

    mime_type = get_image_mime_type(image_path)

    # Contextual prompt tailoring
    tailored_prompt = prompt
    if task_mode == "code_error":
        tailored_prompt = (
            "You are an expert software engineer analyzing a screenshot of code or a terminal error. "
            "1. Extract the exact error message, exception type, and stack trace shown. "
            "2. Identify the line of code causing the failure. "
            "3. Clearly explain the root cause. "
            "4. Provide the complete, corrected Python/target-language code block."
        )
    elif task_mode == "handwritten_math":
        tailored_prompt = (
            "You are a mathematics professor analyzing handwritten notes or equations. "
            "1. Transcribe all mathematical expressions into standard LaTeX notation. "
            "2. State the exact problem to be solved. "
            "3. Provide the step-by-step mathematical derivation and the final boxed solution."
        )
    elif task_mode == "diagram":
        tailored_prompt = (
            "You are a system architect analyzing a diagram. "
            "1. Identify all core components, services, and databases shown. "
            "2. Trace data flow and communication protocols between components. "
            "3. Provide a clear summary and, if applicable, equivalent Mermaid diagram markup."
        )

    # 1. Attempt Google Gemini Multimodal API
    gemini_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    if gemini_key:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=gemini_key)

            # Read image bytes
            with open(image_path, "rb") as f:
                img_bytes = f.read()

            part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[part, tailored_prompt]
            )

            if response and response.text:
                return {
                    "success": True,
                    "engine": "Gemini Multimodal Vision",
                    "model": "gemini-2.5-flash",
                    "task_mode": task_mode,
                    "analysis": response.text.strip(),
                    "image_path": image_path
                }
        except Exception as e:
            logger.warning(f"Gemini vision call failed: {e}")

    # 2. Attempt OpenAI Vision API
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": tailored_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_data}"}}
                        ]
                    }
                ],
                max_tokens=1500
            )
            content = response.choices[0].message.content
            if content:
                return {
                    "success": True,
                    "engine": "OpenAI Vision",
                    "model": "gpt-4o-mini",
                    "task_mode": task_mode,
                    "analysis": content.strip(),
                    "image_path": image_path
                }
        except Exception as e:
            logger.warning(f"OpenAI vision call failed: {e}")

    # 3. Fallback to local OCR tool
    try:
        from tools.extended_tools import read_image_text
        ocr_res = read_image_text(image_path)
        extracted = ocr_res.get("text", "")
        return {
            "success": True,
            "engine": "Local OCR Fallback",
            "model": "pytesseract/ocr",
            "task_mode": task_mode,
            "analysis": f"**Extracted Text from Image:**\n\n```text\n{extracted}\n```\n\n*Note: Cloud vision providers were offline; text was extracted using local OCR.*",
            "image_path": image_path
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Image processing failed across all engines: {str(e)}",
            "image_path": image_path
        }
