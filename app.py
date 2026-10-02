"""
All-in-One AI Assistant — Streamlit Web Application.
Implements intent-driven routing, tool chaining, and clean responses.
"""

import os
import sys
import json
import streamlit as st
from datetime import datetime

# Add workspace to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from core.conversation import ConversationSession
from core.llm_provider import LLMProvider
from core.orchestrator import ChatbotOrchestrator
from tools.file_analyzer import analyze_file

# Streamlit Page Config
st.set_page_config(
    page_title="All-in-One AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #718096;
        font-size: 1.0rem;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "session" not in st.session_state:
    st.session_state.session = ConversationSession()

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Model Configuration")
    
    primary_provider = st.selectbox(
        "Primary Provider",
        options=["Groq (Recommended Free Tier)", "Google Gemini", "OpenAI", "Ollama (Local)"],
        index=0,
        help="Choose the primary LLM provider. Fallbacks will automatically be attempted if configured."
    )
    
    provider_map = {
        "Groq (Recommended Free Tier)": "groq",
        "Google Gemini": "gemini",
        "OpenAI": "openai",
        "Ollama (Local)": "ollama"
    }
    selected_code = provider_map[primary_provider]

    api_key = ""
    model_name = ""

    if selected_code == "groq":
        model_name = st.selectbox("Model", ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"])
        api_key = st.text_input("Groq API Key", value=os.environ.get("GROQ_API_KEY", ""), type="password", placeholder="gsk_...")
        st.caption("Free instant keys at [console.groq.com](https://console.groq.com)")

    elif selected_code == "gemini":
        model_name = st.selectbox("Model", ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"])
        api_key = st.text_input("Gemini API Key", value=os.environ.get("GEMINI_API_KEY", ""), type="password", placeholder="AIza...")
        st.caption("Free keys at [aistudio.google.com](https://aistudio.google.com)")

    elif selected_code == "openai":
        model_name = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "o3-mini"])
        api_key = st.text_input("OpenAI API Key", value=os.environ.get("OPENAI_API_KEY", ""), type="password", placeholder="sk-proj-...")

    elif selected_code == "ollama":
        model_name = st.text_input("Local Model Name", value="llama3.2")
        base_url = st.text_input("Ollama Endpoint", value="http://localhost:11434/v1")

    # Build fallback providers list from environment or other inputs
    fallbacks = []
    if selected_code != "groq" and os.environ.get("GROQ_API_KEY"):
        fallbacks.append({"provider": "groq", "model": "llama-3.3-70b-versatile", "api_key": os.environ.get("GROQ_API_KEY")})
    if selected_code != "gemini" and os.environ.get("GEMINI_API_KEY"):
        fallbacks.append({"provider": "gemini", "model": "gemini-2.5-flash", "api_key": os.environ.get("GEMINI_API_KEY")})
    if selected_code != "openai" and os.environ.get("OPENAI_API_KEY"):
        fallbacks.append({"provider": "openai", "model": "gpt-4o-mini", "api_key": os.environ.get("OPENAI_API_KEY")})

    st.divider()

    # File Upload Section
    st.header("📂 Attach Documents")
    uploaded_files = st.file_uploader(
        "Upload files for analysis (CSV, PDF, Excel, Word, Code)",
        type=["csv", "xlsx", "xls", "pdf", "docx", "txt", "py", "json", "md"],
        accept_multiple_files=True
    )

    uploads_dir = os.path.join(current_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    if uploaded_files:
        for uf in uploaded_files:
            file_path = os.path.join(uploads_dir, uf.name)
            if file_path not in [f["path"] for f in st.session_state.session.attached_files]:
                with open(file_path, "wb") as f:
                    f.write(uf.getbuffer())
                analysis = analyze_file(file_path)
                st.session_state.session.attach_file(uf.name, file_path, uf.type, metadata=analysis)
                st.toast(f"Attached: {uf.name}")

    if st.session_state.session.attached_files:
        st.write("**Active Attachments:**")
        for f in st.session_state.session.attached_files:
            st.caption(f"📄 `{f['name']}`")

    st.divider()

    # Chat Management
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.session.clear()
            st.rerun()
    with col_c2:
        chat_json = json.dumps(st.session_state.session.to_dict(), indent=2)
        st.download_button("💾 Export JSON", data=chat_json, file_name="conversation.json", mime="application/json", use_container_width=True)

# Main UI Header
st.markdown('<div class="main-title">🤖 All-in-One AI Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Intent-driven problem-solving engine with automatic tool routing</div>', unsafe_allow_html=True)

# Quick Suggestion Chips
chips = [
    "What is physics?",
    "Compound interest on ₹25,000 at 8% for 3 years",
    "Latest features in Python 3.14",
    "Solve equation: x^2 - 5x + 6 = 0"
]
selected_chip = None
chip_cols = st.columns(len(chips))
for idx, chip in enumerate(chips):
    if chip_cols[idx].button(chip, key=f"chip_{idx}", use_container_width=True):
        selected_chip = chip

# Display History
for msg in st.session_state.session.messages:
    role = msg["role"]
    content = msg.get("content", "")
    if role in ["user", "assistant"]:
        with st.chat_message(role, avatar="🧑‍💻" if role == "user" else "🤖"):
            st.markdown(content)

# Input Box
user_input = st.chat_input("Ask a question, request a calculation, or describe a task...")
prompt_to_process = selected_chip or user_input

if prompt_to_process:
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt_to_process)

    llm_provider = LLMProvider(
        provider=selected_code,
        model=model_name if model_name else None,
        api_key=api_key if api_key else None,
        fallback_providers=fallbacks
    )
    orchestrator = ChatbotOrchestrator(provider=llm_provider)

    with st.chat_message("assistant", avatar="🤖"):
        status_box = st.status("Processing intent & routing...", expanded=False)

        def update_status(text: str):
            status_box.update(label=text)

        result = orchestrator.process_message(
            session=st.session_state.session,
            user_message=prompt_to_process,
            on_status_update=update_status
        )

        status_box.update(label="Response ready", state="complete", expanded=False)

        # Render clean answer
        st.markdown(result.get("content", ""))

        # Render artifacts if any
        artifacts = result.get("generated_artifacts", [])
        for art in artifacts:
            if art["type"] == "image":
                st.image(art["path"], caption=art["name"], use_column_width=True)
            elif art["type"] == "document":
                with open(art["path"], "rb") as f:
                    file_bytes = f.read()
                st.download_button(
                    label=f"📥 Download {art['name']}",
                    data=file_bytes,
                    file_name=art["name"],
                    mime="application/octet-stream"
                )

    st.rerun()
