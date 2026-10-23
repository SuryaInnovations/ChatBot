"""
evaluation/feedback.py — User Feedback Collection & Quality Analytics.

Supports:
- Recording thumbs up / thumbs down feedback per turn.
- Capturing user satisfaction ratings (1 to 5 stars) and correction notes.
- Aggregating satisfaction metrics and failure trends for continuous improvement.
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class FeedbackEntry:
    feedback_id: str
    session_id: str
    user_id: str
    query: str
    response_content: str
    rating: Optional[int] = None  # 1 to 5
    thumbs: Optional[str] = None  # "up" or "down"
    comment: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FeedbackStore:
    def __init__(self):
        self._entries: List[FeedbackEntry] = []

    def record_feedback(
        self,
        session_id: str,
        query: str,
        response_content: str,
        user_id: str = "default_user",
        thumbs: Optional[str] = None,
        rating: Optional[int] = None,
        comment: str = ""
    ) -> FeedbackEntry:
        """Stores a feedback rating entry."""
        fid = f"fb_{uuid.uuid4().hex[:10]}"
        entry = FeedbackEntry(
            feedback_id=fid,
            session_id=session_id,
            user_id=user_id,
            query=query[:150],
            response_content=response_content[:300],
            rating=rating,
            thumbs=thumbs,
            comment=comment,
            timestamp=time.time()
        )
        self._entries.append(entry)
        return entry

    def get_summary(self) -> Dict[str, Any]:
        """Calculates satisfaction metrics."""
        if not self._entries:
            return {"total_feedback": 0, "thumbs_up": 0, "thumbs_down": 0, "satisfaction_rate": 1.0}

        up = sum(1 for e in self._entries if e.thumbs == "up")
        down = sum(1 for e in self._entries if e.thumbs == "down")
        total_thumbs = up + down
        rate = (up / total_thumbs) if total_thumbs > 0 else 1.0

        return {
            "total_feedback": len(self._entries),
            "thumbs_up": up,
            "thumbs_down": down,
            "satisfaction_rate": round(rate, 3)
        }


default_feedback_store = FeedbackStore()
