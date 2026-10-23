"""
Production Interview Session Manager with 4-Dimension Rubric Scoring,
Curated Question Banks, STAR Story Integration, and Topic Progress Tracking.
"""

from typing import Dict, Any, List, Optional
import json

from core.interview_bank import get_random_question
from core.memory import record_topic_score


class InterviewSession:
    """
    Manages end-to-end mock interviews with structured rubrics:
    - 4-Dimension Scoring: Correctness, Clarity, Structure, Depth (/10 each, total /40).
    - Ideal Model Answer generation.
    - Topic-level progress and weak-area tracking.
    """
    def __init__(
        self,
        topic: str = "General Technical",
        role: str = "Software Engineer",
        category: str = "DSA",
        difficulty: str = "Medium",
        company: str = "General",
        user_id: str = "default"
    ):
        self.topic = topic
        self.role = role
        self.category = category
        self.difficulty = difficulty
        self.company = company
        self.user_id = user_id

        self.current_question_index = 0
        self.active = True
        self.history: List[Dict[str, Any]] = []
        self.current_question: Optional[Dict[str, Any]] = None

    def start_prompt(self) -> str:
        """Generates initial interview question prompt."""
        self.current_question = get_random_question(category=self.category, difficulty=self.difficulty, company=self.company)
        self.current_question_index = 1

        q_text = self.current_question["question"]
        q_title = self.current_question.get("title", f"Question {self.current_question_index}")
        q_company = self.current_question.get("company", self.company)

        return f"""You are conducting a FAANG-tier mock interview for **{self.role}** ({self.category} - {self.difficulty}) targeting **{q_company}**.

Present the first question to the candidate:
### Question 1: {q_title} ({q_company})
> {q_text}

Guidelines:
1. Present the question clearly and state what the interviewer is evaluating.
2. Tell the candidate: "Whenever you're ready, please share your thought process and solution."
3. Wait for the candidate's response. Do NOT provide hints or the solution yet.
"""

    def evaluate_and_next_prompt(self, candidate_answer: str) -> str:
        """
        Evaluates candidate response across the 4 dimensions (40 pts)
        using anchored scoring criteria and calibrated score ranges.
        """
        # Select next question from question bank
        self.current_question_index += 1
        next_q = get_random_question(category=self.category, difficulty=self.difficulty)
        self.current_question = next_q

        return f"""The candidate responded to Question {self.current_question_index - 1}:
Candidate's Answer:
"{candidate_answer}"

Evaluate their answer with objective calibration against these benchmark anchors:
- **Anchor 3/10**: Fundamentally flawed logic, misses core problem, vague or disorganized.
- **Anchor 6/10**: Working brute-force or basic explanation; unoptimized; misses edge cases or scalability.
- **Anchor 9/10**: Optimal time/space complexity, proactive edge case identification, crisp structured communication.

Format your evaluation using this exact structure:

### 🎯 Evaluation & Calibrated Scoring Rubric
- **Correctness (/10)**: Accuracy of logic, algorithm, complexity, or system concepts.
- **Clarity (/10)**: Concise, plain communication without rambling.
- **Structure (/10)**: Methodical sequence (Constraints → Approach → Complexity → Trade-offs, or STAR format).
- **Depth (/10)**: Thoroughness on edge cases, scale bottlenecks, or production caveats.
- **Estimated Score Range**: [e.g. 31–35 / 40] *(LLM calibrated estimate)*
- **Evaluator Confidence**: [High | Medium | Low]

### 💡 Ideal Model Answer:
[Provide the concise, 10/10 model answer showing how a top-tier candidate would answer.]

### ➡️ Next Question: Question {self.current_question_index} ({next_q.get('title', 'Next Question')} - {next_q.get('company', 'Tech')})
> {next_q.get('question')}

Ask the question and invite the candidate to answer.

```json_score
{{
  "correctness": <int 1-10>,
  "clarity": <int 1-10>,
  "structure": <int 1-10>,
  "depth": <int 1-10>,
  "score_range": "<low>-<high>/40",
  "confidence": "<High|Medium|Low>"
}}
```
"""

    def get_progress_summary(self) -> Dict[str, Any]:
        """Returns session summary with scores and weak areas."""
        return {
            "role": self.role,
            "category": self.category,
            "questions_completed": max(0, self.current_question_index - 1),
            "topic": self.topic,
            "difficulty": self.difficulty
        }

    def parse_and_validate_score(self, content: str) -> Optional[Dict[str, Any]]:
        """Parses score json block and validates against fixed InterviewEvaluationSchema."""
        import re
        from tools.schemas import InterviewEvaluationSchema
        match = re.search(r'```(?:json_score|json)?\s*\n(\{.*?\})\s*\n```', content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                validated = InterviewEvaluationSchema(**data)
                avg_score = (validated.correctness + validated.clarity + validated.structure + validated.depth) / 4.0
                curr_topic = self.topic
                if self.current_question:
                    curr_topic = self.current_question.get("topic", self.topic)
                record_topic_score(self.user_id, curr_topic, avg_score, f"Range: {validated.score_range}")
                return validated.model_dump()
            except Exception:
                pass
        return None

