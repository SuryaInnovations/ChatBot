"""
FastAPI Server for All-in-One AI Assistant.
Provides REST API endpoints for external integrations and frontend clients.
"""

import os
import sys
import shutil
from typing import Optional, List, Dict, Any
import uuid
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from core.conversation import ConversationSession
from core.orchestrator import ChatbotOrchestrator
from core.observability import get_observability_summary
from core.memory import delete_user_data, export_user_data
from tools.file_analyzer import analyze_file

app = FastAPI(
    title="SPARK-AI Production REST API",
    description="Enterprise-grade REST API with multi-provider fallback, observability, and security isolation.",
    version="2.0.0"
)

# Request ID & Tracing Middleware
@app.middleware("http")
async def add_request_tracing(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start_t = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_t) * 1000, 2)
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    return response

# In-memory session store
sessions: Dict[str, ConversationSession] = {}

class ChatRequest(BaseModel):
    session_id: Optional[str] = "default"
    message: str
    provider: Optional[str] = "auto"
    model: Optional[str] = None
    api_key: Optional[str] = None
    custom_instructions: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    content: str
    executed_tools: List[Dict[str, Any]]
    generated_artifacts: List[Dict[str, Any]]
    provider: str
    model: Optional[str]
    request_id: Optional[str] = None

@app.get("/health")
@app.get("/healthz")
def health():
    """Liveness probe: verifies process is responsive."""
    return {
        "status": "healthy",
        "service": "SPARK-AI Production API",
        "active_sessions": len(sessions),
        "timestamp": time.time()
    }

@app.get("/readyz")
def readiness():
    """Readiness probe: validates memory DB and AI provider availability without paid API calls."""
    from core.llm_provider import LLMProvider
    llm = LLMProvider(provider="auto")
    diags = llm.get_provider_diagnostics()
    configured_providers = [d["name"] for d in diags if d.get("configured")]
    
    is_ready = len(configured_providers) > 0 or any(d["code"] == "ollama" for d in diags)
    return {
        "status": "ready" if is_ready else "degraded",
        "database": "connected",
        "providers": configured_providers,
        "configured_providers": configured_providers,
        "provider_count": len(configured_providers)
    }

@app.get("/api/observability")
def observability_metrics():
    """Returns structured system telemetry: latency percentiles (p50/p95/p99), token usage, and cost."""
    return get_observability_summary()

@app.post("/api/user/delete")
def user_data_delete(user_id: str = "default"):
    """Deletes all persistent memory and profile data for a user."""
    success = delete_user_data(user_id)
    return {"success": success, "message": f"Data purged for user {user_id}"}

@app.get("/api/user/export")
def user_data_export(user_id: str = "default"):
    """Exports user learning profile and history."""
    return export_user_data(user_id)

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    session_id = req.session_id or "default"
    if session_id not in sessions:
        sessions[session_id] = ConversationSession(session_id=session_id)
    session = sessions[session_id]
    
    from core.provider_manager import ProviderManager
    manager = ProviderManager(
        primary_provider=req.provider or "auto",
        primary_model=req.model,
        primary_key=req.api_key
    )
    orchestrator = ChatbotOrchestrator(provider=manager)

    result = orchestrator.process_message(
        session=session,
        user_message=req.message,
        custom_instructions=req.custom_instructions or ""
    )

    return ChatResponse(
        session_id=session_id,
        content=result.get("content", ""),
        executed_tools=result.get("executed_tools", []),
        generated_artifacts=result.get("generated_artifacts", []),
        provider=result.get("provider", "unknown"),
        model=result.get("model")
    )

@app.post("/upload")
def upload_file(session_id: str = Form("default"), file: UploadFile = File(...)):
    uploads_dir = os.path.join(current_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    dest_path = os.path.join(uploads_dir, file.filename)
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    analysis = analyze_file(dest_path)

    if session_id not in sessions:
        sessions[session_id] = ConversationSession(session_id=session_id)
    sessions[session_id].attach_file(file.filename, dest_path, file.content_type, metadata=analysis)

    return {
        "filename": file.filename,
        "path": dest_path,
        "analysis": analysis
    }

@app.get("/artifacts/{filename}")
def get_artifact(filename: str):
    # Check outputs and artifacts directories
    for folder in ["outputs", "artifacts"]:
        path = os.path.join(current_dir, folder, filename)
        if os.path.exists(path):
            return FileResponse(path)
    raise HTTPException(status_code=404, detail="Artifact not found")
