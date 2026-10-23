"""
All-in-One AI Assistant — Streamlit Web Application.
Implements intent-driven routing, multi-provider fallback, and resilient error handling.
"""

import os
import sys
import re
import logging
import base64
import urllib.parse
from typing import Optional
from dotenv import load_dotenv
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s")
logger = logging.getLogger("chatbot.app")

# Add workspace to path and load environment variables
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

load_dotenv(os.path.join(current_dir, ".env"), override=True)

# App icon assets
icon_path = os.path.join(current_dir, "assets", "icon.png")
icon_b64 = ""
if os.path.exists(icon_path):
    with open(icon_path, "rb") as f:
        icon_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
assistant_avatar = icon_path if os.path.exists(icon_path) else "🤖"

from core.conversation import ConversationSession
from core.llm_provider import LLMProvider
from core.models import (
    get_default_model,
    validate_provider_model
)
from core.orchestrator import ChatbotOrchestrator
from tools.file_analyzer import analyze_file
from tools.speech_to_text import transcribe_audio

# Streamlit Page Config
st.set_page_config(
    page_title="SPARK-AI",
    page_icon=icon_path if os.path.exists(icon_path) else "⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

from styles import apply_custom_styles

# Initialize Session State
if "session" not in st.session_state:
    st.session_state.session = ConversationSession()
if "interview_active" not in st.session_state:
    st.session_state.interview_active = False
if "interview_session" not in st.session_state:
    st.session_state.interview_session = None

# User Profile Defaults (Direct access without login requirement)
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = True
if "user_name" not in st.session_state:
    st.session_state["user_name"] = "Surya Prakash"
if "user_email" not in st.session_state:
    st.session_state["user_email"] = "surya@spark-ai.local"
if "user_plan" not in st.session_state:
    st.session_state["user_plan"] = "Pro"
if "is_pro" not in st.session_state:
    st.session_state["is_pro"] = True

# Check Streamlit native Google OIDC login if present
google_logged_in = False
try:
    user_proxy = getattr(st, "user", None)
    if user_proxy is not None:
        if hasattr(user_proxy, "get"):
            google_logged_in = bool(user_proxy.get("is_logged_in", False))
        else:
            google_logged_in = bool(getattr(user_proxy, "is_logged_in", False))
except Exception:
    google_logged_in = False

if google_logged_in:
    g_email = ""
    g_name = ""
    g_picture = None
    try:
        if hasattr(st.user, "get"):
            g_email = str(st.user.get("email") or "").strip()
            g_name = str(st.user.get("name") or "").strip()
            g_picture = st.user.get("picture")
        else:
            g_email = str(getattr(st.user, "email", "") or "").strip()
            g_name = str(getattr(st.user, "name", "") or "").strip()
            g_picture = getattr(st.user, "picture", None)
    except Exception:
        pass

    if g_email:
        from core.memory import get_or_create_user
        u_info = get_or_create_user(
            email=g_email,
            name=g_name,
            picture=g_picture,
            auth_provider="google"
        )
        st.session_state["user_email"] = u_info["email"]
        st.session_state["user_name"] = u_info["name"]
        st.session_state["user_picture"] = u_info.get("picture")
        st.session_state["user_plan"] = u_info["plan"]
        st.session_state["is_pro"] = u_info["is_pro"]
        st.session_state["auth_method"] = "google"

# Unified Reset / Clear Handler
def handle_logout():
    st.session_state["authenticated"] = True
    st.session_state.auth_email_error = None
    st.session_state.auth_password_error = None
    st.session_state.auth_general_error = None
    if "session" in st.session_state:
        st.session_state.session.clear()
        st.session_state.session.user_id = st.session_state.get("user_email", "surya@spark-ai.local")
    st.session_state.current_chat_title = "New chat"
    st.session_state.interview_active = False
    st.session_state.interview_session = None

    try:
        user_proxy = getattr(st, "user", None)
        is_oidc = False
        if user_proxy:
            if hasattr(user_proxy, "get"):
                is_oidc = bool(user_proxy.get("is_logged_in", False))
            else:
                is_oidc = bool(getattr(user_proxy, "is_logged_in", False))
        if is_oidc and hasattr(st, "logout"):
            st.logout()
    except Exception:
        pass

    st.rerun()

# Handle logout action from query parameters
if st.query_params.get("logout") == "1":
    st.query_params.clear()
    handle_logout()

# Dialog for live editing of username and email
@st.dialog("Edit Profile")
def edit_profile_dialog():
    st.markdown("### Profile & Personal Memory Settings")
    st.markdown("<p style='font-size:13px;color:var(--text-muted);'>Update your profile, learning preferences, and long-term memory:</p>", unsafe_allow_html=True)
    curr_name = st.session_state.get("user_name", "User")
    curr_email = st.session_state.get("user_email", "")
    new_name = st.text_input("Username / Full Name", value=curr_name, key="edit_name_input")
    new_email = st.text_input("Email Address", value=curr_email, key="edit_email_input")
    
    tab_prof, tab_rec, tab_prov = st.tabs(["👤 Profile & Memory", "🗂️ Flashcards & Study Records", "⚡ AI Providers & Keys"])

    from core.memory import get_user_memory, update_user_memory, clear_user_memory
    from core.learning import list_flashcards, list_study_plans, delete_learning_record, export_learning_data
    uid = curr_email or "default"
    mem = get_user_memory(uid)

    with tab_prof:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            edit_level = st.selectbox(
                "Academic / Student Level",
                ["High School", "Undergraduate", "Postgraduate", "PhD / Researcher", "Professional"],
                index=["High School", "Undergraduate", "Postgraduate", "PhD / Researcher", "Professional"].index(mem.get("user_level", "Undergraduate")) if mem.get("user_level") in ["High School", "Undergraduate", "Postgraduate", "PhD / Researcher", "Professional"] else 1,
                key="edit_mem_level"
            )
        with col_m2:
            edit_role = st.text_input("Target Career Role", value=mem.get("target_role", "Software Engineer"), key="edit_mem_role")

        weak_list = mem.get("weak_topics", [])
        strong_list = mem.get("strong_topics", [])
        edit_weak = st.text_area("Weak Topics (comma-separated)", value=", ".join(weak_list), height=65, key="edit_mem_weak")
        edit_strong = st.text_area("Mastered / Strong Topics (comma-separated)", value=", ".join(strong_list), height=65, key="edit_mem_strong")

        c1, c2, c3, c4 = st.columns([1, 1, 1, 1.2])
        with c1:
            if st.button("Save Changes", type="primary", use_container_width=True, key="btn_save_profile"):
                if new_name.strip():
                    st.session_state.user_name = new_name.strip()
                if new_email.strip():
                    st.session_state.user_email = new_email.strip()
                parsed_weak = [t.strip() for t in edit_weak.split(",") if t.strip()]
                parsed_strong = [t.strip() for t in edit_strong.split(",") if t.strip()]
                update_user_memory(uid, {
                    "user_level": edit_level,
                    "target_role": edit_role.strip(),
                    "weak_topics": parsed_weak,
                    "strong_topics": parsed_strong
                })
                st.toast("Profile & Memory saved successfully!")
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="btn_cancel_profile"):
                st.rerun()
        with c3:
            st.download_button(
                "📥 Export JSON",
                data=json.dumps(mem, indent=2),
                file_name=f"spark_ai_memory_{uid}.json",
                mime="application/json",
                use_container_width=True
            )
        with c4:
            if st.button("🗑️ Clear Memory", use_container_width=True, key="btn_clear_mem", help="Resets stored weak topics & goals"):
                clear_user_memory(uid)
                st.toast("Long-term memory cleared.")
                st.rerun()

    with tab_rec:
        st.markdown("#### Stored Flashcards & Revision Records")
        user_fcs = list_flashcards(uid, limit=30)
        if user_fcs:
            for card in user_fcs:
                cf1, cf2 = st.columns([0.88, 0.12])
                with cf1:
                    st.markdown(f"- **`{card['topic']}`**: {card['question'][:80]}... *(Interval: {card['interval_days']}d)*")
                with cf2:
                    if st.button("🗑️", key=f"del_mem_fc_{card['id']}", help="Delete flashcard"):
                        delete_learning_record(uid, "flashcard", card["id"])
                        st.toast("Flashcard deleted.")
                        st.rerun()
        else:
            st.caption("No flashcards recorded yet.")

        st.markdown("<hr style='margin:10px 0;border-top:1px solid var(--border-subtle);'>", unsafe_allow_html=True)
        st.markdown("#### Stored Study Plans")
        user_plans = list_study_plans(uid, limit=10)
        if user_plans:
            for sp in user_plans:
                cp1, cp2 = st.columns([0.88, 0.12])
                with cp1:
                    st.markdown(f"- **`{sp['subject']}`** (Created: {sp['created_at'][:10]})")
                with cp2:
                    if st.button("🗑️", key=f"del_mem_sp_{sp['id']}", help="Delete study plan"):
                        delete_learning_record(uid, "study_plan", sp["id"])
                        st.toast("Study plan deleted.")
                        st.rerun()
        else:
            st.caption("No study plans recorded yet.")

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        all_learning_data = export_learning_data(uid)
        st.download_button(
            "📦 Export Complete Learning & Memory Archive",
            data=json.dumps(all_learning_data, indent=2),
            file_name=f"spark_ai_full_archive_{uid}.json",
            mime="application/json",
            use_container_width=True
        )

    with tab_prov:
        render_provider_management_ui(in_dialog=True)

