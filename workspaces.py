"""
Workspaces Studio Module for SPARK-AI.
Implements specialized interactive workspaces:
- Study Mentor (Exam Patterns, 2/5/10-mark answers, NPTEL MCQs, Timed Mock Test)
- Multi-Document Chat & Comparison (PDF, PPTX, DOCX, cross-doc citations)
- Coding Lab (Live editor, Run button, stdin/stdout, test cases, Big-O complexity)
- AutoML & Visual Data Dashboard (EDA, cleaning suggestions, baseline model comparison)
- Vision & Screenshot Debugger (Code errors, handwritten math, diagrams)
"""

import os
import time
import json
import pandas as pd
import streamlit as st

from tools.rag import get_rag_index, index_uploaded_files, search_documents_semantic, compare_documents_semantic
from tools.study_engine import generate_exam_pattern_answers, generate_nptel_mcqs, parse_mock_test_submission
from tools.coding_lab import run_coding_workspace
from tools.automl import load_dataset, analyze_data_quality, compute_eda_dashboard_data, train_and_compare_models
from core.vision import analyze_image_multimodal
from core.memory import add_user_topic_weakness, add_user_topic_strength, get_user_memory
from core.learning import (
    get_due_flashcards,
    record_flashcard_review,
    create_flashcard,
    get_topic_mastery_report,
    generate_personalized_study_plan,
    list_flashcards,
    list_study_plans,
    delete_learning_record
)


def render_workspace_header(title: str, subtitle: str, workspace_key: str):
    """Renders a standard breadcrumb header with a 1-click return to General Chat."""
    col_nav1, col_nav2 = st.columns([0.76, 0.24])
    with col_nav1:
        st.markdown(f"## {title}")
        st.caption(subtitle)
    with col_nav2:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button("← Back to Chat", key=f"btn_back_from_{workspace_key}", use_container_width=True, help="Switch back to General Chat"):
            st.session_state.selected_workspace = "💬 Chat & Web Search"
            st.rerun()
    st.markdown("<hr style='margin:4px 0 16px 0;border-top:1px solid var(--border-subtle);'>", unsafe_allow_html=True)


def detect_target_workspace(query: str, attached_files: Optional[list] = None) -> Optional[str]:
    """
    Intelligently determines whether a query or attachment should automatically
    trigger a specialized workspace:
    - 🖼️ Vision & Screenshots
    - 📊 Data Science / AutoML
    - 💻 Coding Lab
    - 📖 Study Mentor
    - 📄 Document Chat
    """
    if not query and not attached_files:
        return None

    q_lower = query.strip().lower()

    # Return to General Chat
    if any(k in q_lower for k in [
        "back to chat", "return to chat", "exit workspace", "open chat",
        "switch to chat", "main chat", "general chat"
    ]):
        return "💬 Chat & Web Search"

    # 1. Image files or Screenshot analysis
    if attached_files:
        img_exts = (".png", ".jpg", ".jpeg", ".webp")
        if any(os.path.splitext(f.get("name", ""))[1].lower() in img_exts for f in attached_files):
            return "🖼️ Vision & Screenshots"

    if any(k in q_lower for k in [
        "screenshot", "image error", "inspect image", "handwritten math",
        "transcribe handwritten", "analyze diagram", "diagram analysis",
        "solve this screenshot", "fix error in image", "vision workspace",
        "open vision", "screenshot debugger", "analyze image", "image analysis"
    ]):
        return "🖼️ Vision & Screenshots"

    # 2. Data Science / AutoML (tabular files or explicit ML/cleaning tasks)
    if attached_files:
        csv_exts = (".csv", ".xlsx", ".xls")
        has_csv = any(os.path.splitext(f.get("name", ""))[1].lower() in csv_exts for f in attached_files)
        if has_csv:
            return "📊 Data Science / AutoML"

    if any(k in q_lower for k in [
        "automl", "data cleaning suggestions", "eda report", "correlation heatmap",
        "correlation matrix", "train baseline", "baseline model", "train a model",
        "predict column", "missing values report", "visual data dashboard", "data dashboard",
        "data science workspace", "open data science", "open automl", "train ml model", "clean dataset"
    ]):
        return "📊 Data Science / AutoML"

    # 3. Interactive Coding Lab
    if any(k in q_lower for k in [
        "coding lab", "code editor", "run this code", "run my code", "execute code",
        "test cases", "run in sandbox", "open coding lab", "open code editor",
        "test this function", "stdin input", "coding workspace", "open python",
        "code runner", "code sandbox", "open coding", "python sandbox"
    ]):
        return "💻 Coding Lab"

    # If user asks to run / test / execute a code block
    if "```" in query and any(k in q_lower for k in ["run", "test", "execute", "check output", "does this work", "traceback"]):
        return "💻 Coding Lab"

    # 4. Study Mentor & Exam Patterns
    if any(k in q_lower for k in [
        "study mentor", "mock exam", "mock test", "timed test", "timed mock",
        "2-mark", "2 mark", "5-mark", "5 mark", "10-mark", "10 mark",
        "nptel", "exam pattern", "practice mcq", "test me on", "quiz on",
        "study workspace", "open study mentor", "exam prep", "study mode"
    ]):
        return "📖 Study Mentor"

    # 5. Multi-Document Chat & Comparison
    if attached_files and len(attached_files) > 1:
        if any(k in q_lower for k in ["compare", "difference", "across", "versus", "vs", "both", "all documents", "document chat"]):
            return "📄 Document Chat"

    if attached_files:
        has_slides = any(os.path.splitext(f.get("name", ""))[1].lower() in (".pptx", ".ppt") for f in attached_files)
        if has_slides:
            return "📄 Document Chat"

    if any(k in q_lower for k in [
        "compare documents", "compare files", "cross-document", "across documents",
        "document chat", "read slides", "compare presentations", "open document chat",
        "multi-doc chat", "chat with pdf"
    ]):
        return "📄 Document Chat"

    # 6. Autonomous AI Agent
    if any(k in q_lower for k in [
        "autonomous agent", "agent studio", "agent mode", "plan and execute",
        "bounded agent", "plan-act-verify", "multi-step workflow"
    ]) or q_lower.startswith("/agent"):
        return "🤖 Autonomous Agent"

    return None


