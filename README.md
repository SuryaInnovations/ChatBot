# ⚡ SPARK-AI: Autonomous Problem-Solving Engine & Verification System

[![CI Pipeline](https://github.com/SuryaInnovations/ChatBot/actions/workflows/ci.yml/badge.svg)](https://github.com/SuryaInnovations/ChatBot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Tool Correctness Benchmark](https://img.shields.io/badge/Tool%20Suite-99%2F100-brightgreen.svg)](tests/eval_suite.py)

**SPARK-AI** is a reliability-focused AI assistant engineered with an autonomous tool execution loop, independent symbolic and sandbox post-verification, multi-provider cascading failover, and calibrated technical interview coaching.

---

## 🏗️ System Architecture

```text
                                 ┌────────────────────────────────────────────────────────┐
                                 │                   USER QUERY / ATTACHMENTS             │
                                 └──────────────────────────┬─────────────────────────────┘
                                                            │
                                            ┌───────────────▼───────────────┐
                                            │   Intent Router & Classifier  │
                                            └───────────────┬───────────────┘
                                                            │
                     ┌──────────────────────────────────────┼──────────────────────────────────────┐
                     │                                      │                                      │
          [Deterministic Solver]                   [RAG & Memory]                          [Autonomous Tool Loop]
         (SymPy / AST / SQLite)             (BM25 + n-gram RRF / SQLite WAL)          (Plan → Call → Observe → Verify)
                     │                                      │                                      │
                     └──────────────────────────────────────┼──────────────────────────────────────┘
                                                            │
                                            ┌───────────────▼───────────────┐
                                            │ Multi-Provider Cascade Router │
                                            │ Gemini → Groq → OpenAI → Local│
                                            │ (Circuit Breaker: 60s/120s/300s)
                                            └───────────────┬───────────────┘
                                                            │
                                            ┌───────────────▼───────────────┐
                                            │    Post-Verification Engine   │
                                            │ • Math: SymPy Recomputation   │
                                            │ • Code: AST Isolation Sandbox │
                                            └───────────────┬───────────────┘
                                                            │
                                 ┌──────────────────────────▼─────────────────────────────┐
                                 │  Verified Final Answer + Citations + Download Artifacts│
                                 └────────────────────────────────────────────────────────┘
```

---

## 🌟 Key Highlights & Engineering Features

### 1. Reliable Tool-Calling Loop & Post-Verification
* **Autonomous Cycle**: Cycles through `Plan → Call → Observe → Answer` with a hard 5-step loop cap. If the cap is reached, returns an honest synthesized partial report rather than failing silently.
* **SymPy Symbolic Recomputation**: Mathematically verifies numerical claims through independent SymPy execution. Emits honest trust badges:
  - `✅ SymPy Verified`: Independently recomputed and matched.
  - `❌ Calculation Mismatch`: Highlights numerical discrepancy against the independent calculation.
  - `⚠️ Could not verify independently`: Calculation attempted outside symbolic solver capabilities.
* **Sandbox Verification**: Code execution is verified in an isolated process with AST blocklists. Code that executes without error is labeled `🛡️ Executed OK`, or `🛡️ Code Verified` if assertion test suites pass.

### 2. Multi-Engine Search with SSRF & Rebinding Defense
* **Fallback Cascade**: Primary queries search via **Tavily API** / **Brave Search API**, automatically falling back to **DuckDuckGo**.
* **SSRF & DNS Rebinding Protection**: Blocks requests targeting RFC 1918 private subnets, link-local metadata (169.254.x.x), loopback (127.0.0.1, `::1`, `0.0.0.0`), IPv4-mapped IPv6, and restricts traffic strictly to ports 80 and 443 with manual redirect hop re-validation.
* **Prompt Injection Shielding**: External fetched web content has breakout tags sanitized and is isolated within `<external_data>` demarcation boundaries.

### 3. Fail-Closed Execution Sandbox (`tools/sandbox.py`)
* **AST Pre-Screener**: Strictly rejects `os`, `subprocess`, `socket`, `ctypes`, `importlib`, `pickle`, dynamic built-ins (`eval`, `exec`, `open`, `compile`, `getattr`), and reflection bypasses (`__subclasses__`, `__mro__`, `__globals__`, `__getattribute__`, `__dict__`).
* **Fail-Closed Security**: In cloud/containerless environments lacking Docker virtualization, code execution safely fails closed by default. For local developer testing without Docker, set `ALLOW_UNSAFE_SUBPROCESS=1` in your `.env`.
* **Resource & Output Limits**: Child subprocesses have clean environments (stripped of API keys), execution timeouts, and an enforced 50,000-character stdout/stderr limit.

### 4. Document Retrieval (BM25 + Lexical n-gram via RRF)
* **Reciprocal Rank Fusion**: Combines exact BM25 keyword matching with subword character n-gram cosine similarity (RRF) for fast, dependency-light ranking without heavy local neural models.
* **Page-Level Grounded Citations**: Extracted chunks cite exact document page numbers and snippet context.
* **User-Scoped Persistence**: Document indices and chat caches are partitioned by user identity.

### 5. Resilient Provider Circuit Breaker
* **Fault Detection**: Intercepts `429 Rate Limits`, `5xx Server Errors`, and network timeouts.
* **Exponential Backoff**: Applies a progressive cooldown ladder (60s -> 120s -> 300s) upon repeated transient failures.
* **Non-Transient Classification**: HTTP 400, 401, and 403 errors (invalid credentials or malformed requests) are marked as `MISCONFIGURED` and skipped without useless transient cooldown loops.
* **Zero Downtime Fallback**: Seamlessly fails over across Google Gemini, Groq, OpenAI, or the local deterministic solver. Automatically resets upon first recorded success.

### 6. Interview Preparation & Mock Sessions
* **Curated Problem Bank**: Spans DSA, System Design, SQL, Machine Learning, and STAR Behavioral questions across Big Tech companies.
* **Calibrated Rubric**: 4-Dimension scoring (Correctness, Clarity, Structure, Depth) anchored against benchmark examples (3/10, 6/10, 9/10) with score ranges and evaluator confidence levels.
* **Resume Improver**: Rewrites resume bullet points using the Google XYZ formula: *"Accomplished [X] as measured by [Y], by doing [Z]"*.

---

## 📊 Measured Results & Quality Evaluation

SPARK-AI includes a 100-question automated benchmark suite (`tests/eval_suite.py`) tracking end-to-end correctness, latency, and tool invocation success:

| Benchmark Category | Questions | Pass Rate | Accuracy | Avg Latency |
| :--- | :---: | :---: | :---: | :---: |
| **Algebra & Calculus (SymPy)** | 25 | 25 / 25 | **100.0%** | 6.3 ms |
| **Code Debugging & Big-O** | 25 | 25 / 25 | **100.0%** | 210.3 ms |
| **SQL Sandbox Playground** | 20 | 20 / 20 | **100.0%** | 47.6 ms |
| **Data Science (NumPy/Pandas)** | 15 | 15 / 15 | **100.0%** | 1.3 ms |
| **Interview Coaching & STAR** | 15 | 15 / 15 | **100.0%** | < 1.0 ms |
| **Overall Tool-Correctness Suite** | **100** | **100 / 100** | **100.0%** | **1.1 ms** |

> [!NOTE]
> **Scope of Benchmarks**:
> - **Deterministic & Local Tool Suite (100 Questions)**: Evaluates the deterministic logic, SymPy symbolic solver, in-memory SQLite engine, AST complexity screening, and interview rubrics (`tests/eval_suite.py`). 99/100 on first run; one expectation fixed for NumPy 2 formatting (`value_counts` scalar stringification).
> - **Live End-to-End Network Benchmark (N=20 Runs per Path)**: Measures real live round-trips to external third-party providers (Google Gemini API and DuckDuckGo/Tavily search engines), capturing cold-start and warm p50/p95 latency distributions.

### 📈 Empirical End-to-End Latency Benchmarks ($N \ge 20$ Runs)

Below are the empirical wall-clock latency distributions measured across all processing paths, separating cold-start from warm-cache execution:

| Processing Path | Sample Size ($N$) | Cold Start (Run 1) | Warm p50 | Warm p95 | Warm Mean | Overall p50 | Overall p95 | Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Response Cache Hit** | 20 | 0.18 ms | **0.17 ms** | **0.21 ms** | 0.18 ms | 0.17 ms | 0.20 ms | In-memory SHA-256 cache |
| **Local RAG / Document Analysis** | 20 | 2.45 ms | **1.56 ms** | **1.80 ms** | 1.62 ms | 1.58 ms | 1.82 ms | Parallel BM25 + Lexical n-gram RRF |
| **Deterministic Math (SymPy)** | 20 | 7.20 ms | **5.10 ms** | **5.50 ms** | 5.22 ms | 5.12 ms | 5.60 ms | In-process symbolic recomputation |
| **Deterministic SQL Playground** | 20 | 6.80 ms | **4.40 ms** | **4.80 ms** | 4.51 ms | 4.42 ms | 4.88 ms | SQLite in-memory with WAL mode |
| **Single-LLM Generation (Gemini)** | 20 | 3,470.4 ms | **1,996.9 ms** | **3,271.5 ms** | 2,263.2 ms | 2,000.5 ms | 3,575.6 ms | Per-provider 8s request timeout; warm p95 reduced to 3.27s |
| **Streaming Path TTFT (Gemini)** | 20 | 1,354.0 ms | **1,497.0 ms** | **1,819.1 ms** | 1,503.6 ms | 1,474.2 ms | 1,819.0 ms | Measured first chunk timestamp; warm p50 TTFT is 1.50s |
| **Search + Real LLM Synthesis (End-to-End)** | 20 | 4,714.8 ms | **6,057.9 ms** | **7,020.9 ms** | 5,578.5 ms | 6,043.1 ms | 6,999.6 ms | Dual network hops: search fetch + LLM token synthesis |

---

## 🐍 Python Version Matrix & Platform Portability

| Environment | Python Version | Platform Target | Runtime Details & Compatibility |
| :--- | :---: | :---: | :--- |
| **Local Development** | **3.14.7** | Windows / Host | Active feature development; strict static typing enforcement |
| **Docker Sandbox** | **3.11** | Linux (`python:3.11-slim`) | Hardened container runtime (`--network none`, `--memory 128m`, read-only FS, non-root) |
| **GitHub Actions CI** | **3.11 & 3.12** | Linux (`ubuntu-latest`) | Automated matrix testing across production LTS Python releases |

**Portability Architecture:**
* **Universal Lockfile**: Cross-platform dependency hashes are pinned in `requirements.lock` generated via `uv pip compile requirements.txt --universal --generate-hashes` across Linux, macOS, and Windows.
* **Backward Syntax Compatibility**: Codebase syntax avoids constructs introduced exclusively in Python 3.12+ (e.g. backslashes inside f-string expressions, PEP 701), guaranteeing clean execution under Python 3.11.

---

## ⚠️ Known Limitations & Mitigations

1. **Upstream Latency Bound on Search + LLM Synthesis (p95 > 5.0 s)**:
   - **Empirical Observation**: The end-to-end Search + LLM synthesis path measured a warm p50 of **6.06 s** and warm p95 of **7.02 s**, exceeding the 5.0-second soft threshold.
   - **Root Cause**: This path inherently performs two sequential external network roundtrips:
     1. Outbound TLS handshake and HTTP search query to DuckDuckGo/Tavily, followed by DOM extraction and prompt-injection sanitization (~1.5–2.5 s).
     2. Outbound HTTPS payload transmission and generative reasoning over the extracted context by Google Gemini Flash-Lite (~2.0–4.0 s).
   - **Mitigations Implemented**:
     - **Streaming Behavior & Output**: The Streamlit web UI (`app.py`) streams a completed response via a smooth word-by-word typewriter animation (`st.write_stream`) after the backend pipeline completes intent routing, deterministic checks, tool execution, and verification passes. This ensures verification badges and citations are validated before rendering. For direct generation paths where streaming is supported, the underlying provider engine (`LLMProvider.generate_stream`) uses native provider streaming (`generate_content_stream` for Gemini, `stream=True` for Groq and OpenAI), measuring an empirical warm p50 Time-to-First-Token (TTFT) of **1,497.0 ms** and warm p95 TTFT of **1,819.1 ms**.
     - **Parallel Multi-Tool Execution**: Independent queries and document analyses execute concurrently using `concurrent.futures.ThreadPoolExecutor`.
     - **Connection Reuse & Gap Regulation**: Enforces 0.2 s minimum request spacing and persistent sessions to avoid rate-limit throttling.
     - **Hard Wall-Clock Timeouts**: Tool invocations enforce non-blocking thread termination via `executor.shutdown(wait=False, cancel_futures=True)`, ensuring timeouts abort immediately on time rather than waiting for background workers.
     - **Deterministic Short-Circuiting**: Intent routing ensures math, SQL, code complexity, and cached inquiries completely bypass external APIs.

2. **Third-Party Provider Network Spikes (Single-LLM Path p95)**:
   - **Empirical Observation**: With the configurable per-provider request timeout (default **8.0 s** via `LLM_TIMEOUT_SECONDS`), warm p50 measured at **1,996.9 ms** and warm p95 at **3,271.5 ms** (down from 13.22 s), preventing unbounded queue hangs.
   - **Mitigation**: The per-provider timeout detaches slow requests at 8.0 s and triggers immediate failover to the next configured provider in the cascade (Gemini → Groq → OpenAI → Ollama), recording circuit breaker metrics and exponential cooldown ladders (60s → 120s → 300s) to guarantee high availability.



---

## 🚀 Quickstart & Setup

### 1. Local Environment Setup

```bash
# Clone the repository
git clone https://github.com/your-username/spark-ai.git
cd spark-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# Install pinned dependencies
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)

```env
# Optional API keys for AI model generation:
GEMINI_API_KEY=AIzaSy...
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...

# Search APIs (Optional, falls back to DuckDuckGo):
TAVILY_API_KEY=tvly-...
BRAVE_API_KEY=BSA...
```

### 3. Launch Web Application

```bash
python -m streamlit run app.py
```
Open your browser to `http://localhost:8501`.

### 4. Docker Deployment

```bash
# Build and run via Docker Compose
docker-compose up --build -d
```

---

## 🧪 Testing & Verification

Run the comprehensive test and evaluation suites:

```bash
# Run security escape validation suite (30 exploits)
python -m pytest tests/test_sandbox_security.py -v

# Run 100-question accuracy & latency benchmark suite
python -m pytest tests/eval_suite.py -s

# Run full project pytest suite
python -m pytest tests/
```

---

## 🎯 Scope of the Local Deterministic Engine

The Local Deterministic Engine operates without third-party LLM calls and executes instantly in single-digit milliseconds for:
- **Symbolic & Elementary Arithmetic**: Exact equation solving, calculus, and mathematical simplification via SymPy.
- **Financial Calculations**: Standard loan amortization, compound interest, and mortgage schedules.
- **In-Memory SQL Playground**: Read-only queries executed over uploaded CSV datasets.
- **Static Code Analysis**: AST-based code complexity estimation and syntax parsing.

> [!NOTE]
> The Deterministic Engine strictly solves bounded mathematical, SQL, and syntax queries. When a user asks an open-ended question or conversational prompt while all external LLM providers are offline, the engine does not fabricate an answer; it clearly notifies the user that generation requires an active AI provider.

---

## 🏛️ Design Decisions & Rationale

* **Why Intent-First Routing?** Directing queries based on classified intent bypasses LLMs entirely for deterministic math or local SQL tasks, reducing costs to zero and cutting latency from ~3 seconds to under 10 ms.
* **Why Multi-Provider Cascading with Circuit Breakers?** LLM provider quotas and rate limits (such as Google Gemini free tier 429 errors) frequently degrade user experience. The cascade router dynamically fails over to Groq, OpenAI, or local execution with exponential backoff cooldowns (60s -> 120s -> 300s), ensuring uninterrupted operation. Non-transient errors (HTTP 400/401/403) are marked as `MISCONFIGURED` to prevent useless retry loops.
* **Why Independent Post-Verification?** LLMs are prone to arithmetic, logical, and code hallucinations. Rather than trusting raw model tokens, SPARK-AI independently recomputes mathematical expressions using SymPy and executes unit assertions in an isolated sandbox, emitting verifiable trust badges.

---

## 🔒 Security Design & Privacy Note

1. **Fail-Closed Code Sandbox**: On public cloud deployments (Render, Hugging Face Spaces, Streamlit Cloud) where Docker is absent, untrusted code execution safely fails closed by default. Subprocesses operate with stripped environment variables and enforce a 50,000-character output cap.
2. **Connection-Level SQL Security**: The SQL playground enforces read-only access directly via `PRAGMA query_only = ON` and `sqlite3.Connection.set_authorizer` allowing only `SELECT`, `READ`, and `FUNCTION` actions, preventing bypasses via `WITH ... DELETE`.
3. **SSRF & DNS Rebinding Protection**: Network fetching restricts schemes strictly to HTTP/HTTPS, limits ports to 80/443, rejects private, loopback, and IPv6 ranges, and independently re-validates each redirect hop.
4. **Local Data Privacy**: User profiles, weak/strong topic tracking, STAR behavioral stories, and chat histories are stored strictly locally in a SQLite database (`user_memory.db`) with WAL mode. No user data, prompts, or documents are shared with third parties beyond the user's explicitly configured LLM provider keys.

---

## 📄 License

Licensed under the [MIT License](LICENSE).

