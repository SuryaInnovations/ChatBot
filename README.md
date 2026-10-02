# 🤖 All-in-One AI Assistant

An intelligent, autonomous AI problem-solving system built on the **Master System Prompt** architecture.

> **Core Objective:** Understand what the user is trying to accomplish, determine the best way to accomplish it, automatically route to the appropriate knowledge and tools, verify the result, and provide a clear, actionable response.

---

## 🏗️ Architecture & Universal Request Pipeline

The assistant implements the **Universal Request Pipeline**:

```text
USER REQUEST
     ↓
UNDERSTAND INTENT
     ↓
EXTRACT REQUIREMENTS
     ↓
CHECK AVAILABLE CONTEXT & FILES
     ↓
DETERMINE TASK TYPE
     ↓
PLAN
     ↓
SELECT MINIMUM TOOLS
     ↓
EXECUTE (Code, Math, Search, Docs)
     ↓
VERIFY RESULTS
     ↓
FORMAT RESPONSE
     ↓
DELIVER TO USER
```

### Golden Principles Followed:
1. **User Intent Over Buttons**: The user interacts through natural language ("Calculate compound interest on ₹25,000 at 8% for 3 years", "Analyze this sales CSV and plot trends", "What is the latest Python release?"). The assistant autonomously detects intent and invokes the right tools.
2. **Minimum Tool Principle**: Tools are only called when they materially improve accuracy, freshness, or computational correctness. Simple queries are answered directly without overhead.
3. **Multi-Step Tool Chaining**: Seamlessly chains file reading → data analysis → matplotlib visualization → report generation.
4. **Resilience & Multi-Provider Support**: Supports **Groq** (free ultra-fast tier), **Google Gemini** (free tier), **OpenAI**, **Ollama** (offline local), and an internal **Autonomous Rule & Tool Engine** that functions even without API keys or when quotas are exhausted.

---

## 🛠️ Integrated Capabilities & Tools

| Tool | Capability | Engine / Library |
| :--- | :--- | :--- |
| **🔍 Live Web Search** | Current information, real-time news, documentation, versions | `ddgs`, `httpx`, `BeautifulSoup4` |
| **🐍 Python Code Sandbox** | Computation, data science, algorithms, visualization | Isolated execution, `pandas`, `numpy`, `matplotlib` |
| **➗ Math & Finance Solver** | Exact algebra, calculus, derivatives, compound interest, EMI | `sympy`, financial formulas |
| **📂 File Intelligence** | Deep analysis of CSV, Excel, PDF, Word (DOCX), code & text | `pypdf`, `pdfplumber`, `python-docx`, `openpyxl` |
| **📑 Document Generator** | Exporting structured documents to PDF, DOCX, XLSX, CSV, Markdown | `reportlab`, `python-docx`, `pandas` |

---

## 🚀 How to Run

### 1. Web Application (Streamlit UI)
Launch the modern, responsive web application:

```powershell
python -m streamlit run app.py
```
* **Features:**
  * Clean dark/light chat interface
  * Live expandable status showing tool execution steps
  * File uploader for PDF, CSV, Excel, Word, and images
  * Inline rendering of Matplotlib data charts
  * Instant download buttons for generated PDF/DOCX/Excel reports
  * Provider & model switcher (Groq, Gemini, OpenAI, Ollama, Local Engine)

---

### 2. Terminal Interactive REPL (CLI)
Interact directly in your console with colored Markdown formatting and live status spinners:

```powershell
python cli.py
```

---

### 3. FastAPI REST Server
Expose REST endpoints for integrating with other applications or frontend frameworks:

```powershell
python -m uvicorn api:app --reload --port 8000
```
* **Endpoints:**
  * `POST /chat`: Send message and receive structured response + executed tool traces
  * `POST /upload`: Upload documents for the assistant to inspect
  * `GET /artifacts/{filename}`: Download generated charts and documents
  * `GET /docs`: Interactive Swagger API documentation at `http://localhost:8000/docs`

---

## 🧪 Running Automated Tests

Run the test suite verifying all tools and pipeline components:

```powershell
python -m unittest tests/test_pipeline.py
```

---

## ⚙️ Configuration (`.env`)

Copy `.env.example` to `.env` and provide any preferred API key:

```env
# Optional API Keys:
GROQ_API_KEY=gsk_your_groq_key_here
GEMINI_API_KEY=AIza_your_gemini_key_here
OPENAI_API_KEY=sk-proj-your_openai_key_here

# Local LLM (Optional):
OLLAMA_BASE_URL=http://localhost:11434/v1
```

If no API key is provided, the assistant operates in **Autonomous Local Engine** mode, executing calculations, code, web research, file parsing, and document generation directly.

---

## 📁 Project Structure

```text
chatbot/
├── core/
│   ├── prompt.py           # Full Master System Prompt + runtime context injection
│   ├── conversation.py     # Conversation session state, attachments & project context
│   ├── llm_provider.py     # Multi-provider client (OpenAI, Gemini, Groq, Ollama, Fallback)
│   └── orchestrator.py     # Universal Request Pipeline implementation
├── tools/
│   ├── registry.py         # OpenAI-standard function calling schemas and dispatcher
│   ├── web_search.py       # Live DuckDuckGo web search & webpage scraper
│   ├── code_executor.py    # Python execution sandbox with stdout/plot capture
│   ├── math_solver.py      # Exact SymPy symbolic math and finance calculator
│   ├── file_analyzer.py    # Multi-format parser (PDF, Excel, CSV, DOCX, Code)
│   └── doc_generator.py    # ReportLab PDF, python-docx Word, and Excel generator
├── tests/
│   └── test_pipeline.py    # Complete test suite
├── app.py                  # Streamlit web interface
├── cli.py                  # Terminal interactive CLI
├── api.py                  # FastAPI REST endpoints
├── requirements.txt        # Python dependencies
└── README.md               # Documentation
```
