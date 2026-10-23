"""
core/learning.py — Adaptive Learning, Spaced Repetition, and Study Engine.

Implements Step 5 of the SPARK-AI Architecture:
- Spaced Repetition System (SuperMemo SM-2 algorithm for flashcard scheduling).
- Topic mastery and longitudinal progress tracking across multiple attempts.
- Personalized study plan generation based on weak topics and target roles.
- Structured technical interview preparation with model answers.
- User data governance (view, edit, delete, and export study records).
"""

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

from core.memory import DB_PATH, get_user_memory, add_user_topic_weakness, add_user_topic_strength

logger = logging.getLogger("chatbot.learning")


def init_learning_db():
    """Initializes SQLite tables for flashcards, study plans, and interview records."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                ease_factor REAL DEFAULT 2.5,
                interval_days INTEGER DEFAULT 1,
                repetitions INTEGER DEFAULT 0,
                next_review TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS study_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interview_prep (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                track TEXT NOT NULL,
                question TEXT NOT NULL,
                user_answer TEXT,
                model_answer TEXT,
                score REAL,
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_flashcards_user ON flashcards(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_flashcards_review ON flashcards(user_id, next_review);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_study_plans_user ON study_plans(user_id);")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing learning DB: {e}")


# Initialize schema on import
init_learning_db()


# ---------------------------------------------------------------------------
# SuperMemo SM-2 Spaced Repetition Algorithm
# ---------------------------------------------------------------------------

def calculate_sm2(
    quality: int,  # 0 to 5 rating of recall
    repetitions: int,
    previous_interval: int,
    previous_ease: float
) -> Tuple[int, int, float, datetime]:
    """
    Standard SM-2 algorithm implementation.
    Returns: (new_repetitions, new_interval_days, new_ease_factor, next_review_datetime)
    """
    quality = max(0, min(5, quality))

    if quality >= 3:
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = int(round(previous_interval * previous_ease))
        new_repetitions = repetitions + 1
    else:
        # Failed recall resets repetition count
        new_repetitions = 0
        new_interval = 1

    # Update ease factor: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    new_ease = previous_ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ease = max(1.3, round(new_ease, 3))  # Ease factor floor is 1.3

    next_review = datetime.now() + timedelta(days=new_interval)
    return new_repetitions, new_interval, new_ease, next_review


def create_flashcard(user_id: str, topic: str, question: str, answer: str) -> Dict[str, Any]:
    """Creates a new flashcard for a topic."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        now_str = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO flashcards (user_id, topic, question, answer, ease_factor, interval_days, repetitions, next_review)
            VALUES (?, ?, ?, ?, 2.5, 1, 0, ?)
        """, (user_id, topic.strip(), question.strip(), answer.strip(), now_str))
        card_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {"id": card_id, "topic": topic, "status": "created"}
    except Exception as e:
        logger.error(f"Error creating flashcard: {e}")
        return {"error": str(e)}


def get_due_flashcards(user_id: str, limit: int = 15) -> List[Dict[str, Any]]:
    """Retrieves flashcards that are due for review."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        now_str = datetime.now().isoformat()
        cursor.execute("""
            SELECT id, topic, question, answer, ease_factor, interval_days, repetitions, next_review
            FROM flashcards
            WHERE user_id = ? AND next_review <= ?
            ORDER BY next_review ASC
            LIMIT ?
        """, (user_id, now_str, limit))
        rows = cursor.fetchall()
        conn.close()

        cards = []
        for r in rows:
            cards.append({
                "id": r[0],
                "topic": r[1],
                "question": r[2],
                "answer": r[3],
                "ease_factor": r[4],
                "interval_days": r[5],
                "repetitions": r[6],
                "next_review": r[7]
            })
        return cards
    except Exception as e:
        logger.error(f"Error fetching due flashcards: {e}")
        return []


def record_flashcard_review(card_id: int, quality: int) -> Dict[str, Any]:
    """Updates a flashcard using the SM-2 algorithm following a review."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("SELECT repetitions, interval_days, ease_factor, user_id, topic FROM flashcards WHERE id = ?", (card_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"error": "Flashcard not found"}

        reps, interval, ease, uid, topic = row
        new_reps, new_interval, new_ease, next_rev = calculate_sm2(quality, reps, interval, ease)

        cursor.execute("""
            UPDATE flashcards
            SET repetitions = ?, interval_days = ?, ease_factor = ?, next_review = ?
            WHERE id = ?
        """, (new_reps, new_interval, new_ease, next_rev.isoformat(), card_id))
        conn.commit()
        conn.close()

        # Update topic mastery in long term memory
        if quality < 3:
            add_user_topic_weakness(uid, topic)
        elif quality >= 4 and new_reps >= 2:
            add_user_topic_strength(uid, topic)

        return {
            "card_id": card_id,
            "new_repetitions": new_reps,
            "new_interval_days": new_interval,
            "next_review": next_rev.strftime("%Y-%m-%d %H:%M")
        }
    except Exception as e:
        logger.error(f"Error recording flashcard review: {e}")
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Longitudinal Mastery Tracking Across Multiple Attempts
# ---------------------------------------------------------------------------

def get_topic_mastery_report(user_id: str) -> List[Dict[str, Any]]:
    """
    Computes mastery levels based on repeated topic test scores:
    - Attempt Count >= 3 and Avg Score >= 8.5 -> Mastered
    - Avg Score >= 7.0 -> Proficient
    - Avg Score >= 5.0 -> Developing
    - Avg Score < 5.0 or 1 attempt < 6.0 -> Needs Review
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT topic, COUNT(*) as attempts, AVG(score) as avg_score, MAX(score) as max_score, MAX(created_at) as last_attempt
            FROM topic_scores
            WHERE user_id = ?
            GROUP BY topic
            ORDER BY avg_score ASC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()

        report = []
        for r in rows:
            topic, attempts, avg_score, max_score, last_attempt = r[0], r[1], float(r[2]), float(r[3]), r[4]

            if attempts >= 3 and avg_score >= 8.5:
                status = "Mastered"
                badge = "🏆 Mastered"
            elif avg_score >= 7.0:
                status = "Proficient"
                badge = "🟢 Proficient"
            elif avg_score >= 5.0:
                status = "Developing"
                badge = "🟡 Developing"
            else:
                status = "Needs Review"
                badge = "🔴 Needs Review"

            report.append({
                "topic": topic,
                "attempts": attempts,
                "avg_score": round(avg_score, 1),
                "max_score": round(max_score, 1),
                "status": status,
                "badge": badge,
                "last_attempt": str(last_attempt)[:10]
            })
        return report
    except Exception as e:
        logger.error(f"Error computing topic mastery: {e}")
        return []


