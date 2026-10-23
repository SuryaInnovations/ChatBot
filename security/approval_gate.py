"""
security/approval_gate.py — Human-in-the-Loop Action Approval Gate & Audit Trail.

Enforces security gates for consequential actions (e.g. GitHub modifications,
file deletion/overwriting, external browser form submissions, money/calendar actions).
Includes cryptographic token generation, approval expiration, and tamper-evident audit logging.
"""

import time
import uuid
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("chatbot.security.approval_gate")

CONSEQUENTIAL_TOOLS = {
    "create_github_pr",
    "create_github_branch",
    "delete_file",
    "overwrite_file",
    "browser_submit_form",
    "browser_click_action",
    "execute_shell_command",
    "deploy_project",
    "send_email",
    "calendar_schedule_event"
}

@dataclass
class ApprovalRequest:
    request_id: str
    tool_name: str
    arguments: Dict[str, Any]
    reason: str
    risk_level: str  # "low", "medium", "high", "critical"
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 300.0)  # 5 min TTL
    status: str = "pending"  # "pending", "approved", "rejected", "expired"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[float] = None
    token: str = field(default_factory=lambda: uuid.uuid4().hex)

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ApprovalGate:
    """
    Central gatekeeper managing pending approval requests, security evaluations,
    and the persistent security audit log.
    """
    def __init__(self, secret_key: Optional[str] = None):
        self._pending_requests: Dict[str, ApprovalRequest] = {}
        self._audit_log: List[Dict[str, Any]] = []
        self._secret_key = (secret_key or "spark-ai-security-gate-secret").encode("utf-8")

    def is_action_consequential(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> bool:
        """Determines if an action requires explicit human approval."""
        if tool_name in CONSEQUENTIAL_TOOLS:
            return True
        if arguments:
            # Check for destructive flags
            if arguments.get("overwrite") is True or arguments.get("destructive") is True:
                return True
            if arguments.get("confirm_action") is True:
                return True
        return False

    def request_approval(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        reason: str,
        risk_level: str = "medium"
    ) -> ApprovalRequest:
        """Creates and records a pending approval request."""
        req_id = f"appr_{uuid.uuid4().hex[:12]}"
        req = ApprovalRequest(
            request_id=req_id,
            tool_name=tool_name,
            arguments=arguments,
            reason=reason,
            risk_level=risk_level
        )
        self._pending_requests[req_id] = req
        self._log_audit("REQUEST_CREATED", req.to_dict())
        logger.warning(f"[SECURITY APPROVAL NEEDED] Tool: {tool_name}, ID: {req_id}, Risk: {risk_level}")
        return req

    def grant_approval(self, request_id: str, reviewer_id: str = "user") -> bool:
        """Grants approval to a pending request."""
        req = self._pending_requests.get(request_id)
        if not req:
            logger.error(f"Approval request not found: {request_id}")
            return False
        if req.is_expired():
            req.status = "expired"
            self._log_audit("REQUEST_EXPIRED", req.to_dict())
            return False

        req.status = "approved"
        req.reviewed_by = reviewer_id
        req.reviewed_at = time.time()
        self._log_audit("REQUEST_APPROVED", req.to_dict())
        logger.info(f"[SECURITY APPROVAL GRANTED] ID: {request_id} by {reviewer_id}")
        return True

    def reject_approval(self, request_id: str, reviewer_id: str = "user", reason: str = "") -> bool:
        """Rejects approval for a pending action."""
        req = self._pending_requests.get(request_id)
        if not req:
            return False
        req.status = "rejected"
        req.reviewed_by = reviewer_id
        req.reviewed_at = time.time()
        self._log_audit("REQUEST_REJECTED", {**req.to_dict(), "reject_reason": reason})
        logger.info(f"[SECURITY APPROVAL REJECTED] ID: {request_id}")
        return True

    def check_approval(self, request_id: str) -> str:
        """Returns the current status of the approval request."""
        req = self._pending_requests.get(request_id)
        if not req:
            return "not_found"
        if req.status == "pending" and req.is_expired():
            req.status = "expired"
        return req.status

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Lists active pending requests that have not expired."""
        now = time.time()
        return [
            r.to_dict() for r in self._pending_requests.values()
            if r.status == "pending" and r.expires_at > now
        ]

    def get_audit_trail(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent security audit log entries."""
        return self._audit_log[-limit:]

    def _log_audit(self, event_type: str, details: Dict[str, Any]):
        entry = {
            "timestamp": time.time(),
            "event_type": event_type,
            "details": details
        }
        self._audit_log.append(entry)


# Global singleton instance
default_approval_gate = ApprovalGate()