def render_study_mentor_workspace(user_id: str = "default"):
    """Interactive Study Mentor Workspace for Exam Patterns & NPTEL Tests."""
    render_workspace_header("📖 Study Mentor & Exam Pattern Engine", "Convert topics and notes into 2-mark, 5-mark, and 10-mark answers, NPTEL-style MCQs, or take timed mock tests.", "study")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Exam Patterns & Answers",
        "⏱️ Timed Mock Test & Tracker",
        "🗂️ Spaced Repetition Flashcards",
        "📅 Mastery & Study Plans"
    ])

    with tab1:
        c1, c2 = st.columns([3, 1])
        with c1:
            study_topic = st.text_input(
                "Enter Subject, Topic, or Paste Notes",
                placeholder="e.g. Dynamic Programming, Operating System Deadlocks, TCP/IP vs OSI",
                key="study_topic_input"
            )
        with c2:
            pattern_choice = st.selectbox(
                "Exam Pattern",
                ["All Patterns (2, 5, 10 marks)", "2-Mark (Core Definition & Formula)", "5-Mark (Concepts & Diagram Outline)", "10-Mark (Comprehensive Architectural Synthesis)", "NPTEL-Style MCQs"],
                key="pattern_choice_select"
            )

        if st.button("⚡ Generate Structured Exam Blueprint", type="primary", use_container_width=True, key="btn_gen_exam"):
            if not study_topic.strip():
                st.warning("Please enter a subject or topic.")
            else:
                with st.spinner("Generating calibrated exam structures..."):
                    if "NPTEL" in pattern_choice:
                        mcqs = generate_nptel_mcqs(study_topic, num_questions=4)
                        st.markdown(f"### 🎯 NPTEL-Style Academic MCQs: `{study_topic}`")
                        st.markdown(f"> **Standard**: {mcqs['style']} | **Difficulty**: Moderate to Advanced")
                        st.info(mcqs["instructions"])
                        # Dynamic sample mock preview
                        st.markdown("""
                        **Sample Question 1:**
                        Which of the following conditions is **NOT** strictly necessary for a deadlock to occur in a distributed operating system?
                        - A) Mutual Exclusion
                        - B) Preemption of resources *(Correct)*
                        - C) Hold and Wait
                        - D) Circular Wait
                        
                        *Explanation:* Deadlocks require **No Preemption**. If resources can be preempted, deadlock cannot persist.
                        """)
                    else:
                        pat_code = "all"
                        if "2-Mark" in pattern_choice:
                            pat_code = "2"
                        elif "5-Mark" in pattern_choice:
                            pat_code = "5"
                        elif "10-Mark" in pattern_choice:
                            pat_code = "10"

                        blueprint = generate_exam_pattern_answers(study_topic, pattern=pat_code)
                        st.success(f"Generated exam blueprints for **{study_topic}**")

                        for sec_name, sec_meta in blueprint.get("sections", {}).items():
                            with st.expander(f"📌 {sec_meta['marks']}-Mark Format: {sec_meta['format']}", expanded=True):
                                st.markdown(f"**Guideline:** {sec_meta['guideline']}")
                                st.code(sec_meta["prompt_template"], language="markdown")

    with tab2:
        st.markdown("### ⏱️ Timed Academic Mock Exam")
        mock_topic = st.text_input("Mock Test Topic", value="Data Structures & Algorithms", key="mock_test_topic")
        num_q = st.slider("Number of Questions", min_value=3, max_value=5, value=3, key="mock_q_slider")

        if "active_mock_questions" not in st.session_state:
            st.session_state.active_mock_questions = [
                {
                    "question": f"What is the average time complexity of searching in a Balanced Binary Search Tree (AVL/Red-Black)?",
                    "options": ["A) O(1)", "B) O(log N)", "C) O(N)", "D) O(N log N)"],
                    "correct_option": "B",
                    "explanation": "Balanced BSTs guarantee maximum height of O(log N), so search operations take logarithmic time.",
                    "topic": "Binary Search Trees"
                },
                {
                    "question": "Which of the following algorithm paradigms does Dijkstra's shortest path algorithm strictly follow?",
                    "options": ["A) Greedy Algorithm", "B) Dynamic Programming", "C) Divide and Conquer", "D) Backtracking"],
                    "correct_option": "A",
                    "explanation": "Dijkstra greedily picks the minimum distance unvisited vertex at every step.",
                    "topic": "Graph Theory"
                },
                {
                    "question": "In Python, which built-in data structure provides amortized O(1) time complexity for insertions and lookups?",
                    "options": ["A) List", "B) Tuple", "C) Dictionary (dict)", "D) Linked List"],
                    "correct_option": "C",
                    "explanation": "Python dictionaries are hash tables providing average O(1) lookup and insertion.",
                    "topic": "Python Internals"
                }
            ]

        with st.form("mock_exam_form"):
            user_answers = {}
            for i, q in enumerate(st.session_state.active_mock_questions[:num_q], start=1):
                st.markdown(f"**Q{i}: {q['question']}**")
                ans = st.radio(f"Select Answer for Q{i}", q["options"], key=f"mock_ans_{i}", label_visibility="collapsed")
                user_answers[str(i)] = ans[:1]
                st.markdown("<hr style='margin:8px 0;border-top:1px dashed var(--border-subtle);'>", unsafe_allow_html=True)

            submitted = st.form_submit_button("🏁 Submit Mock Test & Calculate Score", type="primary", use_container_width=True)

        if submitted:
            result = parse_mock_test_submission(user_answers, st.session_state.active_mock_questions[:num_q])
            st.markdown(f"### 🎯 Results: **{result['score']}/{result['total']} ({result['percentage']}%)**")

            if result["percentage"] >= 80:
                st.success("🎉 Excellent mastery! High accuracy across tested concepts.")
            elif result["percentage"] >= 50:
                st.info("👍 Good effort. Focus on recommended revision topics below.")
            else:
                st.warning("⚠️ Review needed. Revisit weak areas before testing again.")

            # Update long-term memory
            for wt in result.get("weak_topics", []):
                add_user_topic_weakness(user_id, wt)
            for st_topic in result.get("strong_topics", []):
                add_user_topic_strength(user_id, st_topic)

            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.markdown("#### 🔍 Question Breakdown")
                for r in result["results"]:
                    mark = "✅" if r["is_correct"] else "❌"
                    st.markdown(f"- {mark} **Q{r['question_num']}**: Your answer `{r['user_answer']}` | Correct `{r['correct_answer']}`")
                    st.caption(f"*{r['explanation']}*")
            with col_res2:
                st.markdown("#### 🧠 Memory Tracker Updated")
                st.markdown(f"- **Recorded Weak Topics**: `{', '.join(result['weak_topics']) if result['weak_topics'] else 'None'}`")
                st.markdown(f"- **Recorded Strong Topics**: `{', '.join(result['strong_topics']) if result['strong_topics'] else 'All mastered'}`")

    with tab3:
        st.markdown("### 🗂️ Spaced Repetition Flashcards (SuperMemo SM-2)")
        st.caption("Active recall engine scheduling flashcard reviews at expanding intervals.")

        due_cards = get_due_flashcards(user_id, limit=10)
        total_cards = list_flashcards(user_id, limit=100)

        c_fc1, c_fc2, c_fc3 = st.columns(3)
        with c_fc1:
            st.metric("Due for Review Now", len(due_cards))
        with c_fc2:
            st.metric("Total Flashcards", len(total_cards))
        with c_fc3:
            st.metric("Scheduling Algorithm", "SM-2")

        st.markdown("<hr style='margin:12px 0;border-top:1px solid var(--border-subtle);'>", unsafe_allow_html=True)

        if due_cards:
            curr_card = due_cards[0]
            st.markdown(f"#### Topic: `{curr_card['topic']}`")
            st.markdown(f"**Question:**\n> {curr_card['question']}")

            if "show_fc_answer" not in st.session_state:
                st.session_state.show_fc_answer = False

            col_flip, _ = st.columns([0.3, 0.7])
            with col_flip:
                if st.button("👁️ " + ("Hide Answer" if st.session_state.show_fc_answer else "Reveal Answer"), key=f"btn_flip_{curr_card['id']}"):
                    st.session_state.show_fc_answer = not st.session_state.show_fc_answer
                    st.rerun()

            if st.session_state.show_fc_answer:
                st.markdown(f"**Answer:**\n{curr_card['answer']}")
                st.markdown("**Rate your recall:**")
                r_col1, r_col2, r_col3, r_col4 = st.columns(4)
                with r_col1:
                    if st.button("🔴 Again (1)", key=f"rate_1_{curr_card['id']}", use_container_width=True):
                        record_flashcard_review(curr_card["id"], 1)
                        st.session_state.show_fc_answer = False
                        st.toast("Card scheduled for tomorrow.")
                        st.rerun()
                with r_col2:
                    if st.button("🟡 Hard (3)", key=f"rate_3_{curr_card['id']}", use_container_width=True):
                        res = record_flashcard_review(curr_card["id"], 3)
                        st.session_state.show_fc_answer = False
                        st.toast(f"Reviewed! Next review in {res.get('new_interval_days', 1)} days.")
                        st.rerun()
                with r_col3:
                    if st.button("🟢 Good (4)", key=f"rate_4_{curr_card['id']}", use_container_width=True):
                        res = record_flashcard_review(curr_card["id"], 4)
                        st.session_state.show_fc_answer = False
                        st.toast(f"Good recall! Next review in {res.get('new_interval_days', 6)} days.")
                        st.rerun()
                with r_col4:
                    if st.button("🌟 Perfect (5)", key=f"rate_5_{curr_card['id']}", use_container_width=True):
                        res = record_flashcard_review(curr_card["id"], 5)
                        st.session_state.show_fc_answer = False
                        st.toast(f"Mastered! Next review in {res.get('new_interval_days', 6)} days.")
                        st.rerun()
        else:
            st.success("🎉 You're all caught up! No flashcards currently due for review.")

        with st.expander("➕ Create New Flashcard", expanded=False):
            fc_topic = st.text_input("Topic / Concept", key="new_fc_topic")
            fc_q = st.text_area("Question / Prompt", key="new_fc_q", height=60)
            fc_a = st.text_area("Model Answer", key="new_fc_a", height=80)
            if st.button("Save Flashcard", type="primary", key="btn_save_fc"):
                if fc_topic.strip() and fc_q.strip() and fc_a.strip():
                    create_flashcard(user_id, fc_topic, fc_q, fc_a)
                    st.toast("Flashcard created successfully!")
                    st.rerun()
                else:
                    st.warning("Please fill in topic, question, and answer.")

        if total_cards:
            with st.expander(f"📚 Manage Stored Flashcards ({len(total_cards)})", expanded=False):
                for card in total_cards:
                    col_card, col_del = st.columns([0.88, 0.12])
                    with col_card:
                        st.markdown(f"**`{card['topic']}`**: {card['question'][:90]}... *(Interval: {card['interval_days']}d, Reps: {card['repetitions']})*")
                    with col_del:
                        if st.button("🗑️", key=f"del_card_{card['id']}", help="Delete flashcard"):
                            delete_learning_record(user_id, "flashcard", card["id"])
                            st.toast("Flashcard deleted.")
                            st.rerun()

    with tab4:
        st.markdown("### 📅 Longitudinal Mastery & Personalized Study Plans")
        st.caption("Tracks mastery across repeated attempts and designs custom study roadmaps targeting weak areas.")

        # Longitudinal Topic Mastery Report
        mastery = get_topic_mastery_report(user_id)
        if mastery:
            st.markdown("#### 🏆 Topic Mastery Matrix")
            m_data = []
            for m in mastery:
                m_data.append({
                    "Topic": m["topic"],
                    "Attempts": m["attempts"],
                    "Avg Score": f"{m['avg_score']}/10",
                    "Max Score": f"{m['max_score']}/10",
                    "Status": m["badge"],
                    "Last Attempt": m["last_attempt"]
                })
            st.dataframe(pd.DataFrame(m_data), use_container_width=True)
        else:
            st.info("No recorded test attempts yet. Complete mock exams to unlock longitudinal topic mastery.")

        st.markdown("<hr style='margin:12px 0;border-top:1px solid var(--border-subtle);'>", unsafe_allow_html=True)
        st.markdown("#### 🚀 Generate Custom Study Plan")

        col_sp1, col_sp2 = st.columns([2, 1])
        with col_sp1:
            plan_subj = st.text_input("Target Subject / Exam", value="Computer Science Core", key="sp_subject_input")
        with col_sp2:
            plan_days = st.slider("Target Revision Duration (Days)", min_value=3, max_value=30, value=14, key="sp_days_slider")

        if st.button("📅 Generate Structured Study Roadmap", type="primary", key="btn_gen_study_plan"):
            with st.spinner("Generating personalized syllabus targeting weak areas..."):
                p_plan = generate_personalized_study_plan(user_id, plan_subj, target_days=plan_days)
                st.success(f"Generated {plan_days}-day study plan for **{plan_subj}**!")

                if p_plan.get("weak_topics_targeted"):
                    st.info(f"Targeting recorded weak topics: `{', '.join(p_plan['weak_topics_targeted'])}`")

                schedule_df = pd.DataFrame(p_plan.get("daily_schedule", []))
                st.dataframe(schedule_df, use_container_width=True)

        # Existing saved study plans
        saved_plans = list_study_plans(user_id)
        if saved_plans:
            with st.expander(f"📁 Saved Study Plans ({len(saved_plans)})", expanded=False):
                for sp in saved_plans:
                    p_info = sp.get("plan", {})
                    col_p, col_pdel = st.columns([0.88, 0.12])
                    with col_p:
                        st.markdown(f"**`{sp['subject']}`** ({p_info.get('target_days', 14)} days, Created: {sp['created_at'][:10]})")
                    with col_pdel:
                        if st.button("🗑️", key=f"del_plan_{sp['id']}", help="Delete study plan"):
                            delete_learning_record(user_id, "study_plan", sp["id"])
                            st.toast("Study plan deleted.")
                            st.rerun()


