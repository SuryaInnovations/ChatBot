"""
STAR Behavioral Story Bank.
Persists candidate stories (Situation, Task, Action, Result)
and maps them to behavioral interview questions.
"""

import os
import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("chatbot.story_bank")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_memory.db")


def init_story_db():
    """Initializes STAR story bank schema."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS star_stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                title TEXT,
                situation TEXT,
                task TEXT,
                action TEXT,
                result TEXT,
                tags TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing star story DB: {e}")


init_story_db()


def save_star_story(
    user_id: str = "default",
    title: str = "Key Project Story",
    situation: str = "",
    task: str = "",
    action: str = "",
    result: str = "",
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Saves a candidate's STAR story to SQLite."""
    tags_json = json.dumps(tags or ["Leadership", "Technical Impact"])
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO star_stories (user_id, title, situation, task, action, result, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, title, situation, task, action, result, tags_json))
        story_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {
            "success": True,
            "story_id": story_id,
            "title": title,
            "message": f"Saved STAR story '{title}' to your personal interview story bank."
        }
    except Exception as e:
        logger.error(f"Error saving star story: {e}")
        return {"success": False, "error": str(e)}


def get_user_star_stories(user_id: str = "default") -> List[Dict[str, Any]]:
    """Retrieves all saved STAR stories for a user."""
    stories = []
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()

        cursor.execute("SELECT id, title, situation, task, action, result, tags, created_at FROM star_stories WHERE user_id = ? ORDER BY id DESC", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        for r in rows:
            stories.append({
                "id": r[0],
                "title": r[1],
                "situation": r[2],
                "task": r[3],
                "action": r[4],
                "result": r[5],
                "tags": json.loads(r[6]) if r[6] else [],
                "created_at": r[7]
            })
    except Exception as e:
        logger.error(f"Error retrieving star stories: {e}")
    return stories


def match_story_to_question(question: str, user_id: str = "default") -> Optional[Dict[str, Any]]:
    """
    Finds the most relevant candidate STAR story for a behavioral interview question.
    """
    stories = get_user_star_stories(user_id)
    if not stories:
        return None

    q_lower = question.lower()
    best_story = None
    best_score = -1

    for s in stories:
        score = 0
        for tag in s.get("tags", []):
            if tag.lower() in q_lower:
                score += 3
        # Match keywords
        words = set(s.get("title", "").lower().split())
        for w in words:
            if len(w) > 3 and w in q_lower:
                score += 1
        if score > best_score:
            best_score = score
            best_story = s

    return best_story or stories[0]