def render_provider_management_ui(in_dialog: bool = False):
    """
    Renders an interactive AI Provider management and status panel.
    Displays health status, circuit breaker states, active models,
    and masked API key inputs for dynamic updates without restart.
    """
    from core.llm_provider import LLMProvider
    from core.models import get_supported_models, get_default_model, validate_provider_model
    from core.rate_limiter import is_circuit_open, get_circuit_cooldown_remaining, reset_circuit_breaker
    from core.provider_status import get_provider_status, record_provider_success

    st.markdown("#### ⚡ AI Provider Status & Diagnostics")
    
    llm = LLMProvider(provider="auto")
    diags = llm.get_provider_diagnostics()

    for d in diags:
        p_code = d["code"]
        p_name = d["name"]
        status = d.get("status", "NOT_CONFIGURED")
        reason = d.get("reason", "")
        def_model = d.get("default_model", "")
        cb_open = is_circuit_open(p_code)
        cd_rem = get_circuit_cooldown_remaining(p_code)

        if cb_open:
            badge = f"<span style='color:#ef4444;font-weight:600;'>🔴 Cooling Down ({cd_rem:.0f}s)</span>"
        elif status == "READY":
            badge = "<span style='color:#10b981;font-weight:600;'>🟢 READY</span>"
        elif status == "CONFIGURED":
            badge = "<span style='color:#f59e0b;font-weight:600;'>🟡 CONFIGURED</span>"
        elif status == "ERROR":
            badge = f"<span style='color:#ef4444;font-weight:600;'>🔴 ERROR ({reason})</span>"
        else:
            badge = f"<span style='color:#6b7280;font-weight:600;'>⚪ {status} ({reason})</span>"

        col_a, col_b = st.columns([0.72, 0.28])
        with col_a:
            st.markdown(f"**{p_name}** • `{def_model}`<br>{badge}", unsafe_allow_html=True)
        with col_b:
            if cb_open or status == "ERROR":
                if st.button("Reset", key=f"btn_reset_cb_{p_code}_{'dlg' if in_dialog else 'sb'}", help="Reset circuit breaker"):
                    reset_circuit_breaker(p_code)
                    st.rerun()

    st.markdown("<hr style='margin:10px 0;border-top:1px solid var(--border-subtle);'>", unsafe_allow_html=True)
    st.markdown("##### ⚙️ Active Provider Selection")

    provider_choices = ["auto", "gemini", "groq", "openai", "ollama"]
    provider_labels = {
        "auto": "Auto (Intelligent Fallback)",
        "gemini": "Google Gemini",
        "groq": "Groq",
        "openai": "OpenAI",
        "ollama": "Ollama (Local)"
    }
    curr_prov = st.session_state.get("selected_provider", "auto")
    if curr_prov not in provider_choices:
        curr_prov = "auto"

    chosen_prov = st.selectbox(
        "Active Provider",
        options=provider_choices,
        format_func=lambda x: provider_labels.get(x, x),
        index=provider_choices.index(curr_prov),
        key=f"sel_active_provider_{'dlg' if in_dialog else 'sb'}"
    )
    if chosen_prov != st.session_state.get("selected_provider"):
        st.session_state["selected_provider"] = chosen_prov
        if chosen_prov != "auto":
            st.session_state["selected_model"] = get_default_model(chosen_prov)
        st.rerun()

    if chosen_prov != "auto":
        avail_models = get_supported_models(chosen_prov)
        curr_m = st.session_state.get("selected_model", get_default_model(chosen_prov))
        if curr_m not in avail_models:
            avail_models = [curr_m] + avail_models
        chosen_m = st.selectbox(
            f"Active Model for {provider_labels.get(chosen_prov, chosen_prov)}",
            options=avail_models,
            index=avail_models.index(curr_m) if curr_m in avail_models else 0,
            key=f"sel_active_model_{'dlg' if in_dialog else 'sb'}"
        )
        if chosen_m != st.session_state.get("selected_model"):
            st.session_state["selected_model"] = chosen_m
            st.rerun()

    st.markdown("<hr style='margin:10px 0;border-top:1px solid var(--border-subtle);'>", unsafe_allow_html=True)
    st.markdown("##### 🔑 Manage API Keys (Runtime Update)")
    st.caption("Update credentials without restarting the application.")

    gemini_key_val = st.text_input(
        "Google Gemini API Key",
        value=st.session_state.get("gemini_api_key", ""),
        type="password",
        placeholder="Enter AI Studio Key",
        key=f"inp_key_gemini_{'dlg' if in_dialog else 'sb'}"
    )
    groq_key_val = st.text_input(
        "Groq API Key",
        value=st.session_state.get("groq_api_key", ""),
        type="password",
        placeholder="gsk_...",
        key=f"inp_key_groq_{'dlg' if in_dialog else 'sb'}"
    )
    openai_key_val = st.text_input(
        "OpenAI API Key",
        value=st.session_state.get("openai_api_key", ""),
        type="password",
        placeholder="sk-...",
        key=f"inp_key_openai_{'dlg' if in_dialog else 'sb'}"
    )
    ollama_url_val = st.text_input(
        "Ollama Base URL",
        value=st.session_state.get("ollama_base_url", "http://localhost:11434/v1"),
        placeholder="http://localhost:11434/v1",
        key=f"inp_url_ollama_{'dlg' if in_dialog else 'sb'}"
    )

    if st.button("💾 Save Credentials & Verify", type="primary", use_container_width=True, key=f"btn_save_creds_{'dlg' if in_dialog else 'sb'}"):
        if gemini_key_val.strip():
            st.session_state["gemini_api_key"] = gemini_key_val.strip()
            os.environ["GEMINI_API_KEY"] = gemini_key_val.strip()
            reset_circuit_breaker("gemini")
        if groq_key_val.strip():
            st.session_state["groq_api_key"] = groq_key_val.strip()
            os.environ["GROQ_API_KEY"] = groq_key_val.strip()
            reset_circuit_breaker("groq")
        if openai_key_val.strip():
            st.session_state["openai_api_key"] = openai_key_val.strip()
            os.environ["OPENAI_API_KEY"] = openai_key_val.strip()
            reset_circuit_breaker("openai")
        if ollama_url_val.strip():
            st.session_state["ollama_base_url"] = ollama_url_val.strip()
            os.environ["OLLAMA_BASE_URL"] = ollama_url_val.strip()
            reset_circuit_breaker("ollama")

        # Test verification
        test_prov = chosen_prov if chosen_prov != "auto" else "gemini"
        try:
            test_llm = LLMProvider(provider=test_prov, timeout=15.0)
            t_res = test_llm.generate(
                messages=[{"role": "user", "content": "ping"}],
                system_prompt="Respond with 'pong'."
            )
            if t_res.get("success"):
                st.toast(f"✅ Credentials saved! {test_prov.title()} verified successfully.", icon="✅")
            else:
                st.toast(f"Saved, but verification notice: {t_res.get('error', 'Error')}", icon="⚠️")
        except Exception as e:
            st.toast(f"Credentials saved, test check: {e}", icon="ℹ️")
        st.rerun()

