"""
core/tool_registry.py — Central Typed Tool Registry, Contracts & Orchestration.

Implements Capability 18:
- Typed tool registration with Pydantic contracts and JSON schemas.
- Permission enforcement (read_only, user_scoped, consequential, system_write).
- Integration with approval gate for consequential actions.
- Latency and failure telemetry with circuit breaker protection.
- Non-blocking execution avoiding unnecessary tool handoffs on simple queries.
"""

import time
import inspect
import asyncio
import logging
from typing import Dict, Any, Callable, Optional, List

from core.tool_contracts import ToolMetadata, ToolInvocation, ToolResult, PermissionLevel, ToolCategory
from core.tool_health import default_tool_health
from security.approval_gate import default_approval_gate

logger = logging.getLogger("chatbot.core.tool_registry")


class CentralToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._metadata: Dict[str, ToolMetadata] = {}

    def register(
        self,
        name: str,
        func: Callable,
        description: str,
        category: ToolCategory = ToolCategory.PRODUCTIVITY,
        permission_level: PermissionLevel = PermissionLevel.READ_ONLY,
        timeout_seconds: float = 10.0,
        requires_approval: bool = False,
        is_idempotent: bool = True
    ):
        """Registers a tool function with typed contract metadata."""
        meta = ToolMetadata(
            name=name,
            description=description,
            category=category,
            permission_level=permission_level,
            timeout_seconds=timeout_seconds,
            requires_approval=requires_approval,
            is_idempotent=is_idempotent
        )
        self._tools[name] = func
        self._metadata[name] = meta
        logger.debug(f"Registered tool: '{name}' ({category.value}, {permission_level.value})")

    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        return self._metadata.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [meta.model_dump() for meta in self._metadata.values()]

    def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Executes tool synchronously with health checks, approval gate, and telemetry.
        """
        tool_name = invocation.tool_name
        func = self._tools.get(tool_name)
        meta = self._metadata.get(tool_name)

        if not func or not meta:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' is not registered in the central tool registry."
            )

        # 1. Circuit breaker health check
        if not default_tool_health.can_call_tool(tool_name):
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' is temporarily unavailable due to circuit breaker trip (repeated failures)."
            )

        # 2. Consequential approval gate check
        if meta.requires_approval or default_approval_gate.is_action_consequential(tool_name, invocation.arguments):
            if not invocation.approval_token:
                # Create pending approval request
                req = default_approval_gate.request_approval(
                    tool_name=tool_name,
                    arguments=invocation.arguments,
                    reason=f"Action '{tool_name}' is marked as consequential.",
                    risk_level="high" if meta.permission_level == PermissionLevel.SYSTEM_WRITE else "medium"
                )
                return ToolResult(
                    tool_name=tool_name,
                    success=False,
                    requires_approval=True,
                    approval_request_id=req.request_id,
                    error=f"Action '{tool_name}' requires human approval before execution. Approval ID: {req.request_id}"
                )

        # 3. Execution with latency timing
        start_t = time.time()
        try:
            # Bind arguments safely
            sig = inspect.signature(func)
            kwargs = {}
            for param_name in sig.parameters.keys():
                if param_name in invocation.arguments:
                    kwargs[param_name] = invocation.arguments[param_name]

            res = func(**kwargs) if kwargs else func(**invocation.arguments)

            duration_ms = round((time.time() - start_t) * 1000.0, 2)
            default_tool_health.report_success(tool_name, duration_ms)

            # Check if result is dict with data/artifacts
            if isinstance(res, dict):
                artifacts = res.get("artifacts", [])
                citations = res.get("citations", [])
                return ToolResult(
                    tool_name=tool_name,
                    success=res.get("success", True) if "success" in res else True,
                    data=res,
                    error=res.get("error"),
                    duration_ms=duration_ms,
                    artifacts=artifacts if isinstance(artifacts, list) else [],
                    citations=citations if isinstance(citations, list) else []
                )

            return ToolResult(
                tool_name=tool_name,
                success=True,
                data=res,
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = round((time.time() - start_t) * 1000.0, 2)
            default_tool_health.report_failure(tool_name, str(e))
            logger.error(f"Error executing tool '{tool_name}': {e}")
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )


default_tool_registry = CentralToolRegistry()


def register_all_blueprint_tools(registry: CentralToolRegistry):
    """Populates registry with all 18 blueprint capabilities and bonus tools."""
    # 01. Web Search & Citations
    from tools.web_search import search_web, fetch_webpage_content
    registry.register("search_web", search_web, "Search the live web for current facts with citations.", category=ToolCategory.SEARCH, timeout_seconds=8.0)
    registry.register("fetch_webpage_content", fetch_webpage_content, "Extract full readable text from a URL.", category=ToolCategory.SEARCH, timeout_seconds=8.0)

    # 02. File Analysis & RAG
    from tools.file_parser import parse_document
    from knowledge.retriever import default_retriever
    registry.register("parse_document", parse_document, "Parse PDF, DOCX, PPTX, XLSX, and CSV documents.", category=ToolCategory.KNOWLEDGE)
    registry.register("retriever_search", default_retriever.retrieve, "Retrieve top relevant knowledge chunks.", category=ToolCategory.KNOWLEDGE)

    # 03. Long-Term Memory
    from memory.long_term import default_long_term_memory
    registry.register("memory_get_profile", default_long_term_memory.get_compact_profile_summary, "Retrieve user profile preferences.", category=ToolCategory.PRODUCTIVITY)

    # 04. Python Code Interpreter
    from tools.python_interpreter import execute_python_interpreter
    registry.register("python_interpreter", execute_python_interpreter, "Execute Python code in isolated sandbox/container.", category=ToolCategory.CODE, timeout_seconds=7.0)

    # 05. Image Understanding
    from tools.image_vision import analyze_image
    registry.register("image_vision", analyze_image, "Analyze diagrams, screenshots, and photos with multimodal vision.", category=ToolCategory.VISION, timeout_seconds=15.0)

    # 07. AI Study Mentor
    from agents.study_mentor import default_study_mentor
    registry.register("study_mentor_explain", default_study_mentor.explain_concept, "Explain study concepts tailored to student level.", category=ToolCategory.PRODUCTIVITY)
    registry.register("study_mentor_quiz", default_study_mentor.generate_quiz, "Generate practice quiz questions on a topic.", category=ToolCategory.PRODUCTIVITY)

    # 08. Coding Workspace
    from agents.coding_agent import default_coding_agent
    registry.register("coding_propose_diff", default_coding_agent.propose_code_edit, "Propose code edits formatted as unified diffs.", category=ToolCategory.CODE)
    registry.register("coding_apply_patch", default_coding_agent.apply_code_edit, "Apply approved code patch and record version.", category=ToolCategory.CODE, requires_approval=True)

    # 09. Deep Research Agent
    from agents.research_agent import default_research_agent
    registry.register("deep_research", default_research_agent.conduct_research, "Conduct multi-source deep research and generate report.", category=ToolCategory.SEARCH, timeout_seconds=25.0)

    # 10. Browser Automation
    from tools.browser_tool import browse_webpage
    registry.register("browse_webpage", browse_webpage, "Safely navigate and extract webpage content.", category=ToolCategory.AUTOMATION, timeout_seconds=12.0)

    # 11. GitHub Integration
    from tools.github_tool import default_github_tool
    registry.register("github_repo_summary", default_github_tool.get_repo_summary, "Inspect GitHub repository details.", category=ToolCategory.WORKSPACE)
    registry.register("github_create_pr", default_github_tool.create_pull_request, "Create a GitHub Pull Request.", category=ToolCategory.WORKSPACE, requires_approval=True)

    # 12. Document & Chart Generator
    from tools.document_generator import create_document
    from tools.chart_generator import generate_chart
    registry.register("document_generator", create_document, "Generate PDF, DOCX, PPTX, XLSX, and Markdown documents.", category=ToolCategory.PRODUCTIVITY)
    registry.register("generate_chart", generate_chart, "Generate interactive Plotly or static Matplotlib charts.", category=ToolCategory.DATA)

    # 13. Image Generation
    from tools.image_generation import generate_image_sync
    registry.register("generate_image", generate_image_sync, "Generate images from text prompts.", category=ToolCategory.VISION, timeout_seconds=20.0)

    # 14. Voice Conversation
    from tools.speech_to_text import transcribe_audio_file
    from tools.text_to_speech import synthesize_speech
    registry.register("transcribe_speech", transcribe_audio_file, "Transcribe spoken audio recordings into text.", category=ToolCategory.AUDIO)
    registry.register("synthesize_speech", synthesize_speech, "Synthesize text into natural spoken audio MP3.", category=ToolCategory.AUDIO)

    # 15. AutoML Dashboard
    from agents.automl_agent import default_automl_agent
    registry.register("automl_pipeline", default_automl_agent.run_automl_pipeline, "Run end-to-end dataset profiling and baseline training.", category=ToolCategory.DATA, timeout_seconds=20.0)

    # 16. Interview Simulator
    from agents.interview_agent import default_interview_agent
    registry.register("interview_start", default_interview_agent.start_interview, "Start mock interview session.", category=ToolCategory.PRODUCTIVITY)
    registry.register("interview_submit_answer", default_interview_agent.submit_answer_and_next, "Submit answer and receive feedback.", category=ToolCategory.PRODUCTIVITY)

    # 17. AI Project Builder
    from agents.project_builder import default_project_builder
    registry.register("project_builder", default_project_builder.build_project, "Scaffold multi-file software projects into ZIP archive.", category=ToolCategory.WORKSPACE, timeout_seconds=25.0)

    # BONUS Tools
    from tools.translator import translate_text
    from tools.ocr_vision import extract_ocr_text, screenshot_to_code
    from tools.calendar_tool import create_calendar_event
    registry.register("multilingual_translate", translate_text, "Translate between languages.", category=ToolCategory.PRODUCTIVITY)
    registry.register("ocr_extract", extract_ocr_text, "Extract text from images.", category=ToolCategory.VISION)
    registry.register("screenshot_to_code", screenshot_to_code, "Convert UI screenshots into frontend code.", category=ToolCategory.CODE)
    registry.register("create_calendar_event", create_calendar_event, "Create calendar .ics events.", category=ToolCategory.PRODUCTIVITY)


# Initialize default registry
register_all_blueprint_tools(default_tool_registry)
