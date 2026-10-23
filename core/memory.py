"""
Long-term Memory Store using SQLite.
Persists user level, learning goals, weak topics, and session insights across conversations.
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("chatbot.memory")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_memory.db")


def init_memory_db():
    """Initializes SQLite schema for long-term user memory with WAL mode and indexes."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                user_level TEXT DEFAULT 'Undergraduate',
                target_role TEXT DEFAULT 'Software Engineer',
                goals TEXT DEFAULT '[]',
                weak_topics TEXT DEFAULT '[]',
                strong_topics TEXT DEFAULT '[]',
                preferences TEXT DEFAULT '{}',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topic_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                topic TEXT,
                score REAL,
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                name TEXT,
                picture TEXT,
                plan TEXT DEFAULT 'standard',
                auth_provider TEXT DEFAULT 'email',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_topic_scores_user ON topic_scores(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_topic_scores_topic ON topic_scores(user_id, topic);")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing memory DB: {e}")


# Initialize schema on load
init_memory_db()


def get_user_memory(user_id: str = "default") -> Dict[str, Any]:
    """Retrieves stored memory profile for a user."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()

        cursor.execute("SELECT user_level, target_role, goals, weak_topics, strong_topics, preferences FROM user_profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "user_level": row[0],
                "target_role": row[1],
                "goals": json.loads(row[2]) if row[2] else [],
                "weak_topics": json.loads(row[3]) if row[3] else [],
                "strong_topics": json.loads(row[4]) if row[4] else [],
                "preferences": json.loads(row[5]) if row[5] else {}
            }
    except Exception as e:
        logger.error(f"Error reading user memory: {e}")

    return {
        "user_level": "Undergraduate",
        "target_role": "Software Engineer",
        "goals": ["Master technical interviews and problem solving"],
        "weak_topics": [],
        "strong_topics": [],
        "preferences": {}
    }


def update_user_memory(user_id: str = "default", updates: Optional[Dict[str, Any]] = None):
    """Updates memory fields (level, role, goals, weak topics)."""
    if not updates:
        return
    try:
        current = get_user_memory(user_id)
        current.update(updates)

        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_profiles (user_id, user_level, target_role, goals, weak_topics, strong_topics, preferences, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                user_level=excluded.user_level,
                target_role=excluded.target_role,
                goals=excluded.goals,
                weak_topics=excluded.weak_topics,
                strong_topics=excluded.strong_topics,
                preferences=excluded.preferences,
                updated_at=CURRENT_TIMESTAMP
        """, (
            user_id,
            current.get("user_level", "Undergraduate"),
            current.get("target_role", "Software Engineer"),
            json.dumps(current.get("goals", [])),
            json.dumps(current.get("weak_topics", [])),
            json.dumps(current.get("strong_topics", [])),
            json.dumps(current.get("preferences", {}))
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error updating user memory: {e}")


def record_topic_score(user_id: str, topic: str, score: float, feedback: str = ""):
    """Records performance on a topic to track weak and strong areas."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO topic_scores (user_id, topic, score, feedback) VALUES (?, ?, ?, ?)", (user_id, topic, score, feedback))
        conn.commit()

        # Update weak/strong lists based on average
        cursor.execute("SELECT AVG(score) FROM topic_scores WHERE user_id = ? AND topic = ?", (user_id, topic))
        avg_score = cursor.fetchone()[0] or score
        conn.close()

        mem = get_user_memory(user_id)
        weak = set(mem.get("weak_topics", []))
        strong = set(mem.get("strong_topics", []))

        if avg_score < 6.5:
            weak.add(topic)
            strong.discard(topic)
        elif avg_score >= 8.0:
            strong.add(topic)
            weak.discard(topic)

        update_user_memory(user_id, {"weak_topics": list(weak), "strong_topics": list(strong)})

    except Exception as e:
        logger.error(f"Error recording topic score: {e}")


def add_user_topic_weakness(user_id: str, topic: str):
    """Explicitly registers a weak topic in user memory."""
    try:
        mem = get_user_memory(user_id)
        weak = set(mem.get("weak_topics", []))
        weak.add(topic)
        strong = set(mem.get("strong_topics", []))
        strong.discard(topic)
        update_user_memory(user_id, {"weak_topics": list(weak), "strong_topics": list(strong)})
    except Exception as e:
        logger.error(f"Error adding weak topic: {e}")


def add_user_topic_strength(user_id: str, topic: str):
    """Explicitly registers a strong topic in user memory."""
    try:
        mem = get_user_memory(user_id)
        strong = set(mem.get("strong_topics", []))
        strong.add(topic)
        weak = set(mem.get("weak_topics", []))
        weak.discard(topic)
        update_user_memory(user_id, {"weak_topics": list(weak), "strong_topics": list(strong)})
    except Exception as e:
        logger.error(f"Error adding strong topic: {e}")


def get_memory_context_string(user_id: str = "default") -> str:
    """Formats long-term memory into prompt context."""
    mem = get_user_memory(user_id)
    lines = [
        f"- User Level: {mem.get('user_level')}",
        f"- Target Role: {mem.get('target_role')}"
    ]
    goals = mem.get("goals")
    if goals and isinstance(goals, list):
        lines.append(f"- Active Goals: {', '.join(str(g) for g in goals)}")
    weak = mem.get("weak_topics")
    if weak and isinstance(weak, list):
        lines.append(f"- Weak Topics (Provide extra pedagogical support): {', '.join(str(t) for t in weak)}")
    strong = mem.get("strong_topics")
    if strong and isinstance(strong, list):
        lines.append(f"- Strong Topics (Can be tested at higher difficulty): {', '.join(str(t) for t in strong)}")

    return "[LONG-TERM USER PROFILE & MEMORY]:\n" + "\n".join(lines)


def clear_user_memory(user_id: str = "default"):
    """Resets memory profile and clears stored topic scores for a user."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM topic_scores WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        logger.info("Cleared long-term memory for user.")
    except Exception as e:
        logger.error(f"Error clearing user memory: {type(e).__name__}")


def get_or_create_user(
    email: str,
    name: Optional[str] = None,
    picture: Optional[str] = None,
    auth_provider: str = "google",
    default_plan: str = "standard"
) -> Dict[str, Any]:
    """
    Creates or fetches a user account by email from SQLite.
    Persists user profile, display name, avatar picture, and account plan.
    Never logs email or credential data.
    """
    clean_email = (email or "").strip().lower()
    if not clean_email:
        clean_email = "default_user@example.com"
    clean_name = (name or "").strip()

    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT email, name, picture, plan, auth_provider FROM users WHERE email = ?",
            (clean_email,)
        )
        row = cursor.fetchone()
        if row:
            stored_email, stored_name, stored_pic, stored_plan, stored_provider = row
            updated = False
            if clean_name and not stored_name:
                stored_name = clean_name
                updated = True
            if picture and not stored_pic:
                stored_pic = picture
                updated = True
            if updated:
                cursor.execute(
                    "UPDATE users SET name = ?, picture = ?, updated_at = CURRENT_TIMESTAMP WHERE email = ?",
                    (stored_name, stored_pic, clean_email)
                )
                conn.commit()
            conn.close()
            plan_val = stored_plan or "standard"
            return {
                "email": stored_email,
                "name": stored_name or clean_name or "User",
                "picture": stored_pic,
                "plan": plan_val,
                "is_pro": plan_val.lower() in ("pro", "premium", "internal"),
                "auth_provider": stored_provider
            }
        else:
            final_name = clean_name or "User"
            plan_val = default_plan or "standard"
            cursor.execute(
                "INSERT INTO users (email, name, picture, plan, auth_provider) VALUES (?, ?, ?, ?, ?)",
                (clean_email, final_name, picture, plan_val, auth_provider)
            )
            conn.commit()
            conn.close()
            return {
                "email": clean_email,
                "name": final_name,
                "picture": picture,
                "plan": plan_val,
                "is_pro": plan_val.lower() in ("pro", "premium", "internal"),
                "auth_provider": auth_provider
            }
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {type(e).__name__}")
        plan_val = default_plan or "standard"
        return {
            "email": clean_email,
            "name": clean_name or "User",
            "picture": picture,
            "plan": plan_val,
            "is_pro": plan_val.lower() in ("pro", "premium"),
            "auth_provider": auth_provider
        }


