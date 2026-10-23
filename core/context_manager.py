"""
core/context_manager.py — Prompt & Context Budget Manager.

Enforces the SPARK-AI speed design:
- Caps prompt context budget to guarantee sub-second LLM TTFT.
- Assembles:
    1. Core System Instruction (concise)
    2. Opted-in User Preferences (1–2 sentences)
    3. Top-k Retrieved Evidence Chunks (max 3–5)
    4. Rolling Summary of Older Turns (max 100 tokens)
    5. Recent Conversation Turns (last 4–6 messages)
    6. Current User Turn
- Dynamically trims oldest or least relevant tokens if budget is exceeded.
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger("chatbot.core.context_manager")


class ContextBudgetManager:
    def __init__(self, max_context_tokens: int = 4000):
        self.max_context_tokens = max_context_tokens

    def estimate_tokens(self, text: str) -> int:
        """Heuristic word-to-token ratio (approx 1 token per 4 chars)."""
        return max(1, len(text) // 4)

    def assemble_context(
        self,
        system_prompt: str,
        user_query: str,
        recent_messages: List[Dict[str, str]],
        memory_summary: str = "",
        retrieved_chunks: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Constructs a strictly bounded message list for LLM invocation.
        """
        budget = max_tokens or self.max_context_tokens
        used_tokens = 0

        # 1. Base system message
        sys_parts = [system_prompt.strip()]
        if memory_summary.strip():
            sys_parts.append(f"\n[USER PREFERENCES & CONTEXT]:\n{memory_summary.strip()}")

        # 2. Add retrieved knowledge snippets (top 3–5 only)
        if retrieved_chunks:
            evidence_lines = ["\n[RETRIEVED KNOWLEDGE (USE AS EVIDENCE FOR ANSWER)]:\n"]
            for i, c in enumerate(retrieved_chunks[:4], start=1):
                loc = f"p. {c['page']}" if c.get("page") else (f"Sheet: {c['sheet_name']}" if c.get("sheet_name") else "")
                loc_str = f" ({loc})" if loc else ""
                evidence_lines.append(f"Source [{i}] {c.get('file_name', 'Doc')}{loc_str}:\n{c.get('text', '')[:600]}\n")
            sys_parts.append("\n".join(evidence_lines))

        full_system_text = "\n\n".join(sys_parts)
        used_tokens += self.estimate_tokens(full_system_text)

        # 3. Current query
        used_tokens += self.estimate_tokens(user_query)

        # 4. Fit recent conversation messages from newest to oldest
        selected_history: List[Dict[str, str]] = []
        for msg in reversed(recent_messages):
            msg_tokens = self.estimate_tokens(msg.get("content", ""))
            if used_tokens + msg_tokens > budget:
                break
            selected_history.insert(0, msg)
            used_tokens += msg_tokens

        # Assemble final message list
        final_messages = [{"role": "system", "content": full_system_text}]
        final_messages.extend(selected_history)
        final_messages.append({"role": "user", "content": user_query})

        return final_messages


default_context_manager = ContextBudgetManager()
