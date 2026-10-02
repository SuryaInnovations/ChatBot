"""
FastAPI Server for All-in-One AI Assistant.
Provides REST API endpoints for external integrations and frontend clients.
"""

import os
import sys
import shutil
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from core.conversation import ConversationSession
from core.llm_provider import LLMProvider
from core.orchestrator import ChatbotOrchestrator
from tools.file_analyzer import analyze_file

app = FastAPI(
    title="All-in-One AI Assistant API",
    description="REST API for the autonomous multi-tool problem-solving AI assistant.",
    version="1.0.0"
)

# In-memory session store
sessions: Dict[str, ConversationSession] = {}

class ChatRequest(BaseModel):
    session_id: Optional[str] = "default"
    message: str
    provider: Optional[str] = "groq"
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

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "All-in-One AI Assistant API",
        "active_sessions": len(sessions)
    }

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    session_id = req.session_id or "default"
    if session_id not in sessions:
        sessions[session_id] = ConversationSession(session_id=session_id)
    
    session = sessions[session_id]
    llm = LLMProvider(
        provider=req.provider or "groq",
        model=req.model,
        api_key=req.api_key
    )
    orchestrator = ChatbotOrchestrator(provider=llm)

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
