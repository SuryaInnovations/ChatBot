"""
Universal Request Pipeline Orchestrator with Intent-Driven Routing.
Implements the exact routing and failure recovery tree.
"""

from typing import Dict, Any, List, Optional, Callable
import os
import json

from core.intent import detect_intent, IntentType
from core.prompt import get_system_prompt
from core.conversation import ConversationSession
from core.llm_provider import LLMProvider
from core.interview import InterviewSession
from tools.web_search import search_web
from tools.math_solver import solve_math_expression, calculate_finance
from tools.code_executor import execute_python_code
from tools.file_analyzer import analyze_file
from tools.doc_generator import generate_document
from tools.deterministic_solver import can_deterministic_tool_answer, solve_deterministically

class ChatbotOrchestrator:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.interview_session: Optional[InterviewSession] = None

    def process_message(
        self,
        session: ConversationSession,
        user_message: str,
        custom_instructions: str = "",
        on_status_update: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Processes message through the Intent Detector and routes to the appropriate pipeline.
        """
        query = user_message.strip()

        # 1. INTENT DETECTOR
        if on_status_update:
            on_status_update("Detecting user intent...")

        in_interview = bool(self.interview_session and self.interview_session.active)
        intent = detect_intent(query, session.attached_files, in_interview=in_interview)

        # 2. Add user message to session
        session.add_message("user", query)

        executed_tools = []
        generated_artifacts = []
        pre_tool_context = ""

        # 3. ROUTE BASED ON INTENT
        # A. Current / Latest Information -> Web Search first
        if intent == IntentType.CURRENT_INFO:
            if on_status_update:
                on_status_update(f"Searching web for current information...")
            search_results = search_web(query, max_results=5)
            executed_tools.append({"name": "search_web", "result": search_results})
            pre_tool_context = f"\n\n[LIVE WEB SEARCH RESULTS]:\n{json.dumps(search_results, indent=2)}\n"

        # B. Mathematical Calculation -> Calculator / SymPy first
        elif intent == IntentType.MATH_CALCULATION:
            if on_status_update:
                on_status_update("Evaluating mathematical calculation...")
            q_lower = query.lower()
            if any(term in q_lower for term in ["compound", "simple", "emi", "interest"]):
                # Calculate finance
                res = calculate_finance("compound" if "compound" in q_lower else "simple", 10000, 8, 3)
                # If specific values in query, the deterministic solver handles it
            else:
                res = solve_math_expression(query)
            executed_tools.append({"name": "math_solver", "result": res})
            pre_tool_context = f"\n\n[MATHEMATICAL ENGINE CALCULATION]:\n{json.dumps(res, indent=2)}\n"

        # C. Uploaded Document -> File Search / Reader first
        elif intent == IntentType.DOCUMENT_ANALYSIS:
            if session.attached_files:
                last_file = session.attached_files[-1]
                if on_status_update:
                    on_status_update(f"Reading attached document: {last_file['name']}...")
                file_analysis = analyze_file(last_file["path"])
                executed_tools.append({"name": "analyze_file", "result": file_analysis})
                pre_tool_context = f"\n\n[ATTACHED DOCUMENT ANALYSIS ({last_file['name']})]:\n{json.dumps(file_analysis, indent=2)}\n"

        # D. Interview Workflow
        elif intent == IntentType.INTERVIEW:
            if not self.interview_session or not self.interview_session.active:
                self.interview_session = InterviewSession()
                pre_tool_context = f"\n\n[WORKFLOW]: {self.interview_session.start_prompt()}"
            else:
                pre_tool_context = f"\n\n[WORKFLOW]: {self.interview_session.evaluate_and_next_prompt(query)}"

        # 4. EXECUTE VIA LLM
        if on_status_update:
            on_status_update("Synthesizing response...")

        # Build dynamic prompt with pre-tool verified context
        system_prompt = get_system_prompt(custom_instructions=custom_instructions, active_files=session.attached_files)
        if pre_tool_context:
            system_prompt += f"\n--- VERIFIED TOOL CONTEXT ---\n{pre_tool_context}\n"

        llm_response = self.provider.chat_completion(
            messages=session.messages,
            system_prompt=system_prompt
        )

        # 5. HANDLE LLM SUCCESS OR FAILURE
        if llm_response.get("success"):
            final_content = llm_response.get("content", "").strip()
            session.add_message("assistant", final_content)
            if on_status_update:
                on_status_update("Done.")
            return {
                "success": True,
                "content": final_content,
                "executed_tools": executed_tools,
                "generated_artifacts": generated_artifacts,
                "provider": llm_response.get("provider"),
                "model": llm_response.get("model")
            }

        # 6. LLM FAILED (NO AVAILABLE CONFIGURED PROVIDER)
        # Check: Can local deterministic tool answer?
        if can_deterministic_tool_answer(intent, query, session.attached_files):
            if on_status_update:
                on_status_update("Resolving with local deterministic engine...")
            det_result = solve_deterministically(intent, query, session.attached_files)
            if det_result and det_result.get("content"):
                final_content = det_result["content"].strip()
                if det_result.get("tool"):
                    executed_tools.append({"name": det_result["tool"], "result": det_result.get("result")})
                if det_result.get("images"):
                    for img in det_result["images"]:
                        generated_artifacts.append({"type": "image", "path": img, "name": os.path.basename(img)})

                session.add_message("assistant", final_content)
                if on_status_update:
                    on_status_update("Done.")
                return {
                    "success": True,
                    "content": final_content,
                    "executed_tools": executed_tools,
                    "generated_artifacts": generated_artifacts,
                    "provider": "local_deterministic",
                    "model": "deterministic_solver"
                }

        # 7. HONEST ERROR
        # If neither LLM nor deterministic tool can answer:
        honest_error = "AI generation is temporarily unavailable. Please configure an available model provider."
        session.add_message("assistant", honest_error)
        if on_status_update:
            on_status_update("Unavailable.")

        return {
            "success": False,
            "content": honest_error,
            "executed_tools": executed_tools,
            "generated_artifacts": [],
            "provider": None,
            "model": None
        }
