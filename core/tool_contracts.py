"""
core/tool_contracts.py — Typed Schemas and Execution Contracts for Tools.

Enforces:
- Strict Pydantic / dataclass schemas for inputs and outputs.
- Permission categories (read_only, user_scoped, consequential, system_write).
- Strict timeout budgets and rate limits per tool.
- Transparent structured error reporting.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class PermissionLevel(str, Enum):
    READ_ONLY = "read_only"
    USER_SCOPED = "user_scoped"
    CONSEQUENTIAL = "consequential"
    SYSTEM_WRITE = "system_write"


class ToolCategory(str, Enum):
    SEARCH = "search"
    KNOWLEDGE = "knowledge"
    CODE = "code"
    VISION = "vision"
    AUDIO = "audio"
    WORKSPACE = "workspace"
    AUTOMATION = "automation"
    PRODUCTIVITY = "productivity"
    DATA = "data"


class ToolMetadata(BaseModel):
    name: str
    description: str
    category: ToolCategory
    permission_level: PermissionLevel = PermissionLevel.READ_ONLY
    timeout_seconds: float = 10.0
    requires_approval: bool = False
    is_idempotent: bool = True
    rate_limit_per_minute: int = 60
    version: str = "1.0.0"


class ToolInvocation(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    user_id: str = "default_user"
    session_id: Optional[str] = None
    approval_token: Optional[str] = None


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    requires_approval: bool = False
    approval_request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