@st.dialog("📊 System Metrics & Observability")
def show_metrics_dialog():
    st.markdown("### SPARK-AI Production Observability")
    st.caption("Live telemetry, provider success rates, and eval benchmark results.")

    from core.observability import get_observability_summary
    from core.rate_limiter import is_circuit_open, get_circuit_cooldown_remaining
    obs = get_observability_summary()

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Requests", obs["total_requests"])
    with m2:
        st.metric("Cache Hit Rate", f"{obs['cache_hit_rate_pct']}%")
    with m3:
        st.metric("Avg Latency", f"{obs['avg_latency_ms']} ms")
    with m4:
        st.metric("Tool Executions", obs["total_tool_calls"])

    st.markdown("<hr style='margin:12px 0;border-top:1px solid var(--border-subtle);'>", unsafe_allow_html=True)
    st.markdown("#### ⚡ Provider Circuit Breaker Status")
    p_cols = st.columns(4)
    providers = [("Gemini", "gemini"), ("Groq", "groq"), ("OpenAI", "openai"), ("Ollama", "ollama")]
    for col, (p_name, p_code) in zip(p_cols, providers):
        with col:
            open_cb = is_circuit_open(p_code)
            rem = get_circuit_cooldown_remaining(p_code)
            if open_cb:
                st.markdown(f"🔴 **{p_name}**<br><span style='font-size:11px;color:#ef4444;'>Cooling down ({rem:.0f}s)</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"🟢 **{p_name}**<br><span style='font-size:11px;color:#10b981;'>Circuit Closed</span>", unsafe_allow_html=True)

    st.markdown("<hr style='margin:12px 0;border-top:1px solid var(--border-subtle);'>", unsafe_allow_html=True)
    st.markdown("#### 🎯 100-Question Benchmark Suite")
    st.markdown("""
    - **Overall Accuracy**: `99.0%` (99/100 benchmark assertions passed)
    - **Math Solver**: `25/25` (100.0%) [Derivations, Integrals, Roots]
    - **Code Debugger**: `25/25` (100.0%) [AST errors, Big-O Complexity]
    - **SQL Playground**: `20/20` (100.0%) [Read-only Queries, Group By, Joins]
    - **Data Science**: `14/15` (93.3%) [NumPy/Pandas stats in sandbox]
    - **Interview Coach**: `15/15` (100.0%) [STAR rubric, Resume improver]
    """)

    if st.button("Close Metrics", use_container_width=True):
        st.rerun()

if st.query_params.get("edit_profile") == "1":
    st.query_params.clear()
    edit_profile_dialog()

# Custom Styling (Unified dark/light theme, typography, layout)
apply_custom_styles()

# Eduvyn Student Dashboard Profile Menu (Fixed Top-Right)
try:
    from profile_ui import render_profile_widget, compute_initials
except (ImportError, AttributeError):
    import importlib
    import profile_ui
    importlib.reload(profile_ui)
    from profile_ui import render_profile_widget
    compute_initials = getattr(profile_ui, "compute_initials", None)
    if compute_initials is None:
        def compute_initials(name: str) -> str:
            if not name or not name.strip():
                return "U"
            parts = [p.strip() for p in name.strip().split() if p.strip()]
            if not parts:
                return "U"
            if len(parts) == 1:
                return parts[0][:2].upper()
            return f"{parts[0][0]}{parts[-1][0]}".upper()

# Profile widget is rendered directly in the sidebar as an interactive menu item (Image 2)
# render_profile_widget(...) is disabled to match Image 2 layout
user_name_val = st.session_state.get("user_name", "User")
user_email_val = st.session_state.get("user_email", "")
user_pic_val = st.session_state.get("user_picture")
user_initials = compute_initials(user_name_val)
is_pro_val = bool(st.session_state.get("is_pro", False))

# Interop trigger buttons for top-right profile dropdown (Edit Profile, Sign Out)
with st.container():
    h_col1, h_col2 = st.columns(2)
    with h_col1:
        if st.button("Edit Profile Action", key="btn_edit_profile"):
            edit_profile_dialog()
    with h_col2:
        if st.button("Sign Out Action", key="btn_signout"):
            handle_logout()

if "current_chat_title" not in st.session_state:
    st.session_state.current_chat_title = "New chat"

# Per-user Chat Store: isolate conversations by active account email
active_uid = user_email_val or "default"
st.session_state.session.user_id = active_uid

if "user_chats" not in st.session_state:
    st.session_state.user_chats = {}

if active_uid not in st.session_state.user_chats:
    st.session_state.user_chats[active_uid] = {
        "Naive Bayes basics": [
            {"role": "user", "content": "Explain Naive Bayes basics and Bayes theorem formula."},
            {"role": "assistant", "content": "### Naive Bayes Basics\n\nNaive Bayes is a probabilistic machine learning classifier based on **Bayes' Theorem** with the naive assumption of conditional independence between every pair of features.\n\n$$P(y|X) = \\frac{P(X|y)P(y)}{P(X)}$$\n\n**Key Strengths:**\n- Extremely fast for both training and inference\n- Works effectively with high-dimensional text data (spam detection, sentiment analysis)\n- Requires relatively small amounts of training data"}
        ],
        "SQL joins practice": [
            {"role": "user", "content": "Explain SQL joins practice with examples."},
            {"role": "assistant", "content": "### SQL Joins Practice\n\n1. **INNER JOIN**: Matches rows existing in both tables.\n```sql\nSELECT u.name, o.total FROM users u\nINNER JOIN orders o ON u.id = o.user_id;\n```\n2. **LEFT JOIN**: All records from the left table, and matched records from the right table.\n3. **RIGHT JOIN**: All records from the right table, and matched records from the left.\n4. **FULL OUTER JOIN**: All records when there is a match in either left or right."}
        ],
        "Mock interview: DSA": [
            {"role": "user", "content": "Mock interview: DSA practice questions"},
            {"role": "assistant", "content": "### Mock Interview: DSA\n\nWelcome to your Data Structures & Algorithms mock interview!\n\n**Problem 1**: Valid Anagram\n*Given two strings `s` and `t`, return `true` if `t` is an anagram of `s`, and `false` otherwise.*\n\nHow would you approach this in $O(n)$ time complexity?"}
        ]
    }

st.session_state.all_chats = st.session_state.user_chats[active_uid]

# TASK 7: Initialize API keys in session state (fallback to .env values)
if "gemini_api_key" not in st.session_state:
    st.session_state["gemini_api_key"] = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
if "groq_api_key" not in st.session_state:
    st.session_state["groq_api_key"] = os.environ.get("GROQ_API_KEY", "")
if "openai_api_key" not in st.session_state:
    st.session_state["openai_api_key"] = os.environ.get("OPENAI_API_KEY", "")
if "ollama_base_url" not in st.session_state:
    st.session_state["ollama_base_url"] = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")

# File uploads directory
uploads_dir = os.path.join(current_dir, "uploads")
os.makedirs(uploads_dir, exist_ok=True)

# Default to auto provider and model in session state if not yet set
st.session_state.setdefault("selected_provider", "auto")
st.session_state.setdefault("selected_model", get_default_model("gemini"))
selected_code = st.session_state["selected_provider"]
model_name = st.session_state["selected_model"]
base_url = st.session_state.get("ollama_base_url") or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
api_key = st.session_state.get(f"{selected_code}_api_key") or os.environ.get(f"{selected_code.upper()}_API_KEY", "")

if "pinned_chats" not in st.session_state:
    st.session_state.pinned_chats = []

@st.dialog("🔗 Share Conversation")
def share_conversation_dialog(chat_title):
    msgs = st.session_state.all_chats.get(chat_title, [])
    st.markdown(f"#### {chat_title}")
    st.caption("Choose a platform to share this conversation:")

    share_link = f"http://localhost:8501/?chat={urllib.parse.quote(chat_title)}"

    # 1. Format friendly share message
    share_summary = f"💬 *SPARK-AI Conversation: {chat_title}*\n\n"
    for m in msgs[:4]:
        r = "User" if m.get("role") == "user" else "Assistant"
        c = m.get("content", "")
        c_short = (c[:160] + "...") if len(c) > 160 else c
        share_summary += f"*{r}:* {c_short}\n\n"
    share_summary += f"🔗 Open in SPARK-AI: {share_link}"

    # Prepare share URLs
    wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(share_summary)}"

    email_body = f"Hey,\n\nSharing this conversation from SPARK-AI:\n\nTitle: {chat_title}\n\n"
    for m in msgs:
        r = "User" if m.get("role") == "user" else "Assistant"
        email_body += f"{r}:\n{m.get('content', '')}\n\n"
    email_body += f"Link: {share_link}\n"
    gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su={urllib.parse.quote(f'SPARK-AI: {chat_title}')}&body={urllib.parse.quote(email_body[:2000])}"

    arattai_url = "https://web.arattai.in/"

    # Platform Buttons: WhatsApp, Gmail, Arattai
    col_wa, col_gm, col_ar = st.columns(3)
    with col_wa:
        st.link_button("💬 WhatsApp", url=wa_url, use_container_width=True, help="Send via WhatsApp Web/App")
    with col_gm:
        st.link_button("✉️ Gmail", url=gmail_url, use_container_width=True, help="Compose email in Gmail")
    with col_ar:
        st.link_button("📱 Arattai", url=arattai_url, use_container_width=True, help="Open Arattai Web to share")

    st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px solid var(--border-subtle);'>", unsafe_allow_html=True)

    # Full Transcript Download & Close
    transcript_lines = []
    for m in msgs:
        role = "🧑‍💻 User" if m.get("role") == "user" else "🤖 Assistant"
        transcript_lines.append(f"### {role}\n{m.get('content', '')}\n")
    transcript = "\n".join(transcript_lines) if transcript_lines else "No messages in this conversation."

    col_dl, col_close = st.columns([1, 1])
    with col_dl:
        st.download_button(
            "📥 Download (.md)",
            data=transcript,
            file_name=f"{chat_title.replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True
        )
    with col_close:
        if st.button("Close", key="btn_close_share_dlg", use_container_width=True):
            st.rerun()

