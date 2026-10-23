"""
Autonomous Multi-Step Tool Calling Loop with Verification.
Executes the Plan -> Call -> Observe -> Verify -> Answer cycle (max 5-6 steps).
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Tuple

from tools.registry import dispatch_tool
from core.verifier import verify_solution
from tools.web_search import extract_citations

logger = logging.getLogger("chatbot.tool_loop")

TOOL_CALL_REGEX = re.compile(r'```(?:tool_call|json)?\s*\n\s*(\{\s*"tool"\s*:\s*"[^"]+".*?\})\s*\n```', re.DOTALL)
ACTION_REGEX = re.compile(r'Action:\s*([a-zA-Z0-9_]+)\s*\nAction Input:\s*(\{.*?\})', re.DOTALL)


def extract_tool_call(content: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Extracts tool call name and arguments from LLM content if present.
    Supports JSON codeblocks:
    ```tool_call
    {"tool": "solve_math", "args": {"expression": "2*x + 5 = 15"}}
    ```
    or ReAct format:
    Action: solve_math
    Action Input: {"expression": "2*x + 5 = 15"}
    """
    if not content:
        return None

    # Check ```tool_call block
    match = TOOL_CALL_REGEX.search(content)
    if match:
        try:
            data = json.loads(match.group(1))
            tool_name = data.get("tool")
            args = data.get("args") or data.get("arguments") or {}
            if tool_name:
                return tool_name, args
        except Exception:
            pass

    # Check Action / Action Input format
    match_act = ACTION_REGEX.search(content)
    if match_act:
        try:
            tool_name = match_act.group(1).strip()
            args = json.loads(match_act.group(2).strip())
            return tool_name, args
        except Exception:
            pass

    # Direct raw JSON object if text is strictly a tool call
    stripped = content.strip()
    if stripped.startswith("{") and stripped.endswith("}") and '"tool"' in stripped:
        try:
            data = json.loads(stripped)
            tool_name = data.get("tool")
            args = data.get("args") or data.get("arguments") or {}
            if tool_name:
                return tool_name, args
        except Exception:
            pass

    return None