def render_multi_document_workspace(user_id: str = "default"):
    """Multi-Document Chat, Presentation (PPTX) Reader, and Cross-Document Comparison."""
    render_workspace_header("📄 Multi-Document Chat & Comparison", "Upload multiple PDFs, PowerPoint presentations (.pptx), DOCX, or text files to compare findings and extract page/slide citations.", "doc")

    uploads = st.file_uploader(
        "Upload files for Cross-Document Analysis",
        type=["pdf", "pptx", "ppt", "docx", "txt", "md", "csv"],
        accept_multiple_files=True,
        key="multi_doc_uploader"
    )

    uploads_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    if uploads:
        saved_files = []
        for uf in uploads:
            fpath = os.path.join(uploads_dir, uf.name)
            with open(fpath, "wb") as f:
                f.write(uf.getbuffer())
            saved_files.append({"name": uf.name, "path": fpath})

        index_uploaded_files(saved_files, user_id=user_id)
        st.toast(f"Indexed {len(saved_files)} file(s) for multi-document RAG.")

    idx = get_rag_index(user_id)
    doc_count = len(set(c.file_name for c in idx.chunks))

    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("Indexed Documents", doc_count)
    with col_stats2:
        st.metric("Total Searchable Chunks", len(idx.chunks))
    with col_stats3:
        if st.button("🗑️ Clear Indexed Documents", use_container_width=True):
            idx.clear()
            st.toast("Index cleared.")
            st.rerun()

    st.markdown("<hr style='margin:12px 0;border-top:1px solid var(--border-subtle);'>", unsafe_allow_html=True)

    tab_qa, tab_comp = st.tabs(["🔍 Search & Ask Across Files", "⚖️ Cross-Document Comparison"])

    with tab_qa:
        doc_query = st.text_input("Ask a question across all uploaded documents:", placeholder="e.g. What are the key performance metrics and conclusions mentioned?", key="input_doc_query")
        if st.button("Search Across Documents", type="primary", key="btn_doc_search"):
            if not doc_query.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("Searching with hybrid RRF retrieval..."):
                    res = search_documents_semantic(doc_query, top_k=5, user_id=user_id)
                    if res.get("success"):
                        st.markdown(f"### Found {res['results_count']} Grounded Passages:")
                        for p in res.get("results", []):
                            with st.expander(f"📍 {p['citation']} (Score: {p['score']})", expanded=True):
                                st.markdown(p["text"])
                    else:
                        st.info("No matching passages found. Try uploading relevant files or broadening your query.")

    with tab_comp:
        st.markdown("#### Side-by-Side Document Contrast")
        comp_query = st.text_input("Comparative Question:", value="Compare the main methodologies and findings", key="input_comp_query")
        if st.button("Run Multi-Document Comparison", type="primary", key="btn_run_comp"):
            with st.spinner("Extracting comparative points across documents..."):
                comp_res = compare_documents_semantic(comp_query, user_id=user_id)
                if comp_res.get("success"):
                    docs = comp_res.get("documents_compared", [])
                    st.markdown(f"**Comparing {len(docs)} document(s):** `{', '.join(docs)}`")
                    c_cols = st.columns(max(1, len(docs)))
                    for col, d_name in zip(c_cols, docs):
                        with col:
                            st.markdown(f"#### 📄 {d_name}")
                            passages = comp_res["by_document"].get(d_name, [])
                            for pass_item in passages:
                                st.markdown(f"**{pass_item['citation']}:**")
                                st.markdown(f"> {pass_item['text'][:250]}...")
                                st.markdown("---")
                else:
                    st.info("Please upload 2 or more files to run side-by-side comparisons.")