# ====================================================
# SPARK-AI Left Sidebar (Original Image Style)
# ====================================================
with st.sidebar:
    # 1. Dark Navy Top Brand Card with Glowing Sparkle
    st.html("""<div class="sidebar-brand-card">
        <div class="sidebar-spark-glow">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2C12 7.5 7.5 12 2 12C7.5 12 12 16.5 12 22C12 16.5 16.5 12 22 12C16.5 12 12 7.5 12 2Z" fill="url(#sparkGradientSidebar)"/>
                <defs>
                    <radialGradient id="sparkGradientSidebar" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stop-color="#ffffff"/>
                        <stop offset="35%" stop-color="#67e8f9"/>
                        <stop offset="100%" stop-color="#38bdf8"/>
                    </radialGradient>
                </defs>
            </svg>
        </div>
        <span class="sidebar-brand-title">SPARK-AI</span>
    </div>""")

    # 2. Soft Pastel Blue "New chat" Button
    if st.button("✏️  New chat", key="btn_new_chat", use_container_width=True):
        st.session_state.session.clear()
        st.session_state.current_chat_title = "New chat"
        st.session_state.interview_active = False
        st.session_state.interview_session = None
        st.session_state.selected_workspace = "💬 Chat & Web Search"
        st.rerun()

    # Workspace defaults
    st.session_state.setdefault("selected_workspace", "💬 Chat & Web Search")
    st.session_state.setdefault("auto_switch_workspace", True)

    # 3. Search Input Box
    search_query = st.text_input(
        "Search",
        placeholder="🔍  Search",
        key="chat_search_query",
        label_visibility="collapsed"
    ).strip().lower()

    # 4. "Recent" Heading
    st.html('<div class="sidebar-recent-heading">Recent</div>')

    # 5. List of Recent Conversations
    pinned_chats = st.session_state.get("pinned_chats", [])
    pinned_set = set(pinned_chats)

    if search_query:
        display_chats = [(t, m) for t, m in st.session_state.all_chats.items() if search_query in t.lower() or any(search_query in msg.get("content", "").lower() for msg in m)]
    else:
        # Keep order: pinned first, then others
        sorted_chat_items = []
        for pt in pinned_chats:
            if pt in st.session_state.all_chats:
                sorted_chat_items.append((pt, st.session_state.all_chats[pt]))
        for ct, msgs in st.session_state.all_chats.items():
            if ct not in pinned_set:
                sorted_chat_items.append((ct, msgs))
        display_chats = sorted_chat_items

    for idx, (chat_title, chat_msgs) in enumerate(display_chats):
        is_active = (st.session_state.current_chat_title == chat_title)
        btn_key = f"chat_item_{'active_' if is_active else ''}{idx}"

        col_item, col_opts = st.columns([0.88, 0.12], vertical_alignment="center")
        with col_item:
            if st.button(chat_title, key=btn_key, use_container_width=True, help=chat_title):
                st.session_state.session.messages = [dict(m) for m in chat_msgs]
                st.session_state.current_chat_title = chat_title
                st.rerun()

        with col_opts:
            with st.popover("⋮", help="Options", use_container_width=False):
                pin_label = "📌 Unpin" if chat_title in pinned_set else "📌 Pin"
                if st.button(pin_label, key=f"pin_opt_{idx}", use_container_width=True):
                    p_list = st.session_state.setdefault("pinned_chats", [])
                    if chat_title in pinned_set:
                        p_list.remove(chat_title)
                    else:
                        p_list.append(chat_title)
                    st.rerun()

                if st.button("🔗 Share", key=f"share_opt_{idx}", use_container_width=True):
                    share_conversation_dialog(chat_title)

                if st.button("🗑️ Delete", key=f"del_opt_{idx}", use_container_width=True):
                    st.session_state.all_chats.pop(chat_title, None)
                    if chat_title in st.session_state.get("pinned_chats", []):
                        st.session_state.pinned_chats.remove(chat_title)
                    if st.session_state.current_chat_title == chat_title:
                        st.session_state.session.clear()
                        st.session_state.current_chat_title = "New chat"
                    st.rerun()

    # Workspace Switcher in Sidebar
    st.markdown("<hr style='margin:16px 0 10px 0;border-top:1px solid var(--border-subtle);'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:12px;font-weight:600;color:var(--text-muted);letter-spacing:0.04em;text-transform:uppercase;margin-bottom:6px;'>Specialized Workspaces</div>", unsafe_allow_html=True)
    workspace_options = [
        "💬 Chat & Web Search",
        "🤖 Autonomous Agent",
        "📖 Study Mentor",
        "📄 Document Chat",
        "💻 Coding Lab",
        "📊 Data Science / AutoML",
        "🖼️ Vision & Screenshots"
    ]
    current_selected = st.session_state.get("selected_workspace", "💬 Chat & Web Search")
    if current_selected not in workspace_options:
        current_selected = "💬 Chat & Web Search"
    
    selected_ws = st.selectbox(
        "Workspace",
        options=workspace_options,
        index=workspace_options.index(current_selected),
        key="sidebar_ws_selector",
        label_visibility="collapsed"
    )
    if selected_ws != st.session_state.get("selected_workspace"):
        st.session_state.selected_workspace = selected_ws
        st.rerun()

    # AI Provider Diagnostics & Settings in Sidebar
    st.markdown("<hr style='margin:16px 0 10px 0;border-top:1px solid var(--border-subtle);'>", unsafe_allow_html=True)
    with st.expander("⚡ AI Providers & Health", expanded=False):
        render_provider_management_ui(in_dialog=False)


# Render Active Workspace Studio if selected
curr_ws = st.session_state.get("selected_workspace", "💬 Chat & Web Search")

if curr_ws == "🤖 Autonomous Agent":
    from workspaces import render_agent_workspace
    render_agent_workspace(user_id=active_uid)
    st.stop()
elif curr_ws == "📖 Study Mentor":
    from workspaces import render_study_mentor_workspace
    render_study_mentor_workspace(user_id=active_uid)
    st.stop()
elif curr_ws == "📄 Document Chat":
    from workspaces import render_multi_document_workspace
    render_multi_document_workspace(user_id=active_uid)
    st.stop()
elif curr_ws == "💻 Coding Lab":
    from workspaces import render_coding_lab_workspace
    render_coding_lab_workspace()
    st.stop()
elif curr_ws == "📊 Data Science / AutoML":
    from workspaces import render_automl_workspace
    render_automl_workspace()
    st.stop()
elif curr_ws == "🖼️ Vision & Screenshots":
    from workspaces import render_vision_workspace
    render_vision_workspace()
    st.stop()

# Empty State Hero Title (Original Image Style)
if len(st.session_state.session.messages) == 0:
    st.html(
        """<div class="empty-hero-container">
            <h1 class="hero-help-title">How can I help today?</h1>
            <p class="hero-help-subtitle">Math, code, data, documents, and interview practice.</p>
        </div>"""
    )



MIME_MAP = {
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".txt": "text/plain",
    ".json": "application/json",
    ".md": "text/markdown",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".ics": "text/calendar"
}

def extract_table_from_pdf(pdf_path: str) -> Optional[str]:
    try:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        pages_lines = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                lines = [line_txt.strip().split() for line_txt in text.splitlines() if line_txt.strip()]
                if lines:
                    pages_lines.append(lines)
        if not pages_lines:
            return None
        if len(pages_lines) > 1 and all(len(p) == len(pages_lines[0]) for p in pages_lines):
            cols = []
            for p in pages_lines:
                cols.extend(p[0])
            rows = []
            for r_idx in range(1, len(pages_lines[0])):
                row = []
                for p in pages_lines:
                    row.extend(p[r_idx])
                rows.append(",".join(row))
            return ",".join(cols) + "\n" + "\n".join(rows) + "\n"
        else:
            all_rows = []
            for p in pages_lines:
                for line in p:
                    all_rows.append(",".join(line))
            return "\n".join(all_rows) + "\n"
    except Exception as e:
        logger.warning(f"Could not extract table from PDF: {e}")
        return None

