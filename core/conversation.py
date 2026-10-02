"""
Conversation state and session manager.
Tracks messages, attached files, project context, and generated artifacts.
"""

from typing import List, Dict, Any, Optional
import json
import os
import uuid
from datetime import datetime

class ConversationSession:
    def __init__(self, session_id: Optional[str] = None, title: str = "New Conversation"):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.title = title
        self.created_at = datetime.now().isoformat()
        self.messages: List[Dict[str, Any]] = []
        self.attached_files: List[Dict[str, Any]] = []
        self.project_context: Dict[str, Any] = {
            "project_goal": None,
            "tech_stack": None,
            "pending_tasks": [],
            "decisions": [],
            "generated_files": []
        }

    def add_message(self, role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None, tool_call_id: Optional[str] = None):
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if tool_call_id:
            msg["tool_call_id"] = tool_call_id
        self.messages.append(msg)

    def attach_file(self, filename: str, file_path: str, file_type: str, metadata: Optional[Dict[str, Any]] = None):
        self.attached_files.append({
            "name": filename,
            "path": file_path,
            "type": file_type,
            "metadata": metadata or {}
        })

    def clear(self):
        self.messages.clear()
        self.attached_files.clear()
        self.project_context = {
            "project_goal": None,
            "tech_stack": None,
            "pending_tasks": [],
            "decisions": [],
            "generated_files": []
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "messages": self.messages,
            "attached_files": self.attached_files,
            "project_context": self.project_context
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationSession":
        session = cls(session_id=data.get("session_id"), title=data.get("title", "New Conversation"))
        session.created_at = data.get("created_at", datetime.now().isoformat())
        session.messages = data.get("messages", [])
        session.attached_files = data.get("attached_files", [])
        session.project_context = data.get("project_context", {})
        return session
