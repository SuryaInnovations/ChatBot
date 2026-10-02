"""
Interview Workflow module.
Manages mock interview sessions, asks one question at a time, evaluates user responses,
and provides structured feedback before progressing to the next question.
"""

from typing import Dict, Any, List, Optional

class InterviewSession:
    def __init__(self, topic: str = "General Technical", role: str = "Software Engineer"):
        self.topic = topic
        self.role = role
        self.current_question_index = 0
        self.active = True
        self.history: List[Dict[str, str]] = []

    def start_prompt(self) -> str:
        return f"""You are conducting a professional mock interview for the role of **{self.role}** focusing on **{self.topic}**.

Guidelines:
1. Ask exactly ONE question to start.
2. Clearly number the question (Question 1).
3. Wait for the candidate's answer. Do not answer it yourself.
"""

    def evaluate_and_next_prompt(self, candidate_answer: str) -> str:
        self.current_question_index += 1
        return f"""The candidate provided the following answer to Question {self.current_question_index}:
Candidate's Answer: "{candidate_answer}"

Provide:
1. **Feedback**: Brief evaluation (Strengths & Areas to Improve).
2. **Next Question**: Numbered Question {self.current_question_index + 1}. Ask one clear question and pause for the candidate's response.
"""
