"""
core/agent.py — Bounded Autonomous Agent with Verification and Action Guardrails.

Implements Step 2 of the SPARK-AI Architecture:
- Autonomous plan-act-verify loop with hard step limits, wall-clock timeouts, and tool budgets.
- Structured timeline tracking distinguishing completed, running, and proposed actions.
- Clarification detection when essential input is missing.
- Human-in-the-loop approval gates for consequential or destructive actions.
- Transient failure retry logic (never retrying auth/quota/model failures).
- Integrated evidence and solution verification before finalizing responses.
- Prevention of infinite loops and false-success claims.
"""

import time
import json
import logging
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Callable, Set

from core.verification import verify_evidence_and_citations, VerificationReport

logger = logging.getLogger("chatbot.agent")


class ActionStatus(str, Enum):
    PROPOSED = "proposed"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AgentAction:
    action_id: str
    step_index: int
    tool_name: str
    arguments: Dict[str, Any]
    status: ActionStatus = ActionStatus.PROPOSED
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    is_consequential: bool = False
    requires_approval: bool = False
    approval_granted: Optional[bool] = None
    verification_status: str = "unverified"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class AgentTimeline:
    session_id: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    actions: List[AgentAction] = field(default_factory=list)
    budget_used: int = 0
    max_budget: int = 6

    def add_action(self, action: AgentAction):
        self.actions.append(action)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_sec": round((self.end_time - self.start_time) if self.end_time else (time.time() - self.start_time), 3),
            "budget_used": self.budget_used,
            "max_budget": self.max_budget,
            "actions": [a.to_dict() for a in self.actions]
        }


@dataclass
class AgentExecutionResult:
    content: str
    status: str  # "success", "needs_clarification", "needs_approval", "budget_exceeded", "timeout", "failed"
    timeline: AgentTimeline
    executed_tools: List[str] = field(default_factory=list)
    verification_report: Optional[VerificationReport] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    clarification_prompt: Optional[str] = None
    pending_approval: Optional[AgentAction] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "status": self.status,
            "timeline": self.timeline.to_dict(),
            "executed_tools": self.executed_tools,
            "verification": self.verification_report.to_dict() if self.verification_report else None,
            "artifacts": self.artifacts,
            "clarification_prompt": self.clarification_prompt,
            "pending_approval": self.pending_approval.to_dict() if self.pending_approval else None
        }