def render_coding_lab_workspace():
    """Interactive Coding Lab Workspace with Sandbox Execution & Complexity Analyzer."""
    render_workspace_header("💻 Coding Lab Workspace", "Write, run, and test Python code in a safe sandbox with test cases, execution timing, and Big-O complexity estimation.", "coding")

    default_code = '''def two_sum(nums, target):
    """Finds two indices such that their values sum to target."""
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []

# Example execution
print(two_sum([2, 7, 11, 15], 9))
'''

    c_left, c_right = st.columns([1.2, 0.8])

    with c_left:
        code_input = st.text_area(
            "Python Code Editor",
            value=default_code,
            height=280,
            key="coding_lab_code_editor"
        )
        stdin_input = st.text_input("Standard Input (stdin)", placeholder="Optional inputs for input() calls", key="coding_lab_stdin")

        col_run, col_tcs = st.columns([1, 1])
        with col_run:
            run_clicked = st.button("▶️ Run Code", type="primary", use_container_width=True, key="btn_run_coding_lab")
        with col_tcs:
            run_tests = st.checkbox("Run Custom Test Cases", value=False, key="cb_run_tcs")

    test_cases = []
    if run_tests:
        with st.expander("🧪 Test Case Configurations", expanded=True):
            tc1_in = st.text_input("Test Case 1 Input", value="[2, 7, 11, 15], 9", key="tc1_in")
            tc1_exp = st.text_input("Test Case 1 Expected Output", value="[0, 1]", key="tc1_exp")
            if tc1_in:
                test_cases.append({"input": tc1_in, "expected": tc1_exp})

    with c_right:
        st.markdown("#### 🖥️ Console Output & Metrics")
        if run_clicked:
            with st.spinner("Executing in secure sandbox..."):
                res = run_coding_workspace(
                    code=code_input,
                    stdin_input=stdin_input,
                    test_cases=test_cases if run_tests else None
                )

                if res.get("success"):
                    st.success(f"Execution OK ({res['execution_time_ms']} ms)")
                    st.markdown("**Standard Output:**")
                    st.code(res.get("stdout") or "[Program produced no output]", language="text")
                else:
                    st.error(f"Execution Failed ({res['execution_time_ms']} ms)")
                    st.markdown("**Error Details:**")
                    st.code(res.get("stderr") or "Unknown error", language="text")
                    if res.get("error_explanation"):
                        st.info(f"💡 **Error Explanation:**\n{res['error_explanation']}")

                # Show Big-O Complexity
                if res.get("complexity") and res["complexity"].get("success"):
                    comp = res["complexity"]
                    st.markdown("---")
                    st.markdown(f"**⚡ Estimated Time Complexity:** `{comp.get('estimated_time')}`")
                    st.markdown(f"**💾 Estimated Space Complexity:** `{comp.get('estimated_space')}`")
                    st.caption(comp.get("explanation", "")[:140] + "...")

                # Show Test Case Results
                if res.get("test_results"):
                    st.markdown("---")
                    st.markdown("#### 🧪 Test Suite Results")
                    for tc in res["test_results"]:
                        icon = "✅ Pass" if tc["passed"] else "❌ Fail"
                        st.markdown(f"- **Test {tc['test_id']}**: {icon} ({tc['duration_ms']} ms)")
                        if not tc["passed"]:
                            st.caption(f"Expected: `{tc['expected']}` | Got: `{tc['actual']}`")


