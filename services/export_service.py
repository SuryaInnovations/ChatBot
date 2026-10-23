"""
services/export_service.py — Data & Session Export Service (Markdown, JSON, ZIP).

Allows users to export:
- Entire conversation history with citations and timestamps.
- Generated code and workspace files bundled into a ZIP archive.
- Analysis reports in formatted Markdown or PDF.
"""

import io
import json
import zipfile
import logging
from typing import Dict, Any, List
from security.privacy import default_privacy_manager

logger = logging.getLogger("chatbot.services.export_service")


class ExportService:
    def export_conversation_markdown(self, session_id: str, messages: List[Dict[str, Any]]) -> str:
        """Formats conversation into readable markdown document with citations."""
        lines = [f"# Conversation Export ({session_id})\n"]
        for m in messages:
            role = m.get("role", "user").capitalize()
            content = m.get("content", "")
            lines.append(f"### {role}:\n{content}\n")
        return "\n".join(lines)

    def export_conversation_json(self, session_id: str, messages: List[Dict[str, Any]], user_id: str = "user") -> str:
        """Exports sanitized conversation history as a JSON string."""
        raw_payload = {
            "session_id": session_id,
            "user_id": user_id,
            "message_count": len(messages),
            "messages": messages
        }
        cleaned = default_privacy_manager.scrub_export_data(raw_payload)
        return json.dumps(cleaned, indent=2)

    def bundle_files_to_zip(self, files: Dict[str, str], zip_filename: str = "project.zip") -> bytes:
        """
        Zips a dictionary of {relative_path: text_content} into in-memory bytes.
        """
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for rel_path, content in files.items():
                zf.writestr(rel_path, content)
        buf.seek(0)
        return buf.getvalue()


default_export_service = ExportService()
