"""
core/event_stream.py — Streaming Response, Token Dispatch & Interactive Stop Button.

Implements:
- Streaming partial tokens to UI / API clients.
- Status update events ("Searching web...", "Analyzing data...", "Executing sandbox...").
- Immediate cancellation token handling (Stop generation).
- Accurate completion guarantees (never claims finished until tools resolve).
"""

import time
import threading
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class StreamEvent:
    event_type: str  # "token", "status", "tool_start", "tool_end", "artifact", "citation", "complete", "cancelled", "error"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.event_type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class CancellationToken:
    """Thread-safe cancellation flag for interactive stop button."""
    def __init__(self):
        self._is_cancelled = threading.Event()
        self.cancel_reason: Optional[str] = None

    def cancel(self, reason: str = "User cancelled generation."):
        self.cancel_reason = reason
        self._is_cancelled.set()

    def is_cancelled(self) -> bool:
        return self._is_cancelled.is_set()

    def reset(self):
        self._is_cancelled.clear()
        self.cancel_reason = None


class EventStream:
    """Manages an active streaming session with listeners and stop button."""
    def __init__(self, session_id: str, cancellation_token: Optional[CancellationToken] = None):
        self.session_id = session_id
        self.cancellation_token = cancellation_token or CancellationToken()
        self._events: list[StreamEvent] = []
        self._callback: Optional[Callable[[StreamEvent], None]] = None

    def set_listener(self, callback: Callable[[StreamEvent], None]):
        self._callback = callback

    def emit(self, event_type: str, content: str = "", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Emits an event to listeners. Returns False if generation was cancelled.
        """
        if self.cancellation_token.is_cancelled():
            return False

        evt = StreamEvent(event_type=event_type, content=content, metadata=metadata or {})
        self._events.append(evt)
        if self._callback:
            try:
                self._callback(evt)
            except Exception:
                pass
        return True

    def emit_token(self, token: str) -> bool:
        return self.emit("token", token)

    def emit_status(self, status_msg: str) -> bool:
        return self.emit("status", status_msg)

    def is_cancelled(self) -> bool:
        return self.cancellation_token.is_cancelled()