def render_automl_workspace():
    """Visual Data Dashboard, Automated Cleaning Suggestions, and Baseline Model Comparisons."""
    render_workspace_header("📊 AutoML & Visual Data Dashboard", "Upload CSV or Excel datasets for automated cleaning suggestions, interactive correlation analytics, and baseline machine learning models.", "automl")

    data_file = st.file_uploader("Upload CSV or Excel Dataset", type=["csv", "xlsx", "xls"], key="automl_uploader")

    if data_file:
        uploads_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, data_file.name)
        with open(file_path, "wb") as f:
            f.write(data_file.getbuffer())

        try:
            df = load_dataset(file_path)
            st.success(f"Loaded **{data_file.name}** ({df.shape[0]} rows, {df.shape[1]} columns)")

            tab_eda, tab_clean, tab_models = st.tabs(["📈 Exploratory Data Analysis", "🧹 Cleaning Suggestions", "🤖 Baseline Models"])

            with tab_eda:
                st.markdown("#### Dataset Preview")
                st.dataframe(df.head(6), use_container_width=True)

                eda_data = compute_eda_dashboard_data(df)
                c_m1, c_m2, c_m3 = st.columns(3)
                with c_m1:
                    st.metric("Total Rows", eda_data["shape"]["rows"])
                with c_m2:
                    st.metric("Numerical Columns", len(eda_data["numerical_columns"]))
                with c_m3:
                    st.metric("Categorical Columns", len(eda_data["categorical_columns"]))

                if eda_data.get("correlation_matrix"):
                    st.markdown("#### 🔗 Correlation Matrix (Numerical Features)")
                    corr_df = pd.DataFrame(eda_data["correlation_matrix"])
                    st.dataframe(corr_df.style.background_gradient(cmap="Blues"), use_container_width=True)

            with tab_clean:
                st.markdown("#### 🧹 Data Quality & Automated Cleaning Suggestions")
                quality = analyze_data_quality(df)
                col_q1, col_q2 = st.columns(2)
                with col_q1:
                    st.metric("Duplicate Rows", quality["duplicate_rows"])
                    st.metric("Constant Columns", len(quality["constant_columns"]))
                with col_q2:
                    st.metric("Columns with Missing Values", len(quality["missing_columns"]))

                st.markdown("##### 💡 Recommended Cleaning Actions:")
                for s in quality["cleaning_suggestions"]:
                    st.markdown(f"- {s}")

            with tab_models:
                st.markdown("#### 🤖 Train & Compare Baseline Models")
                target_col = st.selectbox("Select Target Column to Predict", df.columns.tolist(), key="automl_target_col")
                if st.button("🚀 Train & Compare Models", type="primary", key="btn_train_models"):
                    with st.spinner("Training Random Forest, Linear/Logistic, and Gradient Boosting..."):
                        train_res = train_and_compare_models(file_path, target_col)
                        if train_res.get("success"):
                            st.success(f"Best Performing Model: **{train_res['best_model']}** ({train_res['task_type']} Task)")
                            comp_df = pd.DataFrame(train_res["models_compared"])
                            st.dataframe(comp_df, use_container_width=True)

                            if train_res.get("top_features"):
                                st.markdown("##### 🏆 Top Predictive Features")
                                feat_df = pd.DataFrame(train_res["top_features"])
                                st.dataframe(feat_df, use_container_width=True)
                        else:
                            st.error(train_res.get("error", "Modeling failed."))

        except Exception as e:
            st.error(f"Error parsing dataset: {e}")
    else:
        st.info("Upload a CSV or Excel dataset to begin automated analysis.")