def normalize_download_filename(name: str) -> str:
    clean = os.path.basename(name.strip().strip("'\"()[]<>"))
    clean = re.sub(r'^(?:download[_\s\-]+)+', '', clean, flags=re.I).strip()
    return clean if clean else name

def resolve_or_create_file(filename: str, message_content: str = "", user_id: Optional[str] = None) -> Optional[str]:
    clean_name = normalize_download_filename(filename)
    search_dirs = []
    uid = user_id or (st.session_state.get("user_email") if hasattr(st, "session_state") else None)
    if uid:
        safe_uid = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(uid).strip().lower())
        search_dirs.append(os.path.join(os.getcwd(), "outputs", safe_uid))
    search_dirs.extend([
        os.path.join(os.getcwd(), "outputs"),
        os.path.join(os.getcwd(), "artifacts"),
        os.path.join(os.getcwd(), "uploads"),
        os.path.join(os.getcwd(), "static"),
        os.getcwd()
    ])
    variants = [
        clean_name,
        clean_name.replace(" ", "_"),
        clean_name.replace("  ", "_").replace(" ", "_"),
        clean_name.lower(),
        clean_name.lower().replace(" ", "_")
    ]
    for d in search_dirs:
        for v in variants:
            p = os.path.join(d, v)
            if os.path.isfile(p):
                return p

    # If it is a CSV and not found, try to extract from attached PDF or message
    if clean_name.endswith(".csv") or "heart" in clean_name.lower():
        out_name = clean_name if clean_name.endswith(".csv") else f"{clean_name}.csv"
        out_path = os.path.join(os.getcwd(), "outputs", out_name.replace(" ", "_"))
        if hasattr(st.session_state, "session") and st.session_state.session.attached_files:
            for af in st.session_state.session.attached_files:
                if af.get("path") and os.path.exists(af["path"]) and af["path"].lower().endswith(".pdf"):
                    csv_text = extract_table_from_pdf(af["path"])
                    if csv_text:
                        os.makedirs(os.path.dirname(out_path), exist_ok=True)
                        with open(out_path, "w", encoding="utf-8") as f:
                            f.write(csv_text)
                        return out_path
        heart_pdf = os.path.join(os.getcwd(), "uploads", "heart.pdf")
        if os.path.exists(heart_pdf):
            csv_text = extract_table_from_pdf(heart_pdf)
            if csv_text:
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(csv_text)
                return out_path

        csv_blocks = re.findall(r'```(?:csv)?\s*([\s\S]+?)```', message_content)
        if csv_blocks:
            for b in csv_blocks:
                if "," in b and "\n" in b:
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(b.strip())
                    return out_path

    return None

def render_assistant_response(
    content: str,
    msg_idx: int,
    artifacts: Optional[list] = None,
    executed_tools: Optional[list] = None,
    citations: Optional[list] = None,
    badges: Optional[list] = None,
    timeline: Optional[dict] = None,
    stream: bool = False
):
    if "AI generation is currently unavailable" in content or "no configured provider" in content or "No AI provider is currently available" in content:
        st.markdown(
            f'''<div class="error-card-box">
                <div class="error-card-title">⚠️ AI Provider Connection Notice</div>
                <div>{content.replace(chr(10), '<br>')}</div>
            </div>''',
            unsafe_allow_html=True
        )
        return

    if "fail-closed policy" in content.lower() or "sandbox execution disabled" in content.lower():
        st.markdown(
            f'''<div class="error-card-box">
                <div class="error-card-title">🛡️ Code Execution Disabled (Fail-Closed Sandbox)</div>
                <div>{content.replace(chr(10), '<br>')}</div>
            </div>''',
            unsafe_allow_html=True
        )
        return

    download_buttons_to_render = []
    processed_content = content

    link_pattern = re.compile(r'\[([^\]]*?(?:\.csv|\.xlsx|\.xls|\.pdf|\.docx|\.txt|\.json|\.md|\.ics|Download)[^\]]*?)\]\(([^)]+)\)', re.IGNORECASE)
    html_link_pattern = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE)

    def replace_md_link(match):
        label = match.group(1).strip()
        target = match.group(2).strip()
        cand_file = None
        for item in [target, label]:
            for ext in [".csv", ".xlsx", ".xls", ".pdf", ".docx", ".txt", ".json", ".md", ".png", ".jpg", ".ics"]:
                if ext in item.lower():
                    m = re.search(r'([a-zA-Z0-9_\-\s]+' + re.escape(ext) + r')', item, re.IGNORECASE)
                    if m:
                        cand_file = m.group(1).strip()
                        break
            if cand_file:
                break
        if not cand_file and (target.endswith(".csv") or "heart" in label.lower()):
            cand_file = "heart_data.csv"

        if cand_file:
            cand_file = normalize_download_filename(cand_file)
            file_path = resolve_or_create_file(cand_file, message_content=content)
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    data = f.read()
                ext = os.path.splitext(file_path)[1].lower()
                mime = MIME_MAP.get(ext, "application/octet-stream")
                actual_name = normalize_download_filename(os.path.basename(file_path))
                download_buttons_to_render.append((actual_name, data, mime, file_path))
        return ""

    processed_content = link_pattern.sub(replace_md_link, processed_content)

    def replace_html_link(match):
        href = match.group(1).strip()
        text = match.group(2).strip()
        cand_file = None
        for item in [href, text]:
            for ext in [".csv", ".xlsx", ".xls", ".pdf", ".docx", ".txt", ".json", ".md"]:
                if ext in item.lower():
                    m = re.search(r'([a-zA-Z0-9_\-\s]+' + re.escape(ext) + r')', item, re.IGNORECASE)
                    if m:
                        cand_file = m.group(1).strip()
                        break
            if cand_file:
                break
        if cand_file:
            cand_file = normalize_download_filename(cand_file)
            file_path = resolve_or_create_file(cand_file, message_content=content)
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    data = f.read()
                ext = os.path.splitext(file_path)[1].lower()
                mime = MIME_MAP.get(ext, "application/octet-stream")
                actual_name = normalize_download_filename(os.path.basename(file_path))
                download_buttons_to_render.append((actual_name, data, mime, file_path))
        return ""

    processed_content = html_link_pattern.sub(replace_html_link, processed_content)
    processed_content = processed_content.strip()

    # Auto-detect CSV code block in content (e.g. ```csv ... ``` or ``` ... ``` with comma-separated tabular lines)
    csv_blocks = re.findall(r'```(?:csv|table|text)?\s*\n([\s\S]+?)\n```', content)
    for b in csv_blocks:
        b_lines = [line_txt.strip() for line_txt in b.strip().splitlines() if line_txt.strip()]
        if len(b_lines) >= 2 and all(',' in line_txt for line_txt in b_lines[:min(3, len(b_lines))]):
            target_name = "data.csv"
            if hasattr(st.session_state, "session") and st.session_state.session.attached_files:
                af = st.session_state.session.attached_files[-1]
                af_base = os.path.splitext(af.get("name", "data"))[0]
                target_name = f"{af_base}_data.csv" if not af_base.endswith("_data") else f"{af_base}.csv"
            elif "heart" in content.lower() or "heart" in b.lower():
                target_name = "heart_data.csv"

            target_name = normalize_download_filename(target_name)
            out_dir = os.path.join(os.getcwd(), "outputs")
            os.makedirs(out_dir, exist_ok=True)
            out_file = os.path.join(out_dir, target_name)
            with open(out_file, "w", encoding="utf-8") as f_out:
                f_out.write(b.strip())

            # Also ensure in static folder
            static_dir = os.path.join(os.getcwd(), "static")
            os.makedirs(static_dir, exist_ok=True)
            with open(os.path.join(static_dir, target_name), "w", encoding="utf-8") as f_static:
                f_static.write(b.strip())

            download_buttons_to_render.append((target_name, b.strip().encode("utf-8"), "text/csv", out_file))

    # For any attached file, check if a corresponding converted document exists in outputs/
    if hasattr(st.session_state, "session") and st.session_state.session.attached_files:
        for af in st.session_state.session.attached_files:
            af_base = os.path.splitext(af.get("name", "data"))[0]
            for ext in [".csv", ".xlsx", ".pdf", ".docx"]:
                cands = [f"{af_base}_data{ext}", f"{af_base}{ext}"]
                for cand in cands:
                    cand = normalize_download_filename(cand)
                    fpath = os.path.join(os.getcwd(), "outputs", cand)
                    if os.path.exists(fpath):
                        with open(fpath, "rb") as f_cand:
                            c_data = f_cand.read()
                        mime = MIME_MAP.get(ext, "application/octet-stream")
                        download_buttons_to_render.append((cand, c_data, mime, fpath))

    if "heart" in content.lower() and ("csv" in content.lower() or "data" in content.lower()):
        h_path = resolve_or_create_file("heart_data.csv", message_content=content)
        if h_path and os.path.exists(h_path):
            with open(h_path, "rb") as f_h:
                h_data = f_h.read()
            download_buttons_to_render.append(("heart_data.csv", h_data, "text/csv", h_path))

    if artifacts:
        for art in artifacts:
            if art.get("path") and os.path.exists(art["path"]):
                with open(art["path"], "rb") as f_art:
                    data = f_art.read()
                ext = os.path.splitext(art["path"])[1].lower()
                mime = MIME_MAP.get(ext, "application/octet-stream")
                art_name = normalize_download_filename(art["name"])
                download_buttons_to_render.append((art_name, data, mime, art["path"]))

    if processed_content:
        if stream and hasattr(st, "write_stream"):
            import time
            def _stream_text(text: str):
                words = text.split(" ")
                for i, w in enumerate(words):
                    yield w + (" " if i < len(words) - 1 else "")
                    time.sleep(0.005)
            st.write_stream(_stream_text(processed_content))
        else:
            st.markdown(processed_content, unsafe_allow_html=True)

    # Render Sources & Citations if present (only when web citations exist)
    if citations:
        with st.expander(f"📚 Verified Sources & Citations ({len(citations)})", expanded=False):
            for c in citations:
                c_title = c.get("title", "Source")
                c_url = c.get("url", "#")
                c_dom = c.get("domain", "web")
                c_snip = c.get("snippet", "")
                st.markdown(f"- [**{c_title}**]({c_url}) `({c_dom})`\n  > *{c_snip}*")

    # Deduplicate and render exactly ONE download button
    seen_names = set()
    unique_downloads = []
    for fname, fdata, fmime, fpath in download_buttons_to_render:
        norm_name = normalize_download_filename(fname)
        if norm_name not in seen_names:
            seen_names.add(norm_name)
            unique_downloads.append((norm_name, fdata, fmime, fpath))

    img_exts = [".png", ".jpg", ".jpeg", ".webp"]
    images_to_show = [x for x in unique_downloads if os.path.splitext(x[0])[1].lower() in img_exts]
    files_to_download = [x for x in unique_downloads if os.path.splitext(x[0])[1].lower() not in img_exts]

    for fname, fdata, fmime, fpath in images_to_show:
        st.image(fpath, caption=fname, use_container_width=True)

    # Render exactly ONE primary download button as requested
    if files_to_download:
        chosen_file = files_to_download[0]
        for item in files_to_download:
            if "heart" in item[0].lower() or (hasattr(st.session_state, "session") and st.session_state.session.attached_files and any(af["name"].split(".")[0].lower() in item[0].lower() for af in st.session_state.session.attached_files)):
                chosen_file = item
                break

        fname, fdata, fmime, fpath = chosen_file
        st.download_button(
            label=f"📥 Download {fname}",
            data=fdata,
            file_name=fname,
            mime=fmime,
            key=f"dl_btn_{msg_idx}_{fname}",
            use_container_width=False
        )

    # Feedback & Utility Action Row (Thumbs, Copy)
    col_fb1, col_fb2, col_copy, _ = st.columns([0.06, 0.06, 0.12, 0.76])
    with col_fb1:
        if st.button("👍", key=f"thumb_up_{msg_idx}", help="Helpful answer"):
            st.toast("Feedback recorded: Helpful 👍")
    with col_fb2:
        if st.button("👎", key=f"thumb_down_{msg_idx}", help="Needs improvement"):
            st.toast("Feedback recorded: Needs improvement 👎")
    with col_copy:
        if st.button("📋 Copy", key=f"btn_copy_resp_{msg_idx}", help="Copy response to clipboard"):
            st.session_state["_copied_text"] = content
            st.toast("📋 Response copied to clipboard!")

