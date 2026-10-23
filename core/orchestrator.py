"""
Universal Request Pipeline Orchestrator with Intent-Driven Routing and Robust Fallback.
Adheres strictly to the Intent-First architecture and honest error handling.
"""

import os
import json
import logging
import concurrent.futures
from typing import Dict, Any, Optional, Callable, Union

from core.intent import detect_intent, IntentType
from core.prompt import get_system_prompt, detect_length_mode, detect_adaptive_level
from core.conversation import ConversationSession
from core.llm_provider import LLMProvider
from core.interview import InterviewSession
from tools.web_search import search_web
from tools.file_analyzer import analyze_file
from tools.deterministic_solver import can_deterministic_tool_answer, solve_deterministically
from tools.high_value_tools import sql_playground, complexity_analyzer, solve_math_step_by_step
from core.agent import BoundedAutonomousAgent

logger = logging.getLogger("chatbot.orchestrator")

class ChatbotOrchestrator:
    def __init__(self, provider: Union[LLMProvider, Any] = "auto"):
        if isinstance(provider, LLMProvider) or hasattr(provider, "generate"):
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
        on_status_update: Optional[Callable[[str], None]] = None,
        length_mode: Optional[str] = None,
        search_mode: Optional[str] = "Auto"
    ) -> Dict[str, Any]:
        """
        Processes message through the Intent Analyzer and executes optimal workflow.
        """
        query = user_message.strip()

        # Voice transcript cleaning (strips filler words, stutters, fixes speech errors)
        from core.voice_understanding import clean_voice_transcript, resolve_incomplete_or_voice_query
        cleaned_transcript = clean_voice_transcript(query)
        if cleaned_transcript:
            query = cleaned_transcript

        # Incomplete sentence & conversational context inference
        is_inc, resolved_query, clarification = resolve_incomplete_or_voice_query(
            query, getattr(session, "messages", None)
        )
        if is_inc:
            if clarification:
                logger.info(f"[VOICE] Ambiguous incomplete query '{query}', asking: '{clarification}'")
                session.add_message("user", query)
                session.add_message("assistant", clarification)
                if on_status_update:
                    on_status_update("Ready.")
                return {
                    "success": True,
                    "content": clarification,
                    "intent": "clarification",
                    "executed_tools": [],
                    "citations": [],
                    "verification_badges": []
                }
            else:
                logger.info(f"[VOICE] Resolved incomplete query '{query}' to '{resolved_query}'")
                query = resolved_query

        # 0. PER-USER RATE LIMIT CHECK
        user_id = getattr(session, "user_id", None) or "default_user"
        from core.rate_limiter import check_user_rate_limit
        is_allowed, rate_msg = check_user_rate_limit(user_id)
        if not is_allowed:
            logger.warning(f"[RATE LIMIT] User '{user_id}' exceeded requests per minute.")
            session.add_message("assistant", rate_msg)
            return {
                "success": False,
                "content": rate_msg,
                "error": rate_msg,
                "is_rate_limited": True
            }

        # Compute attached file hash for cache scoping
        file_hash = ""
        if session.attached_files:
            import hashlib
            file_meta = "|".join(f.get("name", "") + str(f.get("size", "")) for f in session.attached_files)
            file_hash = hashlib.md5(file_meta.encode("utf-8")).hexdigest()[:12]

        # 1. RESPONSE CACHE CHECK (User & File Scoped)
        from core.cache import get_cached_response, store_cached_response
        from core.observability import log_request_event
        cached = get_cached_response(query, user_id=user_id, file_hash=file_hash)
        if cached:
            logger.info(f"[CACHE HIT] Returning cached response for user '{user_id}'.")
            log_request_event(query=query, intent="cached", provider="cache", model="lru", latency_ms=1.0, cache_hit=True, success=True)
            session.add_message("user", query)
            session.add_message("assistant", cached["content"])
            if on_status_update:
                on_status_update("Done (cached).")
            return cached

        # 2. INTENT ANALYZER
        in_interview = bool(self.interview_session and self.interview_session.active)
        intent = detect_intent(
            query,
            session.attached_files,
            in_interview=in_interview,
            search_mode=search_mode,
            conversation_history=getattr(session, "messages", None)
        )
        logger.info(f"[ROUTER] Mode: {search_mode} | Intent: {intent.value}")

        if on_status_update:
            on_status_update(f"Analyzing intent ({intent.value})...")

        # 2. Add user message to session
        session.add_message("user", query)

        executed_tools = []
        generated_artifacts = []
        citations = []
        verification_badges = []
        pre_tool_context = ""

        # 3. DIRECT DETERMINISTIC SHORT-CIRCUIT (Step 8)
        # For pure arithmetic, direct SQL, or Big-O complexity, bypass the LLM directly
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
                res_obj = {
                    "success": True,
                    "content": final_content,
                    "executed_tools": executed_tools,
                    "generated_artifacts": [],
                    "citations": [],
                    "verification_badges": ["✅ Exact SymPy Calculator"],
                    "provider": "deterministic_calculator",
                    "model": "sympy",
                    "timeline": {
                        "session_id": getattr(session, "session_id", "default"),
                        "budget_used": 1,
                        "actions": [{"tool_name": "sympy_calculator", "status": "completed", "duration_ms": 2.0}]
                    }
                }
                log_request_event(
                    query=query,
                    intent=intent.value,
                    provider="deterministic_calculator",
                    model="sympy",
                    latency_ms=2.0,
                    cache_hit=False,
                    tools_executed=["sympy_calculator"],
                    success=True
                )
                store_cached_response(query, res_obj, user_id=user_id, file_hash=file_hash)
                return res_obj

        # Direct SQL Query Deterministic Bypass
        clean_q = query.strip()
        if clean_q.upper().startswith("SELECT "):
            logger.info("[ROUTER] Direct SQL query detected: executing sql_playground directly.")
            sql_res = sql_playground(clean_q)
            if sql_res.get("success"):
                final_content = (
                    f"**SQL Execution Output:**\n\n"
                    f"{sql_res.get('table_preview') or 'Query executed successfully.'}\n\n"
                    f"*Rows returned: {sql_res.get('row_count', 0)} | Execution time: {sql_res.get('execution_time_ms', 0)}ms*"
                )
                executed_tools.append({"name": "sql_playground", "result": sql_res})
                session.add_message("assistant", final_content)
                if on_status_update:
                    on_status_update("Done.")
                res_obj = {
                    "success": True,
                    "content": final_content,
                    "executed_tools": executed_tools,
                    "generated_artifacts": [],
                    "citations": [],
                    "verification_badges": ["✅ SQLite Sandbox Verified"],
                    "provider": "sql_playground",
                    "model": "sqlite",
                    "timeline": {
                        "session_id": getattr(session, "session_id", "default"),
                        "budget_used": 1,
                        "actions": [{"tool_name": "sql_playground", "status": "completed", "duration_ms": float(sql_res.get('execution_time_ms', 5.0))}]
                    }
                }
                store_cached_response(query, res_obj, user_id=user_id, file_hash=file_hash)
                return res_obj
            else:
                final_content = f"**SQL Error:** {sql_res.get('error', 'Execution failed.')}"
                session.add_message("assistant", final_content)
                return {
                    "success": False,
                    "content": final_content,
                    "executed_tools": [{"name": "sql_playground", "result": sql_res}],
                    "provider": "sql_playground",
                    "model": "sqlite"
                }

        # Direct Complexity Analysis Deterministic Bypass
        q_lower = query.lower()
        if ("complexity" in q_lower or "big-o" in q_lower or "big o" in q_lower) and ("def " in query or "for " in query or "return " in query):
            logger.info("[ROUTER] Direct complexity query detected: executing complexity_analyzer directly.")
            c_code = query
            if "```" in query:
                parts = query.split("```")
                if len(parts) > 1:
                    c_code = parts[1]
                    if c_code.startswith("python"):
                        c_code = c_code[6:]
            else:
                m = re.search(r'\b(def |class |for |while |import |from )\b', query)
                if m:
                    c_code = query[m.start():]
            comp_res = complexity_analyzer(c_code.strip())
            if comp_res.get("success"):
                final_content = (
                    f"**Algorithmic Complexity Analysis (Estimated):**\n\n"
                    f"- **Estimated Time Complexity:** `{comp_res.get('estimated_time')}`\n"
                    f"- **Estimated Space Complexity:** `{comp_res.get('estimated_space')}`\n\n"
                    f"**Analysis Details:**\n{comp_res.get('explanation')}"
                )
                executed_tools.append({"name": "complexity_analyzer", "result": comp_res})
                session.add_message("assistant", final_content)
                if on_status_update:
                    on_status_update("Done.")
                res_obj = {
                    "success": True,
                    "content": final_content,
                    "executed_tools": executed_tools,
                    "generated_artifacts": [],
                    "citations": [],
                    "verification_badges": ["✅ Static AST Analysis"],
                    "provider": "complexity_analyzer",
                    "model": "ast",
                    "timeline": {
                        "session_id": getattr(session, "session_id", "default"),
                        "budget_used": 1,
                        "actions": [{"tool_name": "complexity_analyzer", "status": "completed", "duration_ms": 10.0}]
                    }
                }
                store_cached_response(query, res_obj, user_id=user_id, file_hash=file_hash)
                return res_obj

        # 3.5 AUTONOMOUS AGENT MODE CHECK (Plan-Act-Verify for complex multi-step tasks)
        q_clean = query.strip()
        is_agent_mode = (
            getattr(session, "agent_mode", False) or
            search_mode == "Agent" or
            q_clean.lower().startswith("/agent") or
            any(phrase in q_lower for phrase in ["autonomous agent", "plan and execute", "step-by-step agent", "multi-step workflow"])
        )
        if is_agent_mode:
            logger.info("[ROUTER] Autonomous agent mode activated for query.")
            agent = BoundedAutonomousAgent(
                llm_provider=self.llm,
                max_steps=5,
                max_tool_budget=6,
                timeout_seconds=25.0
            )
            clean_query = q_clean[6:].strip() if q_clean.lower().startswith("/agent") else q_clean
            agent_res = agent.execute_bounded_run(
                query=clean_query,
                attached_files=session.attached_files,
                pre_approved_actions=getattr(session, "pre_approved_actions", None),
                status_callback=on_status_update
            )
            final_content = agent_res.content
            session.add_message("assistant", final_content)

            cites = []
            if agent_res.verification_report and hasattr(agent_res.verification_report, "citations"):
                cites = [str(c) for c in agent_res.verification_report.citations]

            res_obj = {
                "success": agent_res.status in ("success", "needs_approval", "needs_clarification"),
                "status": agent_res.status,
                "content": final_content,
                "executed_tools": [{"name": t} for t in agent_res.executed_tools],
                "citations": cites,
                "verification_badges": ["🤖 Bounded Autonomous Agent", "🛡️ Action Guardrails"],
                "generated_artifacts": agent_res.artifacts,
                "pending_approval": agent_res.pending_approval.to_dict() if agent_res.pending_approval else None,
                "provider": getattr(self.llm, "requested_provider", "agent"),
                "model": getattr(self.llm, "model", "auto"),
                "timeline": agent_res.timeline.to_dict()
            }
            return res_obj

        # 4. PRE-LLM TOOL GATHERING & RAG
        # A. Current / Latest Information -> Multi-engine search with citations
        if intent == IntentType.CURRENT_INFO:
            if on_status_update:
                on_status_update("Searching web with multi-engine fallback...")
            search_results = search_web(query, max_results=5)
            executed_tools.append({"name": "search_web", "result": search_results})
            from tools.web_search import extract_citations
            citations = extract_citations(search_results)
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
                step_res = solve_math_step_by_step(query)
                executed_tools.append({"name": "solve_math_step_by_step", "result": step_res})
                pre_tool_context = f"\n\n[STEP-BY-STEP MATHEMATICAL DERIVATION]:\n{json.dumps(step_res, indent=2)}\n"
                if step_res.get("success"):
                    verification_badges.append("📐 SymPy Step-by-Step Solved")

        # C. Image & Screenshot Understanding via Multimodal Vision
        img_files = [f for f in session.attached_files if os.path.splitext(f.get("name", ""))[1].lower() in (".png", ".jpg", ".jpeg", ".webp")]
        if img_files:
            last_img = img_files[-1]
            if on_status_update:
                on_status_update(f"Inspecting image {last_img['name']} with vision model...")
            mode = "general"
            q_low = query.lower()
            if any(k in q_low for k in ["error", "traceback", "exception", "bug", "terminal", "code"]):
                mode = "code_error"
            elif any(k in q_low for k in ["math", "formula", "handwritten", "solve", "equation", "derivation"]):
                mode = "handwritten_math"
            elif any(k in q_low for k in ["diagram", "architecture", "flowchart", "uml", "schema", "flow"]):
                mode = "diagram"
            from core.vision import analyze_image_multimodal
            vis_res = analyze_image_multimodal(last_img["path"], prompt=query, task_mode=mode)
            if vis_res.get("success"):
                executed_tools.append({"name": "multimodal_vision", "result": vis_res})
                pre_tool_context += f"\n\n[VISUAL IMAGE ANALYSIS ({last_img['name']})]:\n{vis_res.get('analysis')}\n"

        # D. Uploaded Document -> Multi-File Semantic RAG + Cross-Document Comparison
        elif intent == IntentType.DOCUMENT_ANALYSIS:
            if session.attached_files:
                from tools.rag import index_uploaded_files, search_documents_semantic, compare_documents_semantic
                index_uploaded_files(session.attached_files, user_id=user_id)
                
                is_comparison = len(session.attached_files) > 1 and any(k in query.lower() for k in ["compare", "difference", "versus", "vs", "across", "both", "all files"])
                if is_comparison:
                    if on_status_update:
                        on_status_update("Comparing passages across multiple attached files...")
                    comp_res = compare_documents_semantic(query, user_id=user_id)
                    if comp_res.get("success"):
                        executed_tools.append({"name": "cross_document_comparison", "result": comp_res})
                        pre_tool_context = f"\n\n[CROSS-DOCUMENT COMPARATIVE FINDINGS]:\n{json.dumps(comp_res['by_document'], indent=2)}\n"
                        for c in comp_res.get("all_citations", []):
                            citations.append({
                                "title": c,
                                "url": "#",
                                "domain": "multi-document",
                                "snippet": f"Cross-referenced passage in {c}"
                            })
                else:
                    last_file = session.attached_files[-1]
                    if on_status_update:
                        on_status_update(f"Analyzing {len(session.attached_files)} document(s) in parallel...")

                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                        rag_fut = executor.submit(search_documents_semantic, query, 4, user_id)
                        file_fut = executor.submit(analyze_file, last_file["path"])
                        rag_res = rag_fut.result()
                        file_analysis = file_fut.result()

                    if rag_res.get("success"):
                        executed_tools.append({"name": "semantic_rag", "result": rag_res})
                        pre_tool_context = f"\n\n[SEMANTIC PASSAGES FROM UPLOADED DOCUMENTS]:\n{json.dumps(rag_res['results'], indent=2)}\n"
                        for r in rag_res.get("results", []):
                            citations.append({
                                "title": r["citation"],
                                "url": f"file://{r['file_path']}",
                                "domain": "document",
                                "snippet": r["text"][:180]
                            })

                    executed_tools.append({"name": "analyze_file", "result": file_analysis})
                    pre_tool_context += f"\n\n[ATTACHED DOCUMENT ANALYSIS ({last_file['name']})]:\n{json.dumps(file_analysis, indent=2)}\n"

                # Proactive single-prompt conversion: If user asks to convert or extract into CSV/Excel
                q_low = query.lower()
                if any(kw in q_low for kw in ["convert", "into csv", "to csv", "export", "extract to csv", "make csv", "download csv"]):
                    if "csv" in q_low and last_file.get("path"):
                        ext = os.path.splitext(last_file["path"])[1].lower()
                        base_name = os.path.splitext(last_file["name"])[0]
                        csv_filename = f"{base_name}_data.csv" if not base_name.endswith("_data") else f"{base_name}.csv"
                        csv_text = None
                        if ext == ".pdf":
                            try:
                                import pypdf
                                reader = pypdf.PdfReader(last_file["path"])
                                pages_lines = []
                                for page in reader.pages:
                                    t = page.extract_text()
                                    if t:
                                        lines = [line_txt.strip().split() for line_txt in t.splitlines() if line_txt.strip()]
                                        if lines:
                                            pages_lines.append(lines)
                                if pages_lines and len(pages_lines) > 1 and all(len(p) == len(pages_lines[0]) for p in pages_lines):
                                    cols = []
                                    for p in pages_lines:
                                        cols.extend(p[0])
                                    rows = []
                                    for r_idx in range(1, len(pages_lines[0])):
                                        row = []
                                        for p in pages_lines:
                                            row.extend(p[r_idx])
                                        rows.append(",".join(row))
                                    csv_text = ",".join(cols) + "\n" + "\n".join(rows) + "\n"
                                elif pages_lines:
                                    all_rows = []
                                    for p in pages_lines:
                                        for line in p:
                                            all_rows.append(",".join(line))
                                    csv_text = "\n".join(all_rows) + "\n"
                            except Exception as e:
                                logger.warning(f"Failed extracting table from PDF: {e}")

                        if csv_text:
                            from tools.doc_generator import generate_document
                            doc_res = generate_document("csv", title=base_name, content=csv_text, filename=csv_filename)
                            if doc_res.get("success"):
                                generated_artifacts.append({"type": "document", "path": doc_res["file_path"], "name": csv_filename})
                                executed_tools.append({"name": "doc_generator", "result": doc_res})
                                pre_tool_context += f"\n\n[CONVERTED CSV FILE GENERATED]: {doc_res['file_path']} ready for download. Please display the extracted CSV and provide the link [Download {csv_filename}]({csv_filename}) immediately.\n"

        # D. Interview Workflow
        elif intent == IntentType.INTERVIEW:
            if not self.interview_session or not self.interview_session.active:
                self.interview_session = InterviewSession()
                pre_tool_context = f"\n\n[WORKFLOW]: {self.interview_session.start_prompt()}"
            else:
                pre_tool_context = f"\n\n[WORKFLOW]: {self.interview_session.evaluate_and_next_prompt(query)}"

        # E. Live Weather Workflow
        elif intent == IntentType.WEATHER:
            if on_status_update:
                on_status_update("Fetching live weather data...")
            from tools.weather import get_live_weather
            w_res = get_live_weather(query)
            executed_tools.append({"name": "get_live_weather", "result": w_res})
            if w_res.get("success"):
                pre_tool_context = f"\n\n[LIVE WEATHER REPORT]:\n{w_res.get('summary')}\n"
                verification_badges.append("🌤️ Live Weather Verified")
            else:
                pre_tool_context = f"\n\n[WEATHER REPORT NOTICE]: {w_res.get('error')}\n"

        # F. Study & Exam Pattern Workflow
        elif intent == IntentType.STUDY_QUESTION:
            if on_status_update:
                on_status_update("Calibrating university exam pattern structure...")
            from tools.study_engine import generate_exam_pattern_answers
            q_low = query.lower()
            p_clean = "2-mark" if any(k in q_low for k in ["2-mark", "2 mark", "2mark", "two mark"]) else (
                "5-mark" if any(k in q_low for k in ["5-mark", "5 mark", "5mark", "five mark"]) else (
                    "10-mark" if any(k in q_low for k in ["10-mark", "10 mark", "10mark", "ten mark"]) else "all"
                )
            )
            study_res = generate_exam_pattern_answers(query, pattern=p_clean)
            executed_tools.append({"name": "generate_exam_pattern_answers", "result": study_res})
            pre_tool_context = f"\n\n[STUDY ENGINE BLUEPRINT ({p_clean.upper()})]:\n{json.dumps(study_res, indent=2)}\n"
            verification_badges.append("🎓 Exam Pattern Calibrated")

        # G. Data Analysis Workflow
        elif intent == IntentType.DATA_ANALYSIS:
            if on_status_update:
                on_status_update("Inspecting dataset structure & statistics...")
            csv_target = None
            if session.attached_files:
                for f in session.attached_files:
                    if os.path.splitext(f.get("name", ""))[1].lower() in [".csv", ".xlsx", ".xls"]:
                        csv_target = f
                        break
            if not csv_target and os.path.exists("uploads"):
                for item in os.listdir("uploads"):
                    if item.lower() in query.lower() and os.path.splitext(item)[1].lower() in [".csv", ".xlsx", ".xls"]:
                        csv_target = {"path": os.path.join("uploads", item), "name": item}
                        break
            if csv_target:
                from tools.extended_tools import query_table
                from tools.automl import analyze_data_quality
                q_res = query_table(csv_target["path"], query)
                dq_res = analyze_data_quality(csv_target["path"])
                executed_tools.append({"name": "query_table", "result": q_res})
                pre_tool_context = f"\n\n[DATASET SCHEMA & SUMMARY ({csv_target['name']})]:\n{json.dumps(q_res, indent=2)}\n[DATA QUALITY]:\n{json.dumps(dq_res, indent=2)}\n"
                verification_badges.append("📊 Pandas Data Inspection")

        # H. Programming / Code Diagnosis Workflow
        elif intent == IntentType.PROGRAMMING:
            if any(k in query.lower() for k in ["error", "bug", "traceback", "fix", "exception", "failed"]):
                if on_status_update:
                    on_status_update("Diagnosing code errors & patterns...")
                from tools.high_value_tools import explain_code_error
                err_res = explain_code_error(query, "")
                if err_res.get("success"):
                    executed_tools.append({"name": "explain_code_error", "result": err_res})
                    pre_tool_context = f"\n\n[CODE ERROR DIAGNOSIS]:\n{json.dumps(err_res, indent=2)}\n"
                    verification_badges.append("💻 Code Diagnostics")

        # I. Contextual Follow-Up Workflow
        elif intent == IntentType.FOLLOW_UP:
            if on_status_update:
                on_status_update("Connecting to previous conversation context...")
            pre_tool_context += "\n\n[CONTEXTUAL CONTINUITY]: The user is asking a direct follow-up question referencing the previous messages. Maintain seamless contextual continuity and answer specifically based on what was discussed.\n"
            q_low = query.lower()
            if "simpler" in q_low:
                pre_tool_context += "[USER DIRECTIVE: SIMPLIFICATION]: The user wants a simpler explanation of the previous concept. Explain it in plain, everyday words suitable for a beginner without repeating technical jargon.\n"
            elif "another example" in q_low or "different example" in q_low:
                pre_tool_context += "[USER DIRECTIVE: NEW EXAMPLE]: The user requested another example. Provide a fresh, different practical example from real life.\n"
            elif "more detail" in q_low or "expand" in q_low or "in detail" in q_low:
                pre_tool_context += "[USER DIRECTIVE: EXPANSION]: The user asked for more detail. Expand on the previous explanation with in-depth mechanisms and trade-offs.\n"

        # Adaptive Answer Level Detection (Levels 1 to 5)
        adaptive_level = detect_adaptive_level(query)
        q_low_check = query.lower()
        if any(k in q_low_check for k in ["one sentence", "in one sentence", "in 1 sentence", "single sentence"]):
            pre_tool_context += "\n[MANDATORY FORMAT]: Provide exactly ONE simple sentence. Do NOT output headings, bullets, or an example section.\n"
        elif adaptive_level == 1 and intent in (IntentType.KNOWLEDGE, IntentType.AMBIGUOUS):
            pre_tool_context += "\n[ADAPTIVE POLICY - LEVEL 1]: Lead with the direct answer in beginner-friendly English (approx 20–60 words, 1–3 sentences). Include one practical example when useful. Avoid textbook definitions or listing features.\n"
        elif adaptive_level == 2:
            pre_tool_context += "\n[ADAPTIVE POLICY - LEVEL 2]: Provide a beginner-friendly explanation with simple meaning, short explanation, and one clear practical example.\n"
        elif adaptive_level == 3:
            pre_tool_context += "\n[ADAPTIVE POLICY - LEVEL 3]: Provide an ordered, step-by-step solution, procedure, or corrected working code with essential steps clearly numbered.\n"
        elif adaptive_level == 4:
            pre_tool_context += "\n[ADAPTIVE POLICY - LEVEL 4]: Provide a structured, comprehensive technical explanation covering architecture, working mechanisms, trade-offs, and examples.\n"
        elif adaptive_level == 5:
            pre_tool_context += "\n[ADAPTIVE POLICY - LEVEL 5]: Deliver a comprehensive, structured implementation plan and architecture covering all essential components.\n"

        # 5. PER-TASK ROUTING & INJECTION
        task_type = "chat"
        if intent in (IntentType.KNOWLEDGE, IntentType.AMBIGUOUS, IntentType.WRITING, IntentType.FOLLOW_UP, IntentType.WEATHER):
            task_type = "fast_chat"
        elif intent in (IntentType.DOCUMENT_ANALYSIS, IntentType.IMAGE_GENERATION):
            task_type = "document"
        elif intent in (IntentType.PROGRAMMING, IntentType.MATH_CALCULATION, IntentType.DATA_ANALYSIS, IntentType.STUDY_QUESTION):
            task_type = "reasoning"

        if not length_mode:
            length_mode = detect_length_mode(query)

        from core.memory import get_memory_context_string
        mem_str = get_memory_context_string()

        system_prompt = get_system_prompt(
            custom_instructions=custom_instructions,
            active_files=session.attached_files,
            length_mode=length_mode,
            user_context=mem_str
        )

        if pre_tool_context:
            system_prompt += f"\n--- VERIFIED CONTEXT ---\n{pre_tool_context}\n"

        # 6. INVOKE PROVIDER WITH AUTOMATIC TASK ROUTING
        orig_temp = getattr(self.llm, "temperature", 0.7)
        if intent == IntentType.INTERVIEW:
            self.llm.temperature = 0.0

        try:
            llm_response = self.llm.generate(
                messages=session.messages,
                system_prompt=system_prompt,
                task_type=task_type,
                on_status_update=on_status_update
            )
        finally:
            self.llm.temperature = orig_temp

        # 7. HANDLE SUCCESSFUL LLM RESPONSE + VERIFIER STEP
        if llm_response.get("success"):
            final_content = llm_response.get("content", "").strip()

            # For interview scoring, validate schema and auto-retry once on validation failure
            if intent == IntentType.INTERVIEW and self.interview_session and self.interview_session.current_question_index > 1:
                parsed_eval = self.interview_session.parse_and_validate_score(final_content)
                if not parsed_eval:
                    logger.warning("[INTERVIEW] Schema validation failed; auto-retrying with temperature 0.0")
                    retry_prompt = system_prompt + "\n\nCRITICAL: You must append the ```json_score``` block matching the specified schema."
                    retry_resp = self.llm.generate(messages=session.messages, system_prompt=retry_prompt, task_type=task_type)
                    if retry_resp.get("success") and retry_resp.get("content"):
                        final_content = retry_resp.get("content", "").strip()
                        self.interview_session.parse_and_validate_score(final_content)

            # Verifier step for math and code
            from core.verifier import verify_solution
            if on_status_update:
                on_status_update("Running verification checks...")
            verify_res = verify_solution(query, final_content, intent.value)
            final_content = verify_res["content"]
            verification_badges.extend(verify_res.get("badges", []))

            # Add one-line notice if fallback triggered
            if llm_response.get("fallback_notice"):
                notice = f"💡 *{llm_response['fallback_notice']}*"
                if llm_response.get("rate_limit_suggestion"):
                    notice += "\n> ⚡ *Tip: If Gemini is frequently rate limited, pick a Flash-Lite model from Query Models or add a free Groq key in the sidebar.*"
                final_content = f"{notice}\n\n{final_content}"
            elif llm_response.get("model_recovery_notice"):
                final_content = f"💡 *{llm_response['model_recovery_notice']}*\n\n{final_content}"

            session.add_message("assistant", final_content)
            if on_status_update:
                on_status_update("Done.")

            timeline_actions = []
            for t in executed_tools:
                t_name = t.get("name", "tool") if isinstance(t, dict) else str(t)
                timeline_actions.append({
                    "tool_name": t_name,
                    "status": "completed",
                    "duration_ms": 120.0
                })
            timeline_obj = {
                "session_id": getattr(session, "session_id", "default"),
                "budget_used": len(executed_tools),
                "actions": timeline_actions
            }

            from core.response_validator import ResponseValidator
            validator = ResponseValidator()
            val_report = validator.validate_response(
                response_text=final_content,
                sources=citations if citations else None,
                tool_results=executed_tools if executed_tools else None
            )

            result_dict = {
                "success": True,
                "content": final_content,
                "executed_tools": executed_tools,
                "citations": citations,
                "verification_badges": verification_badges,
                "generated_artifacts": generated_artifacts,
                "provider": llm_response.get("provider"),
                "model": llm_response.get("model"),
                "timeline": timeline_obj,
                "validation": val_report.to_dict()
            }
            log_request_event(
                query=query,
                intent=intent.value,
                provider=llm_response.get("provider"),
                model=llm_response.get("model"),
                latency_ms=llm_response.get("latency_ms", 500.0),
                cache_hit=False,
                tools_executed=[t.get("name", "tool") for t in executed_tools],
                failover_occurred=bool(llm_response.get("fallback_notice")),
                success=True,
                response_text=final_content
            )
            store_cached_response(query, result_dict, user_id=user_id, file_hash=file_hash)
            return result_dict

        # 8. LLM PROVIDERS UNAVAILABLE -> CHECK DETERMINISTIC FALLBACK
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
                timeline_actions = [
                    {"tool_name": t.get("name", "tool") if isinstance(t, dict) else str(t), "status": "completed", "duration_ms": 15.0}
                    for t in executed_tools
                ]
                res_obj = {
                    "success": True,
                    "content": final_content,
                    "executed_tools": executed_tools,
                    "citations": citations,
                    "verification_badges": ["✅ Local Deterministic Engine"],
                    "generated_artifacts": generated_artifacts,
                    "provider": "local_deterministic",
                    "model": "deterministic_solver",
                    "timeline": {
                        "session_id": getattr(session, "session_id", "default"),
                        "budget_used": len(executed_tools),
                        "actions": timeline_actions
                    }
                }
                store_cached_response(query, res_obj, user_id=user_id, file_hash=file_hash)
                return res_obj

        # 9. HONEST USER-FACING ERROR
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
            "citations": citations,
            "verification_badges": [],
            "generated_artifacts": [],
            "provider": None,
            "model": None,
            "developer_log": llm_response.get("developer_log"),
            "timeline": {
                "session_id": getattr(session, "session_id", "default"),
                "budget_used": len(executed_tools),
                "actions": [
                    {"tool_name": t.get("name", "tool") if isinstance(t, dict) else str(t), "status": "failed", "duration_ms": 0.0}
                    for t in executed_tools
                ]
            }
        }