def render_vision_workspace():
    """Image & Screenshot Understanding for Code Errors, Handwritten Math, and Architecture Diagrams."""
    render_workspace_header("🖼️ Image & Screenshot Understanding", "Upload screenshots of code errors, handwritten math notes, or architecture diagrams for diagnostic explanations.", "vision")

    uploaded_img = st.file_uploader("Upload Screenshot or Diagram", type=["png", "jpg", "jpeg", "webp"], key="vision_uploader")

    if uploaded_img:
        uploads_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        img_path = os.path.join(uploads_dir, uploaded_img.name)
        with open(img_path, "wb") as f:
            f.write(uploaded_img.getbuffer())

        c_img, c_ctrl = st.columns([1, 1.2])
        with c_img:
            st.image(img_path, caption=uploaded_img.name, use_container_width=True)

        with c_ctrl:
            task_mode = st.radio(
                "Select Analysis Task",
                ["code_error", "handwritten_math", "diagram", "general"],
                format_func=lambda x: {
                    "code_error": "🐛 Code Error / Stack Trace",
                    "handwritten_math": "📐 Handwritten Math & Equations",
                    "diagram": "🏗️ Architecture Diagram / Flowchart",
                    "general": "🔍 General Image Inspection"
                }.get(x, x),
                key="vision_mode_select"
            )
            user_prompt = st.text_input("Specific Question or Request (optional):", value="", placeholder="e.g. Find the bug in line 42", key="vision_custom_prompt")

            if st.button("⚡ Inspect with Multimodal Vision", type="primary", use_container_width=True, key="btn_run_vision"):
                with st.spinner("Analyzing image features..."):
                    res = analyze_image_multimodal(
                        image_path=img_path,
                        prompt=user_prompt if user_prompt.strip() else "Analyze this image.",
                        task_mode=task_mode
                    )
                    if res.get("success"):
                        st.success(f"Verified via {res.get('engine')} ({res.get('model')})")
                        st.markdown(res.get("analysis", ""))
                    else:
                        st.error(res.get("error", "Vision analysis failed."))
    else:
        st.info("Upload a PNG or JPG image to diagnose code bugs or transcribe handwritten equations.")