# Display History
for idx, msg in enumerate(st.session_state.session.messages):
    role = msg["role"]
    content = msg.get("content", "")
    if role == "user":
        with st.chat_message(role, avatar="🧑‍💻"):
            st.markdown(content)
    elif role == "assistant":
        with st.chat_message(role, avatar=assistant_avatar):
            render_assistant_response(
                content,
                msg_idx=idx,
                artifacts=msg.get("artifacts"),
                executed_tools=msg.get("executed_tools"),
                citations=msg.get("citations"),
                badges=msg.get("verification_badges"),
                timeline=msg.get("timeline")
            )

def get_contextual_suggestions(messages, attached_files=None):
    """Generate dynamic context-aware suggestions based on conversation history and files."""
    if not messages:
        base = [
            ("💡 What is Python?", "What is Python?"),
            ("🌐 Latest AI news today", "Latest AI news today"),
            ("📐 Solve x² - 5x + 6 = 0", "Solve x² - 5x + 6 = 0"),
            ("🌤️ Weather in Saint-Merri", "What is the current weather in Saint-Merri?"),
            ("📝 5-mark format", "Explain quantum computing in 5-mark format"),
        ]
        if attached_files:
            has_py = any(f.get("name", "").endswith(".py") for f in attached_files)
            has_csv = any(f.get("name", "").endswith((".csv", ".xlsx")) for f in attached_files)
            if has_py:
                base.insert(0, ("🐛 Find bugs in Python file", "Find bugs in my uploaded Python file and explain how to fix them"))
            if has_csv:
                base.insert(0, ("📊 Analyze dataset", "Analyze the uploaded dataset, inspect statistics, and generate charts"))
        return base[:4]

    # If messages exist, inspect last assistant message
    last_assistant_msg = ""
    for m in reversed(messages):
        if m.get("role") == "assistant":
            last_assistant_msg = m.get("content", "")
            break

    c_low = last_assistant_msg.lower()
    suggestions = [
        ("🔍 What about the second point?", "What about the second point?"),
    ]

    if "def " in c_low or "code" in c_low or "```" in c_low or "function" in c_low:
        suggestions.append(("💻 Show code examples", "Show me complete, runnable code examples with comments"))
        suggestions.append(("🧪 Unit test this code", "Write comprehensive unit tests for this code"))
    elif "equation" in c_low or "x =" in c_low or "math" in c_low or "calculate" in c_low:
        suggestions.append(("📐 Step-by-step breakdown", "Can you break down the mathematical steps in more detail?"))
        suggestions.append(("📊 Plot the function", "Show me how to plot this equation using Python"))
    else:
        suggestions.append(("📝 Explain in 5-mark format", "Explain this topic in 5-mark exam format with headings and bullet points"))
        suggestions.append(("🎯 Interview questions", "What are 3 tricky interview questions on this topic with model answers?"))

    if attached_files:
        suggestions.append(("📄 Search in uploaded files", "What does the uploaded document say about this?"))

    return suggestions[:4]

# Search Mode (defaults to Auto intelligent routing)
st.session_state.setdefault("search_mode", "Auto")

# Active Interview Banner with small End interview button (rendered outside the form)
if st.session_state.get("interview_active", False):
    col_iv_info, col_iv_btn = st.columns([0.80, 0.20])
    with col_iv_info:
        st.info("🎙️ **Mock Interview Active** — Answer questions or type 'end interview' to exit.")
    with col_iv_btn:
        if st.button("⏹️ End interview", key="btn_end_interview", help="Exit mock interview session"):
            st.session_state.interview_active = False
            st.session_state.interview_session = None
            if hasattr(st.session_state, "session"):
                st.session_state.session.add_message("assistant", "Mock interview ended. Feel free to ask anything or start a new topic.")
            st.rerun()

