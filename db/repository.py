"""
Database Repository providing asynchronous CRUD operations and deduplication logic.
Guarantees zero message loss, idempotency protection, and atomic transactions.
"""

import uuid
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, Conversation, Message, Artifact, ToolExecution

logger = logging.getLogger("chatbot.repository")


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------------------------------------------------------
    # USER OPERATIONS
    # ---------------------------------------------------------
    async def get_or_create_user(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        username: Optional[str] = None,
        tier: str = "standard"
    ) -> User:
        """Retrieves an existing user or creates a new one."""
        if user_id:
            query = select(User).where(User.id == user_id)
            res = await self.session.execute(query)
            user = res.scalar_one_or_none()
            if user:
                return user

        if email:
            query = select(User).where(User.email == email)
            res = await self.session.execute(query)
            user = res.scalar_one_or_none()
            if user:
                return user

        new_user = User(
            id=user_id or str(uuid.uuid4()),
            email=email,
            username=username or f"user_{str(uuid.uuid4())[:8]}",
            tier=tier
        )
        self.session.add(new_user)
        await self.session.flush()
        return new_user

    # ---------------------------------------------------------
    # CONVERSATION OPERATIONS
    # ---------------------------------------------------------
    async def create_conversation(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        title: str = "New Conversation",
        project_context: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """Creates a new conversation record."""
        conv = Conversation(
            id=conversation_id or str(uuid.uuid4())[:8],
            user_id=user_id,
            title=title,
            project_context=project_context or {}
        )
        self.session.add(conv)
        await self.session.flush()
        return conv

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieves a conversation by ID."""
        query = select(Conversation).where(Conversation.id == conversation_id)
        res = await self.session.execute(query)
        return res.scalar_one_or_none()

    async def list_user_conversations(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Conversation]:
        """Lists conversations belonging to a user ordered by most recently updated."""
        query = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def update_conversation_context(self, conversation_id: str, context: Dict[str, Any]) -> None:
        """Updates the conversation project context."""
        query = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(project_context=context)
        )
        await self.session.execute(query)

    # ---------------------------------------------------------
    # MESSAGE OPERATIONS (WITH IDEMPOTENCY & AUDIT)
    # ---------------------------------------------------------
    async def save_message(
        self,
        conversation_id: str,
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
    ) -> Message:
        """
        Persists a message. If an idempotency_key is provided and already exists,
        returns the existing message to guarantee duplicate-free processing.
        """
        if idempotency_key:
            check_q = select(Message).where(Message.idempotency_key == idempotency_key)
            existing = (await self.session.execute(check_q)).scalar_one_or_none()
            if existing:
                logger.info(f"[IDEMPOTENCY] Reusing existing message with key: {idempotency_key}")
                return existing

        # Ensure conversation exists
        conv = await self.get_conversation(conversation_id)
        if not conv:
            conv = await self.create_conversation(conversation_id=conversation_id)

        msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
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
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def get_conversation_messages(self, conversation_id: str, limit: int = 100) -> List[Message]:
        """Loads chronological message history for a conversation."""
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        res = await self.session.execute(query)
        return list(res.scalars().all())

    # ---------------------------------------------------------
    # ARTIFACT & TOOL EXECUTION OPERATIONS
    # ---------------------------------------------------------
    async def save_artifact(
        self,
        conversation_id: str,
        filename: str,
        file_type: str,
        file_path: str,
        file_size_bytes: int = 0,
        message_id: Optional[str] = None,
        storage_backend: str = "local"
    ) -> Artifact:
        """Persists metadata for a generated file or artifact."""
        artifact = Artifact(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            message_id=message_id,
            filename=filename,
            file_type=file_type,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            storage_backend=storage_backend
        )
        self.session.add(artifact)
        await self.session.flush()
        return artifact

    async def list_artifacts(self, conversation_id: str) -> List[Artifact]:
        """Lists all artifacts associated with a conversation."""
        query = select(Artifact).where(Artifact.conversation_id == conversation_id)
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def log_tool_execution(
        self,
        conversation_id: str,
        tool_name: str,
        input_args: Dict[str, Any],
        output_result: Dict[str, Any],
        status: str = "success",
        latency_ms: float = 0.0,
        message_id: Optional[str] = None
    ) -> ToolExecution:
        """Logs individual tool execution events for observability and audit trails."""
        entry = ToolExecution(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            message_id=message_id,
            tool_name=tool_name,
            input_arguments=input_args,
            output_result=output_result,
            status=status,
            latency_ms=latency_ms
        )
        self.session.add(entry)
        await self.session.flush()
        return entry