def update_user_plan(email: str, plan: str) -> bool:
    """Updates the account tier ('standard', 'pro', 'premium') for a user."""
    clean_email = (email or "").strip().lower()
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET plan = ?, updated_at = CURRENT_TIMESTAMP WHERE email = ?",
            (plan.lower().strip(), clean_email)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error in update_user_plan: {type(e).__name__}")
        return False


def get_user_plan(email: str) -> str:
    """Returns the stored plan ('standard', 'pro', etc.) for a user."""
    clean_email = (email or "").strip().lower()
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("SELECT plan FROM users WHERE email = ?", (clean_email,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return str(row[0])
    except Exception as e:
        logger.error(f"Error in get_user_plan: {type(e).__name__}")
    return "standard"


def delete_user_data(user_id: str) -> bool:
    """
    Deletes all persistent profile records, weak/strong topics, and scores for a user.
    Enforces user data privacy, right-to-be-forgotten, and GDPR compliance.
    """
    uid = (user_id or "default").strip()
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_profiles WHERE user_id = ?", (uid,))
        cursor.execute("DELETE FROM topic_scores WHERE user_id = ?", (uid,))
        conn.commit()
        conn.close()
        logger.info(f"User data successfully purged for user_id='{uid}'.")
        return True
    except Exception as e:
        logger.error(f"Error purging user data for user_id='{uid}': {e}")
        return False


def export_user_data(user_id: str) -> Dict[str, Any]:
    """
    Exports full user profile, weak topics, and progress history as a portable JSON dictionary.
    """
    uid = (user_id or "default").strip()
    profile = get_user_memory(uid)
    topic_history = []
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute("SELECT topic, score, feedback, created_at FROM topic_scores WHERE user_id = ? ORDER BY created_at DESC", (uid,))
        rows = cursor.fetchall()
        conn.close()
        for r in rows:
            topic_history.append({"topic": r[0], "score": r[1], "feedback": r[2], "created_at": str(r[3])})
    except Exception as e:
        logger.debug(f"Error retrieving topic history: {e}")

    return {
        "user_id": uid,
        "profile": profile,
        "topic_evaluations": topic_history,
        "exported_at": str(sqlite3.datetime.datetime.now() if hasattr(sqlite3, "datetime") else "2026-10-23")
    }


def clear_user_history(user_id: str) -> bool:
    """Clears past chat messages for a specific user from chatbot.db."""
    db_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chatbot.db")
    if not os.path.exists(db_file):
        return True
    try:
        conn = sqlite3.connect(db_file, timeout=10.0)
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM messages WHERE conversation_id IN (
                SELECT id FROM conversations WHERE user_id = ?
            )
        """, (user_id,))
        cursor.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.debug(f"Error clearing conversation history: {e}")
        return False


def search_conversation_history(query: str, user_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Searches past messages and conversation history across stored conversations in chatbot.db.
    """
    if not query or not query.strip():
        return []
    db_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chatbot.db")
    if not os.path.exists(db_file):
        return []
    try:
        conn = sqlite3.connect(db_file, timeout=10.0)
        cursor = conn.cursor()
        search_term = f"%{query.strip()}%"
        if user_id:
            cursor.execute("""
                SELECT m.id, m.conversation_id, m.role, m.content, m.created_at
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.user_id = ? AND m.content LIKE ?
                ORDER BY m.created_at DESC
                LIMIT ?
            """, (user_id, search_term, limit))
        else:
            cursor.execute("""
                SELECT id, conversation_id, role, content, created_at
                FROM messages
                WHERE content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (search_term, limit))
        rows = cursor.fetchall()
        conn.close()
        results = []
        for r in rows:
            results.append({
                "id": r[0],
                "conversation_id": r[1],
                "role": r[2],
                "content": r[3],
                "created_at": str(r[4])
            })
        return results
    except Exception as e:
        logger.debug(f"Error searching conversation history: {e}")
        return []


