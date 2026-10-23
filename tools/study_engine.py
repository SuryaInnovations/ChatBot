"""
Study Engine: Exam Patterns, Academic Notes Structuring, NPTEL-Style MCQs, and Mock Tests.
Generates 2-mark, 5-mark, and 10-mark structured answers, calibrated MCQs, and timed mock exams.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("chatbot.study_engine")


def generate_exam_pattern_answers(topic_or_notes: str, pattern: str = "all") -> Dict[str, Any]:
    """
    Structures notes or topics into university exam format:
    - 2-mark: Exact definition (20-30 words) + key formula/notation.
    - 5-mark: Core concept + 4 architectural/mechanistic points + diagram layout.
    - 10-mark: Comprehensive essay (Intro, Architecture, Flow, Pros/Cons, Case Study, Conclusion).
    """
    topic_clean = topic_or_notes.strip()
    pattern_clean = pattern.lower().strip()

    two_marker = {
        "marks": 2,
        "format": "Definition & Core Formulation",
        "guideline": "Answer within 25-40 words with key formula and primary application.",
        "prompt_template": f"Generate a calibrated 2-mark university exam answer for '{topic_clean}'. Lead with the exact, formal definition in 2 sentences, followed by 1 key formula/property and 1 primary real-world use case."
    }

    five_marker = {
        "marks": 5,
        "format": "Structured Concept Breakdown with Diagram Outline",
        "guideline": "Clear heading, 4 key conceptual tenets, ASCII/Mermaid block representation, and trade-offs.",
        "prompt_template": f"Generate a calibrated 5-mark university exam answer for '{topic_clean}'. Include: 1) Formal Definition, 2) Core Working Principles (4 bullet points), 3) Diagram Description or Mermaid block diagram, 4) 2 Key Advantages and Limitations."
    }

    ten_marker = {
        "marks": 10,
        "format": "Comprehensive Technical & Architectural Synthesis",
        "guideline": "Full multi-section derivation, architecture breakdown, implementation case study, and comparative analysis.",
        "prompt_template": f"Generate a calibrated 10-mark university exam answer for '{topic_clean}'. Structure strictly with: Section 1: Comprehensive Introduction & Background; Section 2: Theoretical Foundations & Governing Equations; Section 3: Detailed Architecture & Step-by-Step Mechanism (with Diagram); Section 4: Real-World Case Study / Implementation; Section 5: Comparative Trade-Off Analysis; Section 6: Summary & Future Trends."
    }

    sixteen_marker = {
        "marks": 16,
        "format": "Comprehensive University Part-C Master Essay & System Blueprint",
        "guideline": "Exhaustive derivation, full architectural breakdown, mathematical modeling, code/pseudocode, enterprise case study, and trade-off comparison.",
        "prompt_template": f"Generate a calibrated 16-mark university exam answer (Part C standard) for '{topic_clean}'. Structure strictly with: Part 1: Comprehensive Introduction, Context, & Scope; Part 2: Mathematical / Algorithmic Formulations & Derivations; Part 3: System Architecture & ASCII/Mermaid Block Diagram; Part 4: Step-by-Step Working Mechanism & State Machine; Part 5: Pseudocode / Python Implementation; Part 6: Enterprise Industrial Case Study; Part 7: Failure Modes, Scalability, & Performance Trade-Offs; Part 8: Conclusion & Future Enhancements."
    }

    res: Dict[str, Any] = {
        "success": True,
        "topic": topic_clean,
        "pattern": pattern_clean,
        "pattern_title": f"{pattern_clean.title()} Exam Blueprint",
        "sections": {}
    }

    if pattern_clean in ("2", "2-mark", "two_mark", "all"):
        res["sections"]["two_mark"] = two_marker
    if pattern_clean in ("5", "5-mark", "five_mark", "all"):
        res["sections"]["five_mark"] = five_marker
    if pattern_clean in ("10", "10-mark", "ten_mark", "all"):
        res["sections"]["ten_mark"] = ten_marker
    if pattern_clean in ("16", "16-mark", "sixteen_mark", "all"):
        res["sections"]["sixteen_mark"] = sixteen_marker

    return res


def generate_nptel_mcqs(topic_or_notes: str, num_questions: int = 5, difficulty: str = "moderate") -> Dict[str, Any]:
    """
    Generates NPTEL-style challenging multiple-choice questions with 4 distinct options,
    mathematical or algorithmic edge cases, and detailed explanation of distractors.
    """
    return {
        "topic": topic_or_notes.strip(),
        "num_questions": num_questions,
        "difficulty": difficulty,
        "style": "NPTEL / GATE Academic Standards",
        "instructions": (
            f"Generate {num_questions} NPTEL-standard multiple-choice questions for '{topic_or_notes}'. "
            "For each question provide: "
            "1. Clear problem statement focusing on edge cases, mathematical formulas, or conceptual traps. "
            "2. Options A, B, C, D (ensure distractors reflect common student misconceptions). "
            "3. Correct Answer clearly identified. "
            "4. Comprehensive Explanation showing why the answer is correct and why other options fail."
        )
    }


def parse_mock_test_submission(answers: Dict[str, str], questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Scores user answers for a mock exam session, computes percentage,
    identifies weak topics, and recommends specific revision topics.
    """
    total = len(questions)
    if total == 0:
        return {"score": 0, "total": 0, "percentage": 0, "results": [], "weak_topics": []}

    correct_count = 0
    detailed_results = []
    weak_topics = set()
    strong_topics = set()

    for idx, q in enumerate(questions, start=1):
        q_id = str(idx)
        user_ans = str(answers.get(q_id, "")).strip().upper()
        correct_ans = str(q.get("correct_option", q.get("answer", ""))).strip().upper()
        topic = q.get("topic", "General")

        # Check if first character matches (A, B, C, D)
        is_correct = bool(user_ans and correct_ans and user_ans[0] == correct_ans[0])
        if is_correct:
            correct_count += 1
            strong_topics.add(topic)
        else:
            weak_topics.add(topic)

        detailed_results.append({
            "question_num": idx,
            "question": q.get("question", ""),
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
            "topic": topic
        })

    pct = round((correct_count / total) * 100, 1)
    
    return {
        "score": correct_count,
        "total": total,
        "percentage": pct,
        "weak_topics": list(weak_topics),
        "strong_topics": list(strong_topics),
        "results": detailed_results,
        "summary": f"Scored {correct_count}/{total} ({pct}%) in mock exam."
    }
