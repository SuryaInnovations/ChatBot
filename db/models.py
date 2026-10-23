"""
SQLAlchemy ORM Models for PostgreSQL (with SQLite fallback).
Provides indexed relational schemas for users, conversations, messages, artifacts, and tool logs.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    Index
)
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(DeclarativeBase):
    pass


def get_utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=True)
    username = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)
    tier = Column(String(50), default="standard", nullable=False) # standard, premium, internal
    is_active = Column(Boolean, default=True, nullable=False)
    storage_used_bytes = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "tier": self.tier,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    title = Column(String(255), default="New Conversation", nullable=False)
    project_context = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    artifacts = relationship("Artifact", back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_conversation_user_updated", "user_id", "updated_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "project_context": self.project_context or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    role = Column(String(50), nullable=False, index=True) # user, assistant, system, tool
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)
    tool_call_id = Column(String(100), nullable=True)
    
    # Metadata for observability and tracking
    provider = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    latency_ms = Column(Float, nullable=True)
    status = Column(String(50), default="completed", nullable=False) # pending, completed, failed
    error_message = Column(Text, nullable=True)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("idx_message_conv_created", "conversation_id", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
            "provider": self.provider,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    message_id = Column(String(36), nullable=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_size_bytes = Column(Integer, default=0, nullable=False)
    storage_backend = Column(String(50), default="local", nullable=False) # local, s3, minio
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="artifacts")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), index=True, nullable=False)
    message_id = Column(String(36), nullable=True)
    tool_name = Column(String(100), index=True, nullable=False)
    input_arguments = Column(JSON, nullable=True)
    output_result = Column(JSON, nullable=True)
    status = Column(String(50), default="success", nullable=False) # success, error, timeout
    latency_ms = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "tool_name": self.tool_name,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
