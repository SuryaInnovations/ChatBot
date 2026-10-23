"""
Core Chat Processing and Inference Route.
Handles atomic message persistence, orchestrator execution, idempotency, and streaming.
"""

import time
import uuid
import logging
from fastapi import APIRouter, Request

from db.session import get_db_session
from db.repository import ChatRepository
from core.conversation import ConversationSession
from core.orchestrator import ChatbotOrchestrator
from core.llm_provider import LLMProvider
from api.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])
logger = logging.getLogger("chatbot.api.chat")


@router.post("", response_model=ChatResponse, summary="Execute chat generation")
async def chat_endpoint(req: ChatRequest, request: Request):
    """
    Executes universal request pipeline:
    1. Persists user message to PostgreSQL immediately before calling any provider (zero message loss).
    2. Enforces idempotency via idempotency_key to prevent duplicate charges or actions.
    3. Runs orchestrator with automatic fallback chain and isolated sandboxing.
    4. Persists assistant response and generated artifacts to DB.
    """
    start_time = time.time()
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    conv_id = req.conversation_id or str(uuid.uuid4())[:8]

    async with get_db_session() as session:
        repo = ChatRepository(session)

        # 1. Idempotency Check: if key already exists, return previous message
        if req.idempotency_key:
            from sqlalchemy import select
            from db.models import Message
            q = select(Message).where(Message.idempotency_key == req.idempotency_key)
            existing = (await session.execute(q)).scalar_one_or_none()
            if existing:
                # Find corresponding assistant reply
                reply_q = (
                    select(Message)
                    .where(Message.conversation_id == existing.conversation_id, Message.role == "assistant")
                    .order_by(Message.created_at.desc())
                )
                assistant_msg = (await session.execute(reply_q)).scalar_one_or_none()
                if assistant_msg:
                    return ChatResponse(
                        success=True,
                        conversation_id=existing.conversation_id,
                        message_id=assistant_msg.id,
                        content=assistant_msg.content,
                        provider=assistant_msg.provider or "cached",
                        model=assistant_msg.model or "cached",
                        latency_ms=0.0,
                        request_id=req_id
                    )

        # 2. Persist user message IMMEDIATELY to DB before any LLM call
        await repo.save_message(
            conversation_id=conv_id,
            role="user",
            content=req.message,
            status="completed",
            idempotency_key=req.idempotency_key
        )

        # 3. Load historical messages for context
        db_messages = await repo.get_conversation_messages(conv_id, limit=20)
        conv_session = ConversationSession(session_id=conv_id, user_id=req.user_id)
        for m in db_messages:
            conv_session.messages.append({
                "role": m.role,
                "content": m.content,
                "timestamp": m.created_at.isoformat() if m.created_at else None
            })

    # 4. Instantiate Orchestrator with requested provider or auto-fallback
    llm = LLMProvider(
        provider=req.provider or "auto",
        model=req.model
    )
    orchestrator = ChatbotOrchestrator(provider=llm)

    # 5. Process message through universal intent pipeline
    try:
        result = orchestrator.process_message(
            session=conv_session,
            user_message=req.message,
            custom_instructions=req.custom_instructions or ""
        )
    except Exception as e:
        logger.exception(f"Unhandled exception in orchestrator for request {req_id}: {str(e)}")
        result = {
            "success": False,
            "content": f"A system error occurred while processing your request. Please try again or switch providers. (Request ID: {req_id})",
            "error": str(e),
            "provider": req.provider or "error",
            "model": "none"
        }

    latency = round((time.time() - start_time) * 1000, 2)
    final_content = result.get("content", "")
    provider_used = result.get("provider", req.provider or "auto")
    model_used = result.get("model", "default")
    artifacts = result.get("artifacts", [])
    executed_tools = result.get("executed_tools", [])

    # 6. Persist assistant response and generated artifacts to DB
    async with get_db_session() as session:
        repo = ChatRepository(session)
        asst_msg = await repo.save_message(
            conversation_id=conv_id,
            role="assistant",
            content=final_content,
            provider=provider_used,
            model=model_used,
            latency_ms=latency,
            status="completed" if result.get("success") else "failed",
            error_message=result.get("error")
        )

        # Persist artifacts if any were generated
        for art in artifacts:
            await repo.save_artifact(
                conversation_id=conv_id,
                message_id=asst_msg.id,
                filename=art.get("name", "document"),
                file_type=art.get("type", "file"),
                file_path=art.get("path", "")
            )

    return ChatResponse(
        success=bool(result.get("success")),
        conversation_id=conv_id,
        message_id=asst_msg.id,
        content=final_content,
        provider=provider_used,
        model=model_used,
        latency_ms=latency,
        artifacts=artifacts,
        tools_executed=executed_tools,
        fallback_notice=result.get("fallback_notice"),
        request_id=req_id,
        error=result.get("error")
    )