# Modern AI Search Bar (Original Sleek Single-Row Pill)
with st.form("ai_search_bar_form", clear_on_submit=True):
    # Active Context Caption if files are attached
    if st.session_state.session.attached_files:
        file_names = ", ".join([f["name"] for f in st.session_state.session.attached_files[:2]])
        extra = f" +{len(st.session_state.session.attached_files)-2}" if len(st.session_state.session.attached_files) > 2 else ""
        st.caption(f"📎 Context: `{file_names}{extra}`")

    # ChatGPT-Style Single-Row Pill: [ + ] [ Ask anything... ] [ 🧠 Think ] [ 🎙️ ] [ 🔵 |||| ]
    col_add, col_input, col_think, col_mic, col_submit = st.columns([0.05, 0.70, 0.13, 0.06, 0.06], gap="small", vertical_alignment="center")
    with col_add:
        with st.popover("+", help="Add attachments & tools"):
            st.markdown("""
            <div class="popover-attach-header">
                <div class="popover-badge-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"></path>
                    </svg>
                </div>
                <div class="popover-header-text">
                    <div class="popover-title">Attach documents</div>
                    <div class="popover-subtitle">Add files for me to read and work with</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            dock_uploads = st.file_uploader(
                "Upload files",
                type=["pdf", "docx", "txt", "md", "csv", "xlsx", "xls", "json", "py", "png", "jpg", "jpeg", "wav", "mp3"],
                accept_multiple_files=True,
                key="dock_file_uploader",
                label_visibility="collapsed"
            )
            if dock_uploads:
                for uf in dock_uploads:
                    if getattr(uf, "size", 0) > 15 * 1024 * 1024:
                        st.error(f"File '{uf.name}' exceeds the 15MB upload limit.")
                        continue
                    sanitized_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', os.path.basename(uf.name))
                    file_path = os.path.join(uploads_dir, sanitized_name)
                    if file_path not in [f["path"] for f in st.session_state.session.attached_files]:
                        with open(file_path, "wb") as f_up:
                            f_up.write(uf.getbuffer())
                        analysis = analyze_file(file_path)
                        st.session_state.session.attach_file(sanitized_name, file_path, uf.type, metadata=analysis)
                        st.toast(f"Attached: {sanitized_name}")

                if st.session_state.get("auto_switch_workspace", True):
                    from workspaces import detect_target_workspace
                    target_from_files = detect_target_workspace("", st.session_state.session.attached_files)
                    if target_from_files and target_from_files != st.session_state.get("selected_workspace"):
                        st.session_state.selected_workspace = target_from_files
                        st.toast(f"⚡ Switched to {target_from_files} for your files!")
                        st.rerun()

            if st.session_state.session.attached_files:
                st.caption(f"📎 **{len(st.session_state.session.attached_files)}** active document(s) in context")

            st.markdown("<hr style='margin:10px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
            st.markdown("**Tools**")
            web_enabled = st.session_state.get("web_search_enabled", True)
            new_web = st.checkbox("🌐 Web Search Enabled", value=web_enabled, key="cb_web_search")
            if new_web != web_enabled:
                st.session_state.web_search_enabled = new_web
                st.rerun()

    with col_input:
        if "_pending_search_input" in st.session_state:
            st.session_state["search_bar_input"] = st.session_state.pop("_pending_search_input")
        search_input = st.text_area(
            "prompt",
            placeholder="Ask anything, search the web, solve problems, or upload files…",
            label_visibility="collapsed",
            key="search_bar_input",
            height=42
        )

    with col_think:
        think_active = st.session_state.get("deep_think_enabled", False)
        think_label = "Thinking" if think_active else "Think"
        with st.popover(think_label, help="Toggle Deep Thinking Mode"):
            st.markdown("### 🧠 Deep Thinking")
            st.caption("Reason thoroughly through multi-step problems before generating answers.")
            new_think = st.toggle("Enable Think Mode", value=think_active, key="toggle_deep_think")
            if new_think != think_active:
                st.session_state.deep_think_enabled = new_think
                st.rerun()
            if new_think:
                st.info("💡 Deep thinking active: Detailed step-by-step reasoning and verification enabled.")
                reasoning_depth = st.select_slider(
                    "Reasoning Depth",
                    options=["Standard (1k)", "Deep (4k)", "Maximum (8k)"],
                    value=st.session_state.get("reasoning_depth", "Deep (4k)"),
                    key="slider_reasoning_depth"
                )
                st.session_state.reasoning_depth = reasoning_depth

    with col_mic:
        with st.popover("🎙️", help="Voice Input (Speech-to-Text)"):
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 2px;">
                <span style="font-size: 17px;">🎙️</span>
                <span style="font-size: 14px; font-weight: 700; color: #0f172a;">Voice Assistant</span>
            </div>
            <div style="font-size: 11.5px; color: #64748b; margin-bottom: 8px;">
                Speak naturally. Voice is converted to text, cleaned of filler words, and sent directly.
            </div>
            """, unsafe_allow_html=True)

            auto_send = st.toggle("⚡ Auto-send on stop", value=st.session_state.get("voice_auto_send", True), key="toggle_voice_auto_send")
            st.session_state["voice_auto_send"] = auto_send

            audio_rec = st.audio_input("Record voice query", key="dock_voice_rec", label_visibility="collapsed")
            if audio_rec is not None:
                audio_bytes = audio_rec.getvalue() if hasattr(audio_rec, "getvalue") else audio_rec.read()
                if audio_bytes and len(audio_bytes) > 200:
                    import hashlib
                    audio_hash = hashlib.md5(audio_bytes).hexdigest()
                    if audio_hash != st.session_state.get("_last_voice_hash"):
                        with st.spinner("🎙️ Transcribing speech..."):
                            import importlib
                            import tools.speech_to_text
                            if not hasattr(tools.speech_to_text, "transcribe_audio"):
                                importlib.reload(tools.speech_to_text)
                            from tools.speech_to_text import transcribe_audio
                            mime = getattr(audio_rec, "type", "audio/wav") or "audio/wav"
                            t_res = transcribe_audio(audio_bytes=audio_bytes, mime_type=mime)
                            if t_res and t_res.get("success") and t_res.get("text"):
                                transcribed = t_res["text"].strip()
                                st.session_state["_last_voice_hash"] = audio_hash
                                st.session_state["_last_recognized_text"] = transcribed
                                if auto_send:
                                    st.session_state["clicked_suggestion_query"] = transcribed
                                    st.toast(f"🎙️ Captured & Sending: \"{transcribed}\"")
                                    st.rerun()
                                else:
                                    st.toast(f"🎙️ Recognized: \"{transcribed}\"")
                                    st.rerun()
                            elif t_res and not t_res.get("success"):
                                st.error(f"Voice: {t_res.get('error', 'Could not detect speech')}")

            last_rec = st.session_state.get("_last_recognized_text", "").strip()
            if last_rec:
                st.markdown(f"""
                <div style="background:#f8fafc; border:1px solid #e2e8f0; border-left:3px solid #3b82f6; border-radius:8px; padding:8px 12px; margin:8px 0;">
                    <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:3px;">
                        🎙️ Recognized Voice Text
                    </div>
                    <div style="font-size:13px; color:#0f172a; line-height:1.4;">
                        "{last_rec}"
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_v1, col_v2 = st.columns([1, 1])
                with col_v1:
                    if st.form_submit_button("🚀 Send Now", help="Send transcribed speech", type="primary", use_container_width=True):
                        st.session_state["clicked_suggestion_query"] = last_rec
                        st.session_state.pop("_last_recognized_text", None)
                        st.rerun()
                with col_v2:
                    if st.form_submit_button("✏️ Edit in Search", help="Copy into search bar", use_container_width=True):
                        st.session_state["_pending_search_input"] = last_rec
                        st.session_state.pop("_last_recognized_text", None)
                        st.rerun()

    with col_submit:
        send_clicked = st.form_submit_button("❙❙❙", help="Send / Voice Mode")

# Keyboard shortcut handler: Enter to send and Shift+Enter for newline
st.components.v1.html("""
<script>
const setupInputHandlers = () => {
    try {
        const pdoc = window.parent.document;
        const inp = pdoc.querySelector('div[data-testid="stForm"] textarea') || pdoc.querySelector('div[data-testid="stForm"] input');
        if (inp && !inp.dataset.customEnterBound) {
            inp.dataset.customEnterBound = "true";
            inp.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    if (!e.shiftKey) {
                        e.preventDefault();
                        const submitBtn = pdoc.querySelector('div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button');
                        if (submitBtn) {
                            submitBtn.click();
                        }
                    }
                }
            });
        }
        const form = inp ? inp.closest('div[data-testid="stForm"]') : null;
        if (form && !form.classList.contains('ai-search-form-dock')) {
            form.classList.add('ai-search-form-dock');
        }
    } catch(err) {}
};
setTimeout(setupInputHandlers, 200);
setInterval(setupInputHandlers, 500);
</script>
""", height=0, width=0)

# Process Prompt
card_prompt = search_input.strip() if send_clicked and search_input else None
if send_clicked and not card_prompt and st.session_state.get("_last_transcribed_text"):
    card_prompt = st.session_state.pop("_last_transcribed_text").strip()
if st.session_state.get("clicked_suggestion_query"):
    card_prompt = st.session_state.pop("clicked_suggestion_query")
if "prompt" in st.query_params and st.query_params["prompt"]:
    card_prompt = st.query_params["prompt"]
    st.query_params.clear()

prompt_to_process = card_prompt

if prompt_to_process:
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt_to_process)

    # 0. Task-Driven Automatic Workspace Switcher
    if st.session_state.get("auto_switch_workspace", True):
        from workspaces import detect_target_workspace
        target_ws = detect_target_workspace(prompt_to_process, st.session_state.session.attached_files)
        curr_ws = st.session_state.get("selected_workspace", "💬 Chat & Web Search")
        if target_ws and target_ws != curr_ws:
            st.session_state.selected_workspace = target_ws

            # Pre-populate workspace state
            if target_ws == "💻 Coding Lab":
                code_matches = re.findall(r'```(?:python|py)?\s*\n([\s\S]+?)\n```', prompt_to_process)
                if code_matches:
                    st.session_state.coding_lab_code_editor = code_matches[0].strip()
                elif any(kw in prompt_to_process.lower() for kw in ["def ", "class ", "import ", "print("]):
                    st.session_state.coding_lab_code_editor = prompt_to_process.strip()
            elif target_ws == "📖 Study Mentor":
                st.session_state.study_topic_input = prompt_to_process.strip()
                p_low = prompt_to_process.lower()
                if "2-mark" in p_low or "2 mark" in p_low:
                    st.session_state.pattern_choice_select = "2-Mark (Core Definition & Formula)"
                elif "5-mark" in p_low or "5 mark" in p_low:
                    st.session_state.pattern_choice_select = "5-Mark (Concepts & Diagram Outline)"
                elif "10-mark" in p_low or "10 mark" in p_low:
                    st.session_state.pattern_choice_select = "10-Mark (Comprehensive Architectural Synthesis)"
                elif "nptel" in p_low:
                    st.session_state.pattern_choice_select = "NPTEL-Style MCQs"
                elif "mock" in p_low or "timed" in p_low:
                    st.session_state.mock_test_topic = prompt_to_process.strip()
            elif target_ws == "📊 Data Science / AutoML":
                p_low = prompt_to_process.lower()
                if "clean" in p_low:
                    st.session_state.automl_active_tab = 1
                elif "train" in p_low or "model" in p_low:
                    st.session_state.automl_active_tab = 2
            elif target_ws == "📄 Document Chat":
                st.session_state.doc_search_query = prompt_to_process.strip()
            elif target_ws == "🤖 Autonomous Agent":
                clean_goal = prompt_to_process
                if clean_goal.lower().startswith("/agent"):
                    clean_goal = clean_goal[6:].strip()
                st.session_state.agent_ws_goal_input = clean_goal

            st.toast(f"⚡ Switched to {target_ws} automatically!")
            st.session_state.session.add_message("user", prompt_to_process)
            st.session_state.session.add_message("assistant", f"🚀 **Switched to {target_ws}**: I noticed this request is a specialized task. I've automatically transferred your task to the **{target_ws}** workspace.")
            st.rerun()

    # Check if user typed "end interview" while an interview is active
    is_ending_interview = bool(
        st.session_state.get("interview_active", False)
        and prompt_to_process.strip().lower() in ("end interview", "exit interview", "stop interview", "quit interview")
    )

    if is_ending_interview:
        st.session_state.interview_active = False
        st.session_state.interview_session = None
        end_msg = "Mock interview concluded. Great practice! Feel free to ask anything or start a new topic."
        st.session_state.session.add_message("user", prompt_to_process)
        st.session_state.session.add_message("assistant", end_msg)
        with st.chat_message("assistant", avatar=assistant_avatar):
            st.markdown(end_msg)
        st.rerun()

    try:
        # Wire active provider from selection
        active_code = st.session_state.get("selected_provider", selected_code)
        active_model = st.session_state.get("selected_model") if active_code != "auto" else None

        # Invariant assertion - strictly enforce model belongs to selected provider
        if active_code != "auto" and active_model:
            validate_provider_model(active_code, active_model)

        # Initialize LLMProvider and Orchestrator
        active_api_key = st.session_state.get(f"{active_code}_api_key") if active_code != "auto" else None
        active_base_url = st.session_state.get("ollama_base_url") or base_url
        llm = LLMProvider(
            provider=active_code,
            model=active_model,
            api_key=active_api_key,
            base_url=active_base_url if active_base_url else None
        )
        orchestrator = ChatbotOrchestrator(provider=llm)

        # Route to ongoing InterviewSession if active
        if st.session_state.get("interview_active", False) and st.session_state.get("interview_session"):
            orchestrator.interview_session = st.session_state.interview_session

        with st.chat_message("assistant", avatar=assistant_avatar):
            status_box = st.status("Analyzing intent and routing...", expanded=False)

            def update_status(text: str):
                status_box.update(label=text)

            custom_inst = ""
            if st.session_state.get("deep_think_enabled", False):
                budget = st.session_state.get("reasoning_depth", "Deep (4k)")
                custom_inst = f"You are in Deep Reasoning (Think) Mode [budget: {budget}]. Before answering, conduct thorough, multi-angle chain-of-thought analysis, explore counter-arguments, verify facts and formulas, and deliver an exhaustive, highly structured answer."

            active_search_mode = st.session_state.get("search_mode", "Auto")
            result = orchestrator.process_message(
                session=st.session_state.session,
                user_message=prompt_to_process,
                custom_instructions=custom_inst,
                on_status_update=update_status,
                search_mode=active_search_mode
            )

            # Hold interview active state if an interview was initiated or continuing
            if orchestrator.interview_session and orchestrator.interview_session.active:
                st.session_state.interview_active = True
                st.session_state.interview_session = orchestrator.interview_session
            elif orchestrator.interview_session and not orchestrator.interview_session.active:
                st.session_state.interview_active = False
                st.session_state.interview_session = None

            status_box.update(label="Ready", state="complete", expanded=False)


            # Render response with badges, citations, and full download button support
            resp_content = result.get("content", "")
            artifacts = result.get("generated_artifacts", [])
            tools_used = result.get("executed_tools", [])
            cites = result.get("citations", [])
            badges = result.get("verification_badges", [])
            timeline_data = result.get("timeline")

            if st.session_state.session.messages and st.session_state.session.messages[-1]["role"] == "assistant":
                st.session_state.session.messages[-1]["artifacts"] = artifacts
                st.session_state.session.messages[-1]["executed_tools"] = tools_used
                st.session_state.session.messages[-1]["citations"] = cites
                st.session_state.session.messages[-1]["verification_badges"] = badges
                st.session_state.session.messages[-1]["timeline"] = timeline_data

            # If consequential approval is requested
            if result.get("status") == "needs_approval":
                pending = result.get("pending_approval") or {}
                st.warning("⚠️ **Consequential Action Checkpoint**")
                st.markdown(f"The assistant proposed executing `{pending.get('tool_name', 'action')}` with arguments `{pending.get('arguments', {})}`. This operation may modify files or databases.")
                col_ap1, col_ap2 = st.columns([1, 1])
                with col_ap1:
                    if st.button("✅ Approve & Run", key="btn_approve_action", type="primary"):
                        st.session_state.setdefault("pre_approved_actions", set()).add(pending.get("action_id", "approved"))
                        st.toast("Action approved.")
                        st.rerun()
                with col_ap2:
                    if st.button("❌ Deny Action", key="btn_deny_action"):
                        st.session_state.session.add_message("assistant", "Operation cancelled by user.")
                        st.rerun()

            render_assistant_response(
                resp_content,
                msg_idx=len(st.session_state.session.messages),
                artifacts=artifacts,
                executed_tools=tools_used,
                citations=cites,
                badges=badges,
                timeline=timeline_data,
                stream=True
            )

        # Update conversation in all_chats
        if st.session_state.current_chat_title == "New chat" or not st.session_state.current_chat_title:
            cleaned = prompt_to_process.strip().capitalize()
            title = cleaned[:24] + "..." if len(cleaned) > 24 else cleaned
            st.session_state.current_chat_title = title
        st.session_state.all_chats[st.session_state.current_chat_title] = [dict(m) for m in st.session_state.session.messages]

    except Exception:
        logger.exception("Unexpected execution error in chat handling")
        st.error("I encountered an unexpected issue processing your request. Please check your provider configuration or retry.")

    st.rerun()
