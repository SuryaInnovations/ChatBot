"""
Multi-provider LLM client supporting OpenAI, Google Gemini, Groq, Ollama, and local fallback.
Handles tool calling and unified message formatting.
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple, Callable
from tools.registry import TOOL_DEFINITIONS, dispatch_tool

class LLMProvider:
    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.2
    ):
        self.provider = provider.lower()
        self.api_key = api_key or os.environ.get(f"{provider.upper()}_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url
        self.temperature = temperature
        
        # Default model selection per provider
        if not model:
            if self.provider == "openai":
                self.model = "gpt-4o-mini"
            elif self.provider == "gemini":
                self.model = "gemini-2.5-flash"
            elif self.provider == "groq":
                self.model = "llama-3.3-70b-versatile"
            elif self.provider == "ollama":
                self.model = "llama3.2"
            else:
                self.model = "gpt-4o-mini"
        else:
            self.model = model

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Sends conversation to LLM, handles multi-step tool execution loop, and returns final answer.
        """
        if self.provider == "openai" or self.provider == "ollama":
            return self._call_openai_compatible(messages, system_prompt, tools, on_tool_call)
        elif self.provider == "groq":
            return self._call_groq(messages, system_prompt, tools, on_tool_call)
        elif self.provider == "gemini":
            return self._call_gemini(messages, system_prompt, tools, on_tool_call)
        else:
            return self._call_autonomous_local(messages, system_prompt, on_tool_call)

    def _call_openai_compatible(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        import openai
        
        client_kwargs = {}
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        elif self.provider == "ollama":
            client_kwargs["base_url"] = "http://localhost:11434/v1"
            if "api_key" not in client_kwargs or not client_kwargs["api_key"]:
                client_kwargs["api_key"] = "ollama"

        client = openai.OpenAI(**client_kwargs)

        # Prepare messages
        formatted_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            msg_obj = {"role": m["role"], "content": m.get("content", "")}
            if "tool_calls" in m:
                msg_obj["tool_calls"] = m["tool_calls"]
            if "tool_call_id" in m:
                msg_obj["tool_call_id"] = m["tool_call_id"]
            formatted_messages.append(msg_obj)

        executed_tools_record = []
        max_tool_iterations = 6

        for _ in range(max_tool_iterations):
            try:
                kwargs = {
                    "model": self.model,
                    "messages": formatted_messages,
                    "temperature": self.temperature,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"

                response = client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                message = choice.message

                # Check if model made tool calls
                if message.tool_calls:
                    # Append assistant message with tool calls
                    formatted_messages.append({
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in message.tool_calls
                        ]
                    })

                    # Execute each tool call
                    for tc in message.tool_calls:
                        func_name = tc.function.name
                        try:
                            func_args = json.loads(tc.function.arguments)
                        except Exception:
                            func_args = {}

                        if on_tool_call:
                            on_tool_call(func_name, func_args)

                        tool_res = dispatch_tool(func_name, func_args)
                        executed_tools_record.append({
                            "name": func_name,
                            "args": func_args,
                            "result": tool_res
                        })

                        # Feed result back
                        formatted_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(tool_res)
                        })
                    # Continue loop to let model synthesize answer
                    continue

                # No more tool calls, return final message
                return {
                    "success": True,
                    "content": message.content or "",
                    "executed_tools": executed_tools_record,
                    "provider": self.provider,
                    "model": self.model
                }

            except openai.RateLimitError as rle:
                # Fallback to local autonomous execution if quota is exhausted
                return self._fallback_error(str(rle), messages, on_tool_call)
            except Exception as e:
                return {"success": False, "error": str(e), "executed_tools": executed_tools_record}

        return {
            "success": True,
            "content": "Execution completed maximum tool chaining iterations.",
            "executed_tools": executed_tools_record
        }

    def _call_groq(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        import groq
        client = groq.Groq(api_key=self.api_key)

        formatted_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            msg_obj = {"role": m["role"], "content": m.get("content", "")}
            if "tool_calls" in m:
                msg_obj["tool_calls"] = m["tool_calls"]
            if "tool_call_id" in m:
                msg_obj["tool_call_id"] = m["tool_call_id"]
            formatted_messages.append(msg_obj)

        executed_tools_record = []
        max_tool_iterations = 6

        for _ in range(max_tool_iterations):
            try:
                kwargs = {
                    "model": self.model if self.model.startswith("llama") or self.model.startswith("mixtral") else "llama-3.3-70b-versatile",
                    "messages": formatted_messages,
                    "temperature": self.temperature,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"

                response = client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                message = choice.message

                if message.tool_calls:
                    formatted_messages.append({
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in message.tool_calls
                        ]
                    })

                    for tc in message.tool_calls:
                        func_name = tc.function.name
                        try:
                            func_args = json.loads(tc.function.arguments)
                        except Exception:
                            func_args = {}

                        if on_tool_call:
                            on_tool_call(func_name, func_args)

                        tool_res = dispatch_tool(func_name, func_args)
                        executed_tools_record.append({
                            "name": func_name,
                            "args": func_args,
                            "result": tool_res
                        })

                        formatted_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(tool_res)
                        })
                    continue

                return {
                    "success": True,
                    "content": message.content or "",
                    "executed_tools": executed_tools_record,
                    "provider": "groq",
                    "model": kwargs["model"]
                }
            except Exception as e:
                return self._fallback_error(str(e), messages, on_tool_call)

        return {"success": True, "content": "Tool chaining completed.", "executed_tools": executed_tools_record}

    def _call_gemini(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            
            # Simple direct prompt generation
            conversation_text = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nCONVERSATION HISTORY:\n"
            for m in messages:
                conversation_text += f"\n{m['role'].upper()}: {m['content']}\n"
            
            response = client.models.generate_content(
                model=self.model if "gemini" in self.model else "gemini-2.5-flash",
                contents=conversation_text
            )
            return {
                "success": True,
                "content": response.text or "",
                "executed_tools": [],
                "provider": "gemini",
                "model": self.model
            }
        except Exception as e:
            return self._fallback_error(str(e), messages, on_tool_call)

    def _fallback_error(self, err_msg: str, messages: List[Dict[str, Any]], on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        When cloud API keys hit rate limits or are unavailable, the autonomous local engine handles it seamlessly!
        """
        local_res = self._call_autonomous_local(messages, "", on_tool_call)
        
        notice = f"> [!NOTE]\n> **Cloud API Notice**: `{err_msg}`\n> The assistant seamlessly processed your request using the **Autonomous Engine & Local Tools**."
        
        return {
            "success": True,
            "content": f"{notice}\n\n{local_res['content']}",
            "executed_tools": local_res.get("executed_tools", []),
            "provider": "autonomous_local",
            "model": "rule-and-tools-engine"
        }

    def _call_autonomous_local(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Autonomous rule-based pipeline that inspects the query, selects the minimum necessary tools,
        executes them, and formats the response according to the Master System Prompt guidelines.
        """
        last_message = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_message = m.get("content", "")
                break

        query = last_message.strip()
        executed_tools = []
        q_lower = query.lower()

        # 1. Financial calculation
        if any(term in q_lower for term in ["compound interest", "simple interest", "emi", "interest for"]):
            import re
            p_match = re.search(r'(?:₹|\$|rs\.?|principal\s*of)?\s*(\d[\d,]*(?:\.\d+)?)', query, re.I)
            r_match = re.search(r'(\d+(?:\.\d+)?)\s*%', query)
            t_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?|months?)', query, re.I)

            p = float(p_match.group(1).replace(",", "")) if p_match else 10000.0
            r = float(r_match.group(1)) if r_match else 8.0
            t = float(t_match.group(1)) if t_match else 3.0
            calc_type = "emi" if "emi" in q_lower else ("simple" if "simple" in q_lower else "compound")

            if on_tool_call:
                on_tool_call("calculate_finance", {"calc_type": calc_type, "principal": p, "rate_pct": r, "time_years": t})

            tool_res = dispatch_tool("calculate_finance", {"calc_type": calc_type, "principal": p, "rate_pct": r, "time_years": t})
            executed_tools.append({"name": "calculate_finance", "result": tool_res})

            res_data = tool_res.get("result", {})
            amt = res_data.get("total_amount", 0)
            interest = res_data.get("total_interest", 0)
            formula = res_data.get("formula", "")

            content = f"""### Financial Calculation Result

**Formula:**
`{formula}`

**Substitution:**
* Principal ($P$): ₹{p:,.2f}
* Annual Rate ($R$): {r}%
* Time ($T$): {t} years

**Calculation:**
* Total Accrued Amount: ₹{amt:,.2f}
* Interest Earned: ₹{interest:,.2f}

**Final Answer:**
The investment of **₹{p:,.2f}** at **{r}%** interest for **{t} years** grows to **₹{amt:,.2f}** (with an interest return of **₹{interest:,.2f}**).
"""
            return {"success": True, "content": content, "executed_tools": executed_tools}

        # 2. Mathematical expression / equation
        if any(term in q_lower for term in ["solve", "equation", "derivative of", "integral of", "simplify", "calculate"]) and any(c in query for c in "+-*/^="):
            task_type = "derivative" if "derivative" in q_lower else ("integral" if "integral" in q_lower else ("solve_equation" if "=" in query else "eval"))
            # clean expr
            clean_expr = query
            for prefix in ["solve", "calculate", "find", "evaluate", "what is"]:
                if clean_expr.lower().startswith(prefix):
                    clean_expr = clean_expr[len(prefix):].strip()

            if on_tool_call:
                on_tool_call("solve_math", {"expression": clean_expr, "task_type": task_type})

            tool_res = dispatch_tool("solve_math", {"expression": clean_expr, "task_type": task_type})
            executed_tools.append({"name": "solve_math", "result": tool_res})

            data = tool_res.get("result", {})
            if data.get("success"):
                sol = data.get("solutions") or data.get("numeric") or data.get("derivative") or data.get("integral") or data.get("result")
                content = f"""### Mathematics Solution

**Problem:**
${clean_expr}$

**Calculation:**
Step-by-step symbolic evaluation performed.

**Final Answer:**
The exact evaluated result is: **{sol}**
"""
                return {"success": True, "content": content, "executed_tools": executed_tools}

        # 3. Current information / Web Search
        if any(term in q_lower for term in ["latest", "current", "news", "today", "price", "version", "syllabus", "who is", "weather"]):
            if on_tool_call:
                on_tool_call("search_web", {"query": query, "max_results": 5})

            tool_res = dispatch_tool("search_web", {"query": query, "max_results": 5})
            executed_tools.append({"name": "search_web", "result": tool_res})

            results = tool_res.get("result", [])
            content_lines = ["### Live Web Information\n"]
            if results and not isinstance(results, str):
                for item in results:
                    content_lines.append(f"**[{item.get('title')}]({item.get('href')})**\n{item.get('body')}\n")
            else:
                content_lines.append("No live web results returned.")

            return {"success": True, "content": "\n".join(content_lines), "executed_tools": executed_tools}

        # 4. Python code execution request
        if "python" in q_lower and ("code" in q_lower or "script" in q_lower or "run" in q_lower or "plot" in q_lower):
            # If code block in query
            if "```" in query:
                code_snippet = query.split("```")[1]
                if code_snippet.startswith("python"):
                    code_snippet = code_snippet[6:].strip()
                if on_tool_call:
                    on_tool_call("execute_python_code", {"code": code_snippet})
                tool_res = dispatch_tool("execute_python_code", {"code": code_snippet})
                executed_tools.append({"name": "execute_python_code", "result": tool_res})
                res_dict = tool_res.get("result", {})
                out = res_dict.get("stdout", "")
                err = res_dict.get("stderr", "")
                imgs = res_dict.get("generated_images", [])

                content = f"### Python Execution Result\n\n```text\n{out or '(No stdout output)'}\n```\n"
                if err:
                    content += f"\n**Stderr / Diagnostic:**\n```text\n{err}\n```\n"
                if imgs:
                    content += f"\n**Generated Plot(s):**\nSaved {len(imgs)} figure(s) to `artifacts/`."
                return {"success": True, "content": content, "executed_tools": executed_tools}

        # Default knowledge response
        content = f"""### Response

I have analyzed your request: **"{query}"**.

To provide full generative conversational assistance across all topics, please provide an active API key in the sidebar:
- **Groq API Key** (Free, instant high-speed tier)
- **Google Gemini API Key** (Free tier available)
- **OpenAI API Key** (Requires active billing balance)
- Or run local **Ollama** (`http://localhost:11434`)

All autonomous tools (**Live Web Search, Python Sandbox Code Execution, SymPy Math Solver, Document Generation, and File Intelligence**) are active and working!
"""
        return {"success": True, "content": content, "executed_tools": executed_tools}
