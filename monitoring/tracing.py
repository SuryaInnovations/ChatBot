"""
monitoring/tracing.py — Granular Request Tracing and Span Timeline.

Records span timestamps and durations for:
- request_received
- intent_classified
- first_token_streamed
- tool_start / tool_end
- model_start / model_end
- response_completed
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class TraceSpan:
    name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict)

    def finish(self):
        if self.end_time is None:
            self.end_time = time.time()
            self.duration_ms = round((self.end_time - self.start_time) * 1000.0, 2)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RequestTrace:
    def __init__(self, trace_id: Optional[str] = None, query: str = "", user_id: str = "default_user"):
        self.trace_id = trace_id or f"trace_{uuid.uuid4().hex[:12]}"
        self.query = query[:120]
        self.user_id = user_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.total_duration_ms: float = 0.0
        self.first_token_ms: Optional[float] = None
        self.spans: List[TraceSpan] = []
        self._active_spans: Dict[str, TraceSpan] = {}

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> TraceSpan:
        span = TraceSpan(name=name, attributes=attributes or {})
        self.spans.append(span)
        self._active_spans[name] = span
        return span

    def end_span(self, name: str, extra_attributes: Optional[Dict[str, Any]] = None):
        span = self._active_spans.pop(name, None)
        if span:
            if extra_attributes:
                span.attributes.update(extra_attributes)
            span.finish()

    def record_first_token(self):
        if self.first_token_ms is None:
            self.first_token_ms = round((time.time() - self.start_time) * 1000.0, 2)

    def finish(self):
        if self.end_time is None:
            self.end_time = time.time()
            self.total_duration_ms = round((self.end_time - self.start_time) * 1000.0, 2)
            # Ensure all open spans are ended
            for span in self._active_spans.values():
                span.finish()
            self._active_spans.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "user_id": self.user_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_ms": self.total_duration_ms,
            "first_token_ms": self.first_token_ms,
            "spans": [s.to_dict() for s in self.spans]
        }


class TraceManager:
    def __init__(self, max_history: int = 500):
        self._traces: List[RequestTrace] = []
        self.max_history = max_history

    def create_trace(self, query: str = "", user_id: str = "default_user") -> RequestTrace:
        trace = RequestTrace(query=query, user_id=user_id)
        self._traces.append(trace)
        if len(self._traces) > self.max_history:
            self._traces.pop(0)
        return trace

    def get_recent_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._traces[-limit:]]


default_trace_manager = TraceManager()