def run_tool_calling_loop(
    llm: Any,
    messages: List[Dict[str, Any]],
    system_prompt: str,
    user_query: str,
    task_type: Optional[str] = None,
    max_steps: int = 5,
    on_status_update: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Executes autonomous multi-step tool calling loop with post-verification.
    Cycles through Plan -> Call -> Observe -> Answer up to max_steps.
    Runs SymPy and Sandbox verification before final emission.
    """
    executed_tools: List[Dict[str, Any]] = []
    all_citations: List[Dict[str, Any]] = []
    generated_artifacts: List[Dict[str, Any]] = []

    current_messages = list(messages)
    last_llm_response = None
    final_content = ""

    # Instruct LLM on tool calling format
    tool_instruction = """
[TOOL CALLING FORMAT]
If you need to call a tool, output ONLY the tool call block:
```tool_call
{"tool": "<tool_name>", "args": {<arguments>}}
```
When you have all information needed to completely answer the user, provide your final comprehensive response directly without tool_call.
"""
    augmented_system_prompt = system_prompt + "\n" + tool_instruction

    for step in range(1, max_steps + 1):
        if on_status_update:
            on_status_update(f"Step {step}/{max_steps}: Reasoning...")

        logger.info(f"[TOOL LOOP] Step {step}/{max_steps} invoking LLM.")
        llm_response = llm.generate(
            messages=current_messages,
            system_prompt=augmented_system_prompt,
            task_type=task_type,
            on_status_update=on_status_update
        )
        last_llm_response = llm_response

        if not llm_response.get("success"):
            logger.warning(f"[TOOL LOOP] LLM failed at step {step}: {llm_response.get('error')}")
            break

        raw_content = llm_response.get("content", "").strip()
        tool_call = extract_tool_call(raw_content)

        if not tool_call:
            # LLM answered directly
            final_content = raw_content
            logger.info(f"[TOOL LOOP] Final answer produced at step {step}.")
            break

        tool_name, tool_args = tool_call
        logger.info(f"[TOOL LOOP] Executing tool: {tool_name} with args: {tool_args}")
        if on_status_update:
            on_status_update(f"Running tool: {tool_name}...")

        try:
            tool_result = dispatch_tool(tool_name, tool_args)
        except Exception as tool_err:
            tool_result = {
                "success": False,
                "error": f"Tool argument validation or runtime error: {str(tool_err)}. Please verify argument schema and retry."
            }

        executed_tools.append({"name": tool_name, "args": tool_args, "result": tool_result})

        # Check for citations from search
        if tool_name == "search_web":
            res_data = tool_result.get("result")
            if res_data:
                cites = extract_citations(res_data)
                all_citations.extend(cites)

        # Check for generated files
        if tool_name in ("generate_document", "create_calendar_file"):
            res = tool_result.get("result", {})
            if res.get("file_path"):
                generated_artifacts.append({
                    "type": "document",
                    "path": res["file_path"],
                    "name": res.get("filename", "output")
                })

        # Append observation to message thread
        obs_text = json.dumps(tool_result, default=str)
        if len(obs_text) > 3000:
            obs_text = obs_text[:3000] + "\n... [truncated]"

        current_messages.append({"role": "assistant", "content": raw_content})
        current_messages.append({
            "role": "user",
            "content": f"[Observation for {tool_name}]:\n{obs_text}\n\nContinue with next step or produce final answer."
        })

    # If loop ended without final content (e.g. hit max_steps), synthesize partial findings
    if not final_content:
        if executed_tools:
            tool_summary_lines = []
            for t in executed_tools:
                r_preview = str(t.get("result", {}))[:130].replace("\n", " ")
                tool_summary_lines.append(f"- **`{t['name']}`**: `{json.dumps(t.get('args', {}))}` → *{r_preview}*")
            tools_summary = "\n".join(tool_summary_lines)

            interim_text = ""
            if last_llm_response and last_llm_response.get("content"):
                interim_text = re.sub(r'```tool_call[\s\S]*?```', '', last_llm_response.get("content", "")).strip()

            final_content = (
                f"### ⏳ Partial Answer (Completed {len(executed_tools)} Tool Steps)\n\n"
                f"The maximum autonomous tool investigation limit ({max_steps} steps) was reached. "
                f"Here is a summary of the diagnostic tools executed:\n\n"
                f"{tools_summary}\n\n"
                f"**Synthesized Findings:**\n"
                f"{interim_text if interim_text else 'Data collection completed. Please ask a follow-up question for deeper analysis.'}"
            )
        elif last_llm_response and last_llm_response.get("success"):
            final_content = last_llm_response.get("content", "")

    # Clean any remaining tool_call markers from final content
    final_content = re.sub(r'```tool_call[\s\S]*?```', '', final_content).strip()

    # If we have a final content, run the VERIFIER STEP
    verification_badges = []
    if final_content:
        if on_status_update:
            on_status_update("Verifying math and code accuracy...")
        verified = verify_solution(user_query, final_content)
        final_content = verified["content"]
        verification_badges = verified["badges"]

    # Deduplicate citations
    unique_citations = []
    seen_urls = set()
    for c in all_citations:
        u = c.get("url")
        if u and u not in seen_urls:
            seen_urls.add(u)
            unique_citations.append(c)

    return {
        "success": bool(last_llm_response and last_llm_response.get("success")),
        "content": final_content,
        "executed_tools": executed_tools,
        "citations": unique_citations,
        "verification_badges": verification_badges,
        "generated_artifacts": generated_artifacts,
        "provider": last_llm_response.get("provider") if last_llm_response else None,
        "model": last_llm_response.get("model") if last_llm_response else None,
        "fallback_notice": last_llm_response.get("fallback_notice") if last_llm_response else None,
        "rate_limit_suggestion": last_llm_response.get("rate_limit_suggestion") if last_llm_response else False,
        "error": last_llm_response.get("error") if last_llm_response else "Failed to generate answer."
    }