class BoundedAutonomousAgent:
    """
    Autonomous Execution Agent with bounded budgets, safety guardrails, and verification.
    """

    # Non-retriable failure keywords (authentication, quota, permissions, invalid models)
    PERMANENT_ERROR_SUBSTRINGS: Set[str] = {
        "401", "unauthorized", "invalid api key", "authentication",
        "quota exceeded", "rate limit exceeded", "model not found",
        "permissiondenied", "access denied", "credit balance"
    }

    # Tools that carry destructive or irreversible impact requiring approval
    CONSEQUENTIAL_TOOLS: Set[str] = {
        "delete_file", "drop_table", "overwrite_file", "system_mutation", "kill_process"
    }

    def __init__(
        self,
        llm_provider=None,
        max_steps: int = 5,
        max_tool_budget: int = 6,
        timeout_seconds: float = 25.0
    ):
        self.llm = llm_provider
        self.max_steps = max_steps
        self.max_tool_budget = max_tool_budget
        self.timeout_seconds = timeout_seconds

    def check_needs_clarification(self, query: str, context_files: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
        """
        Detects underspecified or ambiguous queries before launching tools.
        """
        q = query.strip().lower()

        # Extremely short or vague queries lacking context
        if len(q.split()) <= 2:
            if q in ("run this", "execute this", "run it", "test it", "check output") and not context_files:
                return "Which code or file would you like me to execute? Please provide or paste the code snippet."
            if q in ("calculate", "solve it", "compute") and not any(c in q for c in "0123456789+-*/="):
                return "Please provide the mathematical expression, equation, or numbers you would like me to solve."
            if q in ("analyze", "summarize", "clean it") and not context_files:
                return "Please specify what you would like me to analyze, or attach a document/dataset."

        # Ambiguous file execution request with no attachments
        if any(phrase in q for phrase in ["run the script", "execute my file", "train on my dataset"]) and not context_files:
            return "No file or dataset is currently attached. Please upload the file or paste the content to proceed."

        return None

    def is_consequential_action(self, tool_name: str, args: Dict[str, Any]) -> bool:
        """Determines if an action modifies the filesystem, data, or external resources irreversibly."""
        if tool_name in self.CONSEQUENTIAL_TOOLS:
            return True
        # Check for destructive SQL operations in playground
        if tool_name == "sql_playground" and any(k in str(args.get("query", "")).upper() for k in ["DROP", "TRUNCATE", "DELETE", "ALTER"]):
            return True
        # Check code executor for destructive file calls
        if tool_name == "code_executor":
            code = str(args.get("code", "")).lower()
            if any(k in code for k in ["shutil.rmtree", "os.remove", "os.unlink", "drop table", "truncate table"]):
                return True
        return False

    def is_transient_error(self, error_message: str) -> bool:
        """Identifies transient network/service errors that are safe to retry once."""
        err_lower = (error_message or "").lower()
        if any(perm in err_lower for perm in self.PERMANENT_ERROR_SUBSTRINGS):
            return False
        return any(trans in err_lower for trans in ["timeout", "connection reset", "temporarily unavailable", "retry-after", "gateway timeout"])

    def execute_bounded_run(
        self,
        query: str,
        attached_files: Optional[List[Dict[str, Any]]] = None,
        pre_approved_actions: Optional[Set[str]] = None,
        status_callback: Optional[Callable[[str], None]] = None
    ) -> AgentExecutionResult:
        """
        Executes the bounded autonomous loop:
        1. Validates query completeness (clarification check).
        2. Detects required tools dynamically based on query + attached files.
        3. Enforces execution steps, wall-clock timeout, and tool budgets.
        4. Bounded retries for transient errors only.
        5. Comprehensive post-execution solution and evidence verification.
        """
        start_time = time.time()
        timeline = AgentTimeline(session_id=f"agent_{int(start_time)}", max_budget=self.max_tool_budget)
        executed_tools = []
        retrieved_sources = []
        pre_approved_actions = pre_approved_actions or set()

        def notify(msg: str):
            if status_callback:
                try:
                    status_callback(msg)
                except Exception:
                    pass

        # Step 1: Clarification Gate
        clarification = self.check_needs_clarification(query, attached_files)
        if clarification:
            notify("Awaiting clarification...")
            timeline.end_time = time.time()
            return AgentExecutionResult(
                content=clarification,
                status="needs_clarification",
                timeline=timeline,
                clarification_prompt=clarification
            )

        # Step 2: Determine Candidate Tools
        from core.intent import detect_intent, IntentType
        intent = detect_intent(query, attached_files)
        logger.info(f"Agent detected primary intent: {intent.value}")

        # Step 3: Autonomous Execution Loop
        step = 0
        final_answer = ""
        current_context = ""

        # Map candidate tools based on intent & query
        candidate_tools = []
        if intent == IntentType.MATH_CALCULATION:
            candidate_tools.append(("solve_math", {"expression": query}))
        elif intent == IntentType.PROGRAMMING:
            candidate_tools.append(("code_executor", {"code": query}))
        elif intent == IntentType.DOCUMENT_ANALYSIS:
            candidate_tools.append(("rag_search", {"query": query}))
        elif intent == IntentType.CURRENT_INFO:
            candidate_tools.append(("web_search", {"query": query}))

        # If no strict tool was pre-classified, check for keyword actions
        if not candidate_tools:
            q_lower = query.lower()
            if any(k in q_lower for k in ["calculate", "solve", "+", "-", "*", "/", "="]) and any(c.isdigit() for c in query):
                candidate_tools.append(("solve_math", {"expression": query}))
            elif any(k in q_lower for k in ["search", "latest", "news", "current price", "who won"]):
                candidate_tools.append(("web_search", {"query": query}))

        for tool_name, tool_args in candidate_tools:
            step += 1
            if step > self.max_steps or timeline.budget_used >= self.max_tool_budget:
                logger.warning("Agent budget exhausted. Halting execution loop.")
                break

            if time.time() - start_time > self.timeout_seconds:
                logger.warning("Agent wall-clock timeout reached.")
                timeline.end_time = time.time()
                return AgentExecutionResult(
                    content="Execution paused: Wall-clock timeout exceeded.",
                    status="timeout",
                    timeline=timeline,
                    executed_tools=executed_tools
                )

            action_id = f"act_{step}_{tool_name}"
            is_consequential = self.is_consequential_action(tool_name, tool_args)

            action = AgentAction(
                action_id=action_id,
                step_index=step,
                tool_name=tool_name,
                arguments=tool_args,
                is_consequential=is_consequential,
                requires_approval=is_consequential and (action_id not in pre_approved_actions)
            )

            # Approval Gate for consequential operations
            if action.requires_approval:
                action.status = ActionStatus.AWAITING_APPROVAL
                timeline.add_action(action)
                timeline.end_time = time.time()
                notify(f"Approval required for consequential action: {tool_name}")
                return AgentExecutionResult(
                    content=f"⚠️ **Action requires approval**: `{tool_name}` with arguments `{tool_args}` has potential system side-effects. Do you approve execution?",
                    status="needs_approval",
                    timeline=timeline,
                    executed_tools=executed_tools,
                    pending_approval=action
                )

            # Execute Tool with timing and bounded retries
            action.status = ActionStatus.RUNNING
            notify(f"Executing: {tool_name}...")
            t0 = time.time()

            max_retries = 1
            last_err = None
            res = None

            for attempt in range(max_retries + 1):
                try:
                    from tools.registry import dispatch_tool
                    res = dispatch_tool(tool_name, tool_args)
                    if res.get("success"):
                        last_err = None
                        break
                    else:
                        last_err = res.get("error", "Tool execution failed")
                        if not self.is_transient_error(last_err):
                            # Non-retriable: fail immediately without looping
                            break
                        notify(f"Transient issue encountered. Retrying {tool_name} once...")
                except Exception as e:
                    last_err = str(e)
                    if not self.is_transient_error(last_err):
                        break

            duration = (time.time() - t0) * 1000.0
            action.duration_ms = round(duration, 2)
            timeline.budget_used += 1

            if res and res.get("success"):
                action.status = ActionStatus.COMPLETED
                action.result = res
                executed_tools.append(tool_name)

                # Collect sources for verification
                if tool_name == "web_search":
                    for item in res.get("results", []):
                        retrieved_sources.append(item)
                elif tool_name == "rag_search":
                    for item in res.get("chunks", []):
                        retrieved_sources.append(item)

                current_context += f"\nObservation from {tool_name}: {json.dumps(res.get('result') or res.get('content') or res.get('results') or '')[:800]}"
            else:
                action.status = ActionStatus.FAILED
                action.error = last_err or "Unknown execution error"
                notify(f"Execution notice on {tool_name}: {action.error}")

            timeline.add_action(action)

        # Step 4: Synthesize Final Answer with Provider
        notify("Synthesizing response...")
        if self.llm:
            try:
                system_instruction = "You are SPARK-AI. Answer the user accurately using the provided observations. Clearly cite verified sources."
                prompt_with_obs = query
                if current_context:
                    prompt_with_obs += f"\n\nContext and Tool Observations:\n{current_context}"
                
                # Robust adapter supporting LLMProvider (messages, system_prompt) as well as legacy/mock (prompt, system)
                import inspect
                sig = inspect.signature(self.llm.generate)
                if "messages" in sig.parameters:
                    resp = self.llm.generate(
                        messages=[{"role": "user", "content": prompt_with_obs}],
                        system_prompt=system_instruction
                    )
                else:
                    resp = self.llm.generate(prompt=prompt_with_obs, system=system_instruction)
                final_answer = resp.get("content", "")
            except Exception as e:
                logger.error(f"Error during agent final synthesis: {e}")
                final_answer = f"Generated answer based on tool outputs: {current_context}"
        else:
            final_answer = current_context if current_context else "Task completed."

        # Step 5: Evidence & Solution Verification
        notify("Verifying solution and citations...")
        verification_rep = verify_evidence_and_citations(
            query=query,
            proposed_answer=final_answer,
            retrieved_sources=retrieved_sources
        )

        timeline.end_time = time.time()
        notify("Ready")

        return AgentExecutionResult(
            content=verification_rep.annotated_content if verification_rep else final_answer,
            status="success",
            timeline=timeline,
            executed_tools=executed_tools,
            verification_report=verification_rep
        )
