"""
All-in-One AI Assistant — Streamlit Web Application.
Implements the autonomous multi-tool problem-solving architecture.
"""

import os
import sys
import json
import uuid
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
    .tool-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        font-size: 0.8rem;
        border-radius: 12px;
        background-color: #E2E8F0;
        color: #2D3748;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
    }
    .stDownloadButton button {
        width: 100%;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "session" not in st.session_state:
    st.session_state.session = ConversationSession()

if "uploaded_files_cache" not in st.session_state:
    st.session_state.uploaded_files_cache = []

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Assistant Settings")
    
    # Provider Selection
    provider = st.selectbox(
        "AI Provider",
        options=["Groq", "Google Gemini", "OpenAI", "Ollama (Local)", "Autonomous Local Engine"],
        index=0,
        help="Select LLM provider. Groq and Gemini offer generous free tiers; Local Engine runs completely offline."
    )
    
    provider_key_map = {
        "Groq": "groq",
        "Google Gemini": "gemini",
        "OpenAI": "openai",
        "Ollama (Local)": "ollama",
        "Autonomous Local Engine": "autonomous_local"
    }
    selected_provider_code = provider_key_map[provider]

    # Model & API Key
    api_key = ""
    model_name = ""

    if selected_provider_code == "groq":
        model_name = st.selectbox("Model", ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"])
        env_groq = os.environ.get("GROQ_API_KEY", "")
        api_key = st.text_input("Groq API Key", value=env_groq, type="password", placeholder="gsk_...")
        st.caption("Get free instant API keys at [console.groq.com](https://console.groq.com)")

    elif selected_provider_code == "gemini":
        model_name = st.selectbox("Model", ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"])
        env_gemini = os.environ.get("GEMINI_API_KEY", "")
        api_key = st.text_input("Gemini API Key", value=env_gemini, type="password", placeholder="AIza...")
        st.caption("Get free keys at [aistudio.google.com](https://aistudio.google.com)")

    elif selected_provider_code == "openai":
        model_name = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "o3-mini"])
        env_openai = os.environ.get("OPENAI_API_KEY", "")
        api_key = st.text_input("OpenAI API Key", value=env_openai, type="password", placeholder="sk-proj-...")

    elif selected_provider_code == "ollama":
        model_name = st.text_input("Local Model Name", value="llama3.2")
        base_url = st.text_input("Ollama Endpoint", value="http://localhost:11434/v1")

    else:
        st.info("Operating in Autonomous Local Solver mode. Executes math, Python code, web search, files, and documents directly!")

    st.divider()

    # File Upload Section
    st.header("📂 Attach Files")
    uploaded_files = st.file_uploader(
        "Upload files for analysis (CSV, PDF, Excel, Word, Code, Images)",
        type=["csv", "xlsx", "xls", "pdf", "docx", "txt", "py", "json", "md", "png", "jpg"],
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
                st.toast(f"Attached & analyzed: {uf.name}")

    if st.session_state.session.attached_files:
        st.write("**Active Attachments:**")
        for f in st.session_state.session.attached_files:
            st.caption(f"📄 `{f['name']}` ({f['type']})")

    st.divider()

    # Clear Chat & Management
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.session.clear()
            st.rerun()
    with col_c2:
        chat_json = json.dumps(st.session_state.session.to_dict(), indent=2)
        st.download_button("💾 Export JSON", data=chat_json, file_name="conversation.json", mime="application/json", use_container_width=True)

    st.divider()
    st.markdown("""
    **Active Capabilities:**
    * 🔍 Real-time Web Search
    * 🐍 Python Execution Sandbox
    * ➗ Exact SymPy Math & Finance
    * 📊 Data Analysis & Visualizations
    * 📑 Multi-Format Document Generation
    """)

# Main UI Header
st.markdown('<div class="main-title">🤖 All-in-One AI Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Autonomous problem-solving system powered by intent recognition & adaptive tool routing</div>', unsafe_allow_html=True)

# Quick Action Suggestion Chips
chips = [
    "📈 ₹25,000 compound interest at 8% for 3 years",
    "🌐 Latest features in Python 3.14",
    "📊 Generate a sales dataset chart in Python",
    "📄 Create a PDF report for Project Status"
]
selected_chip = None
chip_cols = st.columns(len(chips))
for idx, chip in enumerate(chips):
    if chip_cols[idx].button(chip, key=f"chip_{idx}", use_container_width=True):
        selected_chip = chip

# Display Conversation History
for msg in st.session_state.session.messages:
    role = msg["role"]
    content = msg.get("content", "")
    
    if role in ["user", "assistant"]:
        with st.chat_message(role, avatar="🧑‍💻" if role == "user" else "🤖"):
            st.markdown(content)

# Handle Chat Input
user_input = st.chat_input("Ask a question, describe a problem, or request an action...")
prompt_to_process = selected_chip or user_input

if prompt_to_process:
    # Render user query
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt_to_process)

    # Initialize Provider & Orchestrator
    llm_provider = LLMProvider(
        provider=selected_provider_code,
        model=model_name if model_name else None,
        api_key=api_key if api_key else None
    )
    orchestrator = ChatbotOrchestrator(provider=llm_provider)

    with st.chat_message("assistant", avatar="🤖"):
        status_box = st.status("Executing Universal Request Pipeline...", expanded=True)
        
        def update_status(text: str):
            status_box.update(label=text)

        result = orchestrator.process_message(
            session=st.session_state.session,
            user_message=prompt_to_process,
            on_status_update=update_status
        )

        status_box.update(label="✅ Task successfully processed", state="complete", expanded=False)

        # Show executed tools summary if any
        if result.get("executed_tools"):
            with st.expander("🛠️ Actions & Tools Executed", expanded=False):
                for et in result["executed_tools"]:
                    st.write(f"**Tool:** `{et.get('name')}`")
                    st.json(et.get("result", {}))

        # Render content
        st.markdown(result.get("content", ""))

        # Render any generated artifacts (charts or documents)
        artifacts = result.get("generated_artifacts", [])
        for art in artifacts:
            if art["type"] == "image":
                st.image(art["path"], caption=art["name"], use_column_width=True)
            elif art["type"] == "document":
                with open(art["path"], "rb") as f:
                    file_bytes = f.read()
                st.download_button(
                    label=f"📥 Download Generated Document ({art['name']})",
                    data=file_bytes,
                    file_name=art["name"],
                    mime="application/octet-stream"
                )

    st.rerun()
