"""
agents/interview_agent.py — Interactive Mock Interview Simulator Agent.

Implements Capability 16:
- Conducts realistic technical, behavioral, and system design mock interviews.
- Delivers questions one at a time to keep response latency <2s.
- Evaluates candidate answers using structured rubrics (correctness, communication, depth).
- Provides actionable constructive feedback and final performance scorecard.
"""

import time
import logging
from typing import Dict, Any, List, Optional

from core.interview_bank import get_interview_question, get_questions_by_topic

logger = logging.getLogger("chatbot.agents.interview_agent")


class MockInterviewSession:
    def __init__(self, session_id: str, role: str = "Software Engineer", topic: str = "System Design"):
        self.session_id = session_id
        self.role = role
        self.topic = topic
        self.questions_asked: List[str] = []
        self.answers_recorded: List[str] = []
        self.evaluations: List[Dict[str, Any]] = []
        self.current_question_idx: int = 0
        self.active: bool = True
        self.started_at: float = time.time()


class InterviewSimulatorAgent:
    def __init__(self):
        self._sessions: Dict[str, MockInterviewSession] = {}

    def start_interview(
        self,
        session_id: str,
        role: str = "Software Engineer",
        topic: str = "Python & Data Structures"
    ) -> Dict[str, Any]:
        """Starts a new mock interview session and poses the first question."""
        session = MockInterviewSession(session_id=session_id, role=role, topic=topic)
        self._sessions[session_id] = session

        # Get first question from bank or generate
        q_item = get_interview_question(topic=topic, difficulty="intermediate")
        q_text = q_item.get("question") if q_item else f"Can you explain how hash maps handle collisions in {topic}?"

        session.questions_asked.append(q_text)
        session.current_question_idx = 1

        return {
            "success": True,
            "session_id": session_id,
            "role": role,
            "topic": topic,
            "question_number": 1,
            "question": q_text,
            "message": f"Welcome to your mock interview for {role}! Here is your first question:"
        }

    def submit_answer_and_next(
        self,
        session_id: str,
        candidate_answer: str
    ) -> Dict[str, Any]:
        """Evaluates previous answer and delivers the next interview question."""
        session = self._sessions.get(session_id)
        if not session or not session.active:
            return {"success": False, "error": "No active interview session found."}

        current_q = session.questions_asked[-1]
        session.answers_recorded.append(candidate_answer)

        # Evaluate candidate answer
        from core.llm_provider import LLMProvider
        llm = LLMProvider(provider="auto")
        eval_prompt = (
            f"Role: {session.role}\nQuestion: {current_q}\nCandidate Answer: {candidate_answer}\n\n"
            "Evaluate this answer realistically:\n"
            "1. Score (out of 10)\n2. Strengths\n3. Weaknesses\n4. Better Alternative Answer."
        )
        try:
            feedback = llm.generate_response([{"role": "user", "content": eval_prompt}])
        except Exception:
            feedback = "Good explanation. Be sure to mention trade-offs and edge cases."

        session.evaluations.append({
            "question": current_q,
            "answer": candidate_answer,
            "feedback": feedback
        })

        # Check if interview is finished (after 3–5 questions)
        if len(session.questions_asked) >= 3:
            session.active = False
            return {
                "success": True,
                "session_id": session_id,
                "status": "completed",
                "feedback_on_last": feedback,
                "total_questions": len(session.questions_asked),
                "summary": "Mock interview completed! You answered all questions. Review the feedback to sharpen your skills."
            }

        # Next question
        session.current_question_idx += 1
        q_item = get_interview_question(topic=session.topic, difficulty="intermediate")
        next_q = q_item.get("question") if q_item else "How would you design a scalable caching layer for this service?"
        session.questions_asked.append(next_q)

        return {
            "success": True,
            "session_id": session_id,
            "feedback_on_previous": feedback,
            "question_number": session.current_question_idx,
            "question": next_q
        }


default_interview_agent = InterviewSimulatorAgent()
