"""
Universal Request Pipeline Orchestrator.
Executes the UNDERSTAND -> PLAN -> ROUTE -> EXECUTE -> VERIFY -> RESPOND pipeline.
"""

from typing import Dict, Any, List, Optional, Callable
import os
from datetime import datetime

from core.prompt import get_system_prompt
from core.conversation import ConversationSession
from core.llm_provider import LLMProvider
from tools.registry import TOOL_DEFINITIONS, dispatch_tool
from tools.file_analyzer import analyze_file

class ChatbotOrchestrator:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def process_message(
        self,
        session: ConversationSession,
        user_message: str,
        custom_instructions: str = "",
        on_status_update: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes the full Universal Request Pipeline.
        """
        if on_status_update:
            on_status_update("Understanding user intent & planning...")

        # 1. Process and attach any new file context
        active_files = session.attached_files

        # 2. Add user message to session
        session.add_message("user", user_message)

        # 3. Build dynamic system prompt
        system_prompt = get_system_prompt(
            custom_instructions=custom_instructions,
            active_files=active_files
        )

        # 4. Tool execution callback
        def on_tool_call(tool_name: str, args: Dict[str, Any]):
            if on_status_update:
                if tool_name == "search_web":
                    on_status_update(f"Searching web for: {args.get('query', '')}...")
                elif tool_name == "execute_python_code":
                    on_status_update("Executing Python computation...")
                elif tool_name == "solve_math" or tool_name == "calculate_finance":
                    on_status_update("Solving mathematical equations...")
                elif tool_name == "analyze_file":
                    on_status_update(f"Analyzing file: {os.path.basename(args.get('file_path', ''))}...")
                elif tool_name == "generate_document":
                    on_status_update(f"Generating {args.get('format_type', 'doc').upper()} document...")
                else:
                    on_status_update(f"Executing tool {tool_name}...")

        # 5. Call LLM with tool routing
        if on_status_update:
            on_status_update("Processing reasoning & executing pipeline...")

        response = self.provider.chat_completion(
            messages=session.messages,
            system_prompt=system_prompt,
            tools=TOOL_DEFINITIONS,
            on_tool_call=on_tool_call
        )

        final_content = response.get("content", "")
        executed_tools = response.get("executed_tools", [])

        # 6. Check for generated artifacts (files or charts)
        generated_artifacts = []
        for et in executed_tools:
            res = et.get("result", {})
            # Document generation result
            if et.get("name") == "generate_document" and res.get("result", {}).get("success"):
                doc_info = res.get("result", {})
                generated_artifacts.append({
                    "type": "document",
                    "path": doc_info.get("file_path"),
                    "name": doc_info.get("filename"),
                    "format": doc_info.get("format")
                })
                session.project_context["generated_files"].append(doc_info.get("filename"))
            # Code execution charts
            elif et.get("name") == "execute_python_code":
                imgs = res.get("result", {}).get("generated_images", [])
                for img in imgs:
                    generated_artifacts.append({
                        "type": "image",
                        "path": img,
                        "name": os.path.basename(img)
                    })

        # 7. Add assistant message to session
        session.add_message("assistant", final_content)

        if on_status_update:
            on_status_update("Task completed.")

        return {
            "success": response.get("success", True),
            "content": final_content,
            "executed_tools": executed_tools,
            "generated_artifacts": generated_artifacts,
            "provider": response.get("provider", self.provider.provider),
            "model": response.get("model", self.provider.model)
        }
