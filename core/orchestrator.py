"""
Universal Request Pipeline Orchestrator with Intent-Driven Routing and Robust Fallback.
Adheres strictly to the Intent-First architecture and honest error handling.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Union

from core.intent import detect_intent, IntentType
from core.prompt import get_system_prompt
from core.conversation import ConversationSession
from core.llm_provider import LLMProvider
from core.provider_manager import ProviderManager
from core.interview import InterviewSession
from tools.web_search import search_web
from tools.math_solver import solve_math_expression, calculate_finance
from tools.file_analyzer import analyze_file
from tools.deterministic_solver import can_deterministic_tool_answer, solve_deterministically

logger = logging.getLogger("chatbot.orchestrator")

class ChatbotOrchestrator:
    def __init__(self, provider: Union[LLMProvider, Any] = "auto"):
        if isinstance(provider, LLMProvider):
            self.llm = provider
        elif hasattr(provider, "primary_provider"): # ProviderManager duck typing
            self.llm = LLMProvider(
                provider=provider.primary_provider,
                model=getattr(provider, "primary_model", None),
                api_key=getattr(provider, "primary_key", None),
                fallback_providers=getattr(provider, "fallback_providers", None)
            )
        elif isinstance(provider, str):
            self.llm = LLMProvider(provider=provider)
        else:
            self.llm = LLMProvider()

        self.interview_session: Optional[InterviewSession] = None

    def process_message(
        self,
        session: ConversationSession,
        user_message: str,
        custom_instructions: str = "",
        on_status_update: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Processes message through the Intent Analyzer and executes optimal workflow.
        """
        query = user_message.strip()

        # 1. INTENT ANALYZER
        in_interview = bool(self.interview_session and self.interview_session.active)
        intent = detect_intent(query, session.attached_files, in_interview=in_interview)
        logger.info(f"[ROUTER] Intent: {intent.value}")

        if on_status_update:
            on_status_update(f"Analyzing intent ({intent.value})...")

        # 2. Add user message to session
        session.add_message("user", query)

        executed_tools = []
        generated_artifacts = []
        pre_tool_context = ""

        # 3. DIRECT DETERMINISTIC SHORT-CIRCUIT (Step 8)
        # For pure simple arithmetic (e.g., '2 + 5 * 10'), do not call an expensive LLM
        clean_arithmetic = query.strip()
        import re
        if (intent == IntentType.MATH_CALCULATION and 
            re.match(r'^[\d\s\+\-\*\/\^\(\)\.\%]+$', clean_arithmetic) and 
            re.search(r'[\+\-\*\/\^\%]', clean_arithmetic)):
            
            logger.info("[ROUTER] Pure arithmetic detected: executing deterministic math tool directly.")
            det_res = solve_deterministically(intent, query)
            if det_res and det_res.get("content"):
                final_content = det_res["content"].strip()
                executed_tools.append({"name": det_res.get("tool", "calculator"), "result": det_res.get("result")})
                session.add_message("assistant", final_content)
                if on_status_update:
                    on_status_update("Done.")
                return {
                    "success": True,
                    "content": final_content,
                    "executed_tools": executed_tools,
                    "generated_artifacts": [],
                    "provider": "deterministic_calculator",
                    "model": "sympy"
                }

        # 4. PRE-LLM TOOL GATHERING
        # A. Current / Latest Information -> Web Search first
        if intent == IntentType.CURRENT_INFO:
            if on_status_update:
                on_status_update("Searching web for current information...")
            search_results = search_web(query, max_results=5)
            executed_tools.append({"name": "search_web", "result": search_results})
            pre_tool_context = f"\n\n[LIVE WEB SEARCH RESULTS]:\n{json.dumps(search_results, indent=2)}\n"

        # B. Complex Mathematical Calculation -> SymPy / Finance first
        elif intent == IntentType.MATH_CALCULATION:
            if on_status_update:
                on_status_update("Calculating mathematical expressions...")
            q_lower = query.lower()
            if any(term in q_lower for term in ["compound", "simple", "emi", "interest"]):
                det_math = solve_deterministically(intent, query)
                if det_math:
                    executed_tools.append({"name": det_math.get("tool"), "result": det_math.get("result")})
                    pre_tool_context = f"\n\n[FINANCIAL CALCULATION]:\n{det_math.get('content')}\n"
            else:
                res = solve_math_expression(query)
                executed_tools.append({"name": "math_solver", "result": res})
                pre_tool_context = f"\n\n[MATHEMATICAL ENGINE CALCULATION]:\n{json.dumps(res, indent=2)}\n"

        # C. Uploaded Document -> File Search / Reader first
        elif intent == IntentType.DOCUMENT_ANALYSIS:
            if session.attached_files:
                last_file = session.attached_files[-1]
                if on_status_update:
                    on_status_update(f"Reading document: {last_file['name']}...")
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

        # 5. INVOKE PROVIDER WITH AUTOMATIC FALLBACK
        system_prompt = get_system_prompt(custom_instructions=custom_instructions, active_files=session.attached_files)
        if pre_tool_context:
            system_prompt += f"\n--- VERIFIED CONTEXT ---\n{pre_tool_context}\n"

        llm_response = self.llm.generate(
            messages=session.messages,
            system_prompt=system_prompt,
            on_status_update=on_status_update
        )

        # 6. HANDLE SUCCESSFUL LLM RESPONSE
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

        # 7. LLM PROVIDERS UNAVAILABLE -> CHECK DETERMINISTIC FALLBACK
        logger.info("[ROUTER] LLM providers unavailable. Checking if local deterministic tools can answer.")
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

        # 8. HONEST USER-FACING ERROR (Step 14 & 18)
        honest_error = llm_response.get("error") or (
            "AI generation is currently unavailable because no configured provider could complete the request.\n\n"
            "Please check your AI provider configuration or API quota."
        )
        session.add_message("assistant", honest_error)
        if on_status_update:
            on_status_update("Unavailable.")

        return {
            "success": False,
            "content": honest_error,
            "executed_tools": executed_tools,
            "generated_artifacts": [],
            "provider": None,
            "model": None,
            "developer_log": llm_response.get("developer_log")
        }
