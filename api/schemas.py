"""
Pydantic Request and Response Schemas for the FastAPI Stateless Backend.
Enforces strict input validation, type safety, and typed error responses.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=30000, description="User input message")
    conversation_id: Optional[str] = Field(None, description="Unique conversation session ID")
    user_id: Optional[str] = Field(None, description="Authenticated or guest user ID")
    provider: Optional[str] = Field("auto", description="Target provider (gemini, groq, openai, ollama, auto)")
    model: Optional[str] = Field(None, description="Specific model name")
    custom_instructions: Optional[str] = Field("", description="Custom directives or system persona")
    idempotency_key: Optional[str] = Field(None, description="Unique client key to prevent duplicate submissions")
    stream: bool = Field(False, description="Whether to stream the response via SSE")


class ArtifactItem(BaseModel):
    name: str
    type: str
    path: str
    url: Optional[str] = None


class ToolExecutionItem(BaseModel):
    name: str
    arguments: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    latency_ms: Optional[float] = None


class ChatResponse(BaseModel):
    success: bool
    conversation_id: str
    message_id: str
    content: str
    provider: str
    model: str
    latency_ms: float
    artifacts: List[Dict[str, Any]] = []
    tools_executed: List[Dict[str, Any]] = []
    fallback_notice: Optional[str] = None
    request_id: Optional[str] = None
    error: Optional[str] = None


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    message_count: int = 0


class HealthCheckResponse(BaseModel):
    status: str # healthy, degraded, unhealthy
    timestamp: str
    database: Dict[str, Any]
    redis: Dict[str, Any]
    providers: Dict[str, Any]
    version: str = "2.0.0"
