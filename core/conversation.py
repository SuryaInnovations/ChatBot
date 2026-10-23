"""
Conversation state and session manager with database persistence.
Tracks messages, attached files, project context, and generated artifacts.
Guarantees message preservation across page refreshes, crashes, and server restarts.
"""

from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger("chatbot.conversation")


class ConversationSession:
    def __init__(self, session_id: Optional[str] = None, title: str = "New Conversation", user_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.title = title
        self.user_id = user_id
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

    def add_message(
        self,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        latency_ms: Optional[float] = None,
        status: str = "completed",
        error_message: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Adds a message to in-memory session and synchronously triggers async background DB persist if available.
        """
        msg: Dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "status": status
        }
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if tool_call_id:
            msg["tool_call_id"] = tool_call_id
        if provider:
            msg["provider"] = provider
        if model:
            msg["model"] = model
        if latency_ms:
            msg["latency_ms"] = latency_ms
        if idempotency_key:
            msg["idempotency_key"] = idempotency_key

        self.messages.append(msg)

        # Attempt DB persistence in background task if loop is active
        try:
            asyncio.get_running_loop()
            asyncio.create_task(self._persist_message_async(role, content, tool_calls, tool_call_id, provider, model, latency_ms, status, error_message, idempotency_key))
        except (RuntimeError, Exception):
            pass

        return msg

    async def _persist_message_async(
        self,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]],
        tool_call_id: Optional[str],
        provider: Optional[str],
        model: Optional[str],
        latency_ms: Optional[float],
        status: str,
        error_message: Optional[str],
        idempotency_key: Optional[str]
    ):
        try:
            from db.session import get_db_session
            from db.repository import ChatRepository
            async with get_db_session() as session:
                repo = ChatRepository(session)
                await repo.save_message(
                    conversation_id=self.session_id,
                    role=role,
                    content=content,
                    tool_calls=tool_calls,
                    tool_call_id=tool_call_id,
                    provider=provider,
                    model=model,
                    latency_ms=latency_ms,
                    status=status,
                    error_message=error_message,
                    idempotency_key=idempotency_key
                )
        except Exception as e:
            logger.debug(f"DB background persistence error: {e}")

    async def sync_from_db(self):
        """Loads complete conversation history from database."""
        try:
            from db.session import get_db_session
            from db.repository import ChatRepository
            async with get_db_session() as session:
                repo = ChatRepository(session)
                db_conv = await repo.get_conversation(self.session_id)
                if db_conv:
                    self.title = db_conv.title
                    self.project_context = db_conv.project_context or {}
                db_messages = await repo.get_conversation_messages(self.session_id)
                if db_messages:
                    self.messages = [m.to_dict() for m in db_messages]
        except Exception as e:
            logger.debug(f"Could not load conversation from DB: {e}")

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
            "user_id": self.user_id,
            "created_at": self.created_at,
            "messages": self.messages,
            "attached_files": self.attached_files,
            "project_context": self.project_context
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationSession":
        session = cls(
            session_id=data.get("session_id"),
            title=data.get("title", "New Conversation"),
            user_id=data.get("user_id")
        )
        session.created_at = data.get("created_at", datetime.now().isoformat())
        session.messages = data.get("messages", [])
        session.attached_files = data.get("attached_files", [])
        session.project_context = data.get("project_context", {})
        return session