def render_agent_workspace(user_id: str = "default"):
    """
    Autonomous AI Agent Studio:
    Provides an interactive Plan-Act-Verify execution workbench with hard step limits,
    tool budgets, approval gates, and structured timeline inspection.
    """
    render_workspace_header(
        "🤖 Autonomous AI Agent Studio",
        "Goal-oriented Plan-Act-Verify execution with bounded step limits, safety guardrails, and verification.",
        "agent_studio"
    )

    col_cfg1, col_cfg2, col_cfg3 = st.columns([2, 1, 1])
    with col_cfg1:
        st.markdown("**Agent Execution Parameters**")
        st.caption("Guardrails prevent runaway loops, infinite retries, and unauthorized operations.")
    with col_cfg2:
        max_steps = st.number_input("Max Steps", min_value=1, max_value=8, value=5, step=1, key="agent_ws_max_steps")
    with col_cfg3:
        max_budget = st.number_input("Tool Budget", min_value=1, max_value=10, value=6, step=1, key="agent_ws_max_budget")

    st.markdown("---")

    goal_prompt = st.text_area(
        "Agent Objective / Goal:",
        placeholder="e.g. Calculate compound interest on $25,000 at 7.5% for 4 years compounded quarterly, verify with SymPy, and output the step-by-step breakdown.",
        height=100,
        key="agent_ws_goal_input"
    )

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        start_agent = st.button("🚀 Launch Autonomous Agent", type="primary", use_container_width=True, key="btn_start_agent_ws")
    with col_btn2:
        if st.button("🧪 Sample Agent Goal", use_container_width=True, key="btn_sample_agent_ws"):
            st.session_state.agent_ws_goal_input = "Calculate the derivative of x^3 + 5*x^2 - 7*x + 12 and evaluate at x=3."
            st.rerun()

    if start_agent and goal_prompt.strip():
        from core.llm_provider import LLMProvider
        from core.agent import BoundedAutonomousAgent, ActionStatus
        
        status_box = st.status("Initializing autonomous Plan-Act-Verify loop...", expanded=True)
        
        def on_agent_status(msg: str):
            status_box.update(label=f"Agent: {msg}")

        llm = LLMProvider(provider="auto")
        agent = BoundedAutonomousAgent(
            llm_provider=llm,
            max_steps=int(max_steps),
            max_tool_budget=int(max_budget),
            timeout_seconds=25.0
        )

        t_start = time.perf_counter()
        result = agent.execute_bounded_run(
            query=goal_prompt.strip(),
            pre_approved_actions=st.session_state.get("pre_approved_actions", set()),
            status_callback=on_agent_status
        )
        elapsed_sec = round(time.perf_counter() - t_start, 2)
        status_box.update(label=f"Completed in {elapsed_sec}s", state="complete", expanded=False)

        st.markdown("### 📋 Agent Verified Result")
        st.markdown(result.content)

        # Timeline and executed actions breakdown
        tl = result.timeline
        with st.expander("⏱️ Activity Timeline & Tool Execution Details", expanded=True):
            st.markdown(f"**Session ID:** `{tl.session_id}` | **Budget Used:** `{tl.budget_used} / {tl.max_budget}` | **Duration:** `{tl.to_dict().get('total_duration_sec', elapsed_sec)}s`")
            for act in tl.actions:
                st.markdown(f"- **Step {act.step_index}:** `{act.tool_name}` — Status: `{act.status.value}` ({act.duration_ms} ms)")
                if act.error:
                    st.caption(f"  *Error:* {act.error}")

        if result.status == "needs_approval" and result.pending_approval:
            st.warning("⚠️ **Consequential Operation Awaiting Approval**")
            st.markdown(f"Tool `{result.pending_approval.tool_name}` requires human confirmation.")
            if st.button("✅ Approve Operation", key="btn_agent_ws_approve"):
                st.session_state.setdefault("pre_approved_actions", set()).add(result.pending_approval.action_id)
                st.rerun()