# ---------------------------------------------------------------------------
# Personalized Study Plan Generator
# ---------------------------------------------------------------------------

def generate_personalized_study_plan(user_id: str, subject: str, target_days: int = 14) -> Dict[str, Any]:
    """
    Constructs a structured day-by-day revision schedule integrating
    user weak topics from memory.
    """
    mem = get_user_memory(user_id)
    weak_topics = mem.get("weak_topics", [])
    target_role = mem.get("target_role", "Software Engineer")

    # Group schedule
    daily_schedule = []
    days = max(3, min(60, target_days))

    # Priority topics (weak topics first)
    priority_topics = [t for t in weak_topics if subject.lower() in t.lower()]
    if not priority_topics:
        priority_topics = [f"{subject} Fundamentals", f"{subject} Core Concepts", f"{subject} Applied Problem Solving", f"{subject} Mock Examination"]

    for d in range(1, days + 1):
        focus = priority_topics[(d - 1) % len(priority_topics)]
        daily_schedule.append({
            "day": d,
            "focus_topic": focus,
            "milestone": "Core Theory & 2-Mark Blueprints" if d <= 3 else "5-Mark & Diagram Practice" if d <= 8 else "10-Mark Architectural Synthesis & Mock Test",
            "recommended_time_min": 60
        })

    plan_payload = {
        "subject": subject,
        "target_days": days,
        "target_role": target_role,
        "weak_topics_targeted": [t for t in weak_topics if subject.lower() in t.lower()],
        "daily_schedule": daily_schedule,
        "created_at": datetime.now().isoformat()
    }

    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO study_plans (user_id, subject, plan_json) VALUES (?, ?, ?)",
                       (user_id, subject, json.dumps(plan_payload)))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error persisting study plan: {e}")

    return plan_payload


# ---------------------------------------------------------------------------
# User Data Correction & Deletion
# ---------------------------------------------------------------------------

def delete_learning_record(user_id: str, record_type: str, record_id: int) -> bool:
    """Allows user to correct/delete flashcards, study plans, or test score records."""
    table_map = {
        "flashcard": "flashcards",
        "study_plan": "study_plans",
        "topic_score": "topic_scores",
        "interview": "interview_prep"
    }
    table = table_map.get(record_type)
    if not table:
        return False

    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table} WHERE id = ? AND user_id = ?", (record_id, user_id))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    except Exception as e:
        logger.error(f"Error deleting learning record: {e}")
        return False


def list_flashcards(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves all flashcards for a user ordered by newest first."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, topic, question, answer, ease_factor, interval_days, repetitions, next_review, created_at
            FROM flashcards
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cursor.fetchall()
        conn.close()

        cards = []
        for r in rows:
            cards.append({
                "id": r[0],
                "topic": r[1],
                "question": r[2],
                "answer": r[3],
                "ease_factor": r[4],
                "interval_days": r[5],
                "repetitions": r[6],
                "next_review": str(r[7]),
                "created_at": str(r[8])
            })
        return cards
    except Exception as e:
        logger.error(f"Error listing flashcards: {e}")
        return []


def list_study_plans(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieves saved study plans for a user."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, subject, plan_json, status, created_at
            FROM study_plans
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cursor.fetchall()
        conn.close()

        plans = []
        for r in rows:
            plan_data = {}
            try:
                plan_data = json.loads(r[2])
            except Exception:
                pass
            plans.append({
                "id": r[0],
                "subject": r[1],
                "plan": plan_data,
                "status": r[3],
                "created_at": str(r[4])
            })
        return plans
    except Exception as e:
        logger.error(f"Error listing study plans: {e}")
        return []


def export_learning_data(user_id: str) -> Dict[str, Any]:
    """Exports all flashcards, study plans, and topic mastery history for a user."""
    from core.memory import get_user_memory
    return {
        "user_id": user_id,
        "memory_profile": get_user_memory(user_id),
        "topic_mastery": get_topic_mastery_report(user_id),
        "flashcards": list_flashcards(user_id, limit=200),
        "study_plans": list_study_plans(user_id, limit=50)
    }

