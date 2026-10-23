"""
Conversation history endpoints.
Enables reliable retrieval of past chats across page reloads and server restarts.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, delete

from db.session import get_db_session
from db.repository import ChatRepository
from db.models import Conversation, Message
from api.schemas import ConversationSummary

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])


@router.get("", response_model=List[ConversationSummary], summary="List conversations")
async def list_conversations(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Returns conversation summaries ordered by last update."""
    async with get_db_session() as session:
        repo = ChatRepository(session)
        if user_id:
            convs = await repo.list_user_conversations(user_id, limit=limit, offset=offset)
        else:
            query = select(Conversation).order_by(Conversation.updated_at.desc()).limit(limit).offset(offset)
            res = await session.execute(query)
            convs = list(res.scalars().all())

        results = []
        for c in convs:
            msg_count_q = select(Message).where(Message.conversation_id == c.id)
            msgs = (await session.execute(msg_count_q)).scalars().all()
            results.append(ConversationSummary(
                id=c.id,
                title=c.title,
                created_at=c.created_at.isoformat() if c.created_at else None,
                updated_at=c.updated_at.isoformat() if c.updated_at else None,
                message_count=len(msgs)
            ))
        return results


@router.get("/{conversation_id}", summary="Get conversation messages")
async def get_conversation_history(conversation_id: str):
    """Retrieves full conversation details, chronological messages, and artifacts."""
    async with get_db_session() as session:
        repo = ChatRepository(session)
        conv = await repo.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

        messages = await repo.get_conversation_messages(conversation_id)
        artifacts = await repo.list_artifacts(conversation_id)

        return {
            "conversation": conv.to_dict(),
            "messages": [m.to_dict() for m in messages],
            "artifacts": [a.to_dict() for a in artifacts]
        }


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete conversation")
async def delete_conversation(conversation_id: str):
    """Deletes a conversation and its messages."""
    async with get_db_session() as session:
        query = delete(Conversation).where(Conversation.id == conversation_id)
        await session.execute(query)
