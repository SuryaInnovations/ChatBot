"""
All-in-One AI Assistant — Streamlit Web Application.
Implements intent-driven routing, multi-provider fallback, and resilient error handling.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s")
logger = logging.getLogger("chatbot.app")

# Add workspace to path and load environment variables
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

load_dotenv(os.path.join(current_dir, ".env"), override=False)

from core.conversation import ConversationSession
from core.llm_provider import LLMProvider
from core.provider_manager import get_available_providers
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
    
    # Dynamic check of configured providers
    available_providers = get_available_providers()
    provider_names = [p["name"] for p in available_providers]
    
    primary_choice = st.selectbox(
        "Primary AI Provider",
        options=provider_names,
        index=0,
        help="Choose 'Auto' to let the system route to the best configured provider, or select a specific provider."
    )
    
    selected_cfg = next((p for p in available_providers if p["name"] == primary_choice), available_providers[0])
    selected_code = selected_cfg["code"]

    api_key = ""
    model_name = ""

    if selected_code == "groq":
        model_name = st.selectbox("Model", ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"])
        env_groq = os.environ.get("GROQ_API_KEY", "")
        api_key = st.text_input("Groq API Key", value=env_groq, type="password", placeholder="gsk_...")
        st.caption("Get free instant keys at [console.groq.com](https://console.groq.com)")

    elif selected_code == "gemini":
        model_name = st.selectbox("Model", ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"])
        env_gemini = os.environ.get("GEMINI_API_KEY", "")
        api_key = st.text_input("Gemini API Key", value=env_gemini, type="password", placeholder="AIza...")
        st.caption("Get free keys at [aistudio.google.com](https://aistudio.google.com)")

    elif selected_code == "openai":
        model_name = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "o3-mini"])
        env_openai = os.environ.get("OPENAI_API_KEY", "")
        api_key = st.text_input("OpenAI API Key", value=env_openai, type="password", placeholder="sk-proj-...")

    elif selected_code == "ollama":
        model_name = st.text_input("Local Model Name", value="llama3.2")
        base_url = st.text_input("Ollama Endpoint", value="http://localhost:11434/v1")

    # Update environment dynamically if key entered
    if api_key and api_key.strip():
        if selected_code == "groq":
            os.environ["GROQ_API_KEY"] = api_key.strip()
        elif selected_code == "gemini":
            os.environ["GEMINI_API_KEY"] = api_key.strip()
        elif selected_code == "openai":
            os.environ["OPENAI_API_KEY"] = api_key.strip()

    st.markdown("#### Provider Status:")
    for prov in available_providers:
        is_cfg = prov["configured"] or (prov["code"] == selected_code and bool(api_key.strip()))
        status_text = "🟢 Configured" if is_cfg else "⚪ Not Configured"
        st.caption(f"**{prov['name']}**: {status_text}")

    # Developer Diagnostic Expander
    with st.expander("🔍 Health Diagnostics", expanded=False):
        temp_llm = LLMProvider(provider="auto")
        diags = temp_llm.get_provider_diagnostics()
        for d in diags:
            st.write(f"**{d['name']}** (`{d['code']}`):")
            st.caption(f"Status: `{d['status']}` | Configured: `{d['configured']}`")

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
st.markdown('<div class="sub-title">Autonomous problem-solving system powered by intent recognition & resilient provider fallback</div>', unsafe_allow_html=True)

# Quick Suggestion Chips
chips = [
    "what is llm",
    "what is physics",
    "2 + 5 * 10",
    "Explain Python list comprehensions simply.",
    "Debug this Python code:\nfor i in range(5)\n    print(i)"
]
selected_chip = None
chip_cols = st.columns(len(chips))
for idx, chip in enumerate(chips):
    chip_label = chip.replace("\n", " ")[:25] + ("..." if len(chip) > 25 else "")
    if chip_cols[idx].button(chip_label, key=f"chip_{idx}", use_container_width=True):
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

    try:
        # Initialize LLMProvider and Orchestrator
        llm = LLMProvider(
            provider=selected_code,
            model=model_name if model_name else None,
            api_key=api_key if api_key else None
        )
        orchestrator = ChatbotOrchestrator(provider=llm)

        with st.chat_message("assistant", avatar="🤖"):
            status_box = st.status("Analyzing intent and routing...", expanded=False)

            def update_status(text: str):
                status_box.update(label=text)

            result = orchestrator.process_message(
                session=st.session_state.session,
                user_message=prompt_to_process,
                on_status_update=update_status
            )

            status_box.update(label="Ready", state="complete", expanded=False)

            # Render response
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

    except Exception as e:
        logger.exception("Unexpected execution error in chat handling")
        # Step 9: User-friendly error message, never expose raw Python tracebacks
        st.error("I couldn't initialize the selected AI provider. Please check the provider configuration.")

    st.rerun()
