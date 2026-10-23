# 🎬 SPARK-AI: 60–90s Demo Video / Walkthrough Script

This script provides a concise, high-impact demonstration sequence to showcase the unique capabilities of SPARK-AI in a screen recording or recruiter demo.

---

### Segment 1: Introduction & Intent Auto-Routing (0:00 – 0:15)
* **Visual**: Clean homepage with dock search bar and active mode pills (`⚡ Auto`, `📚 Study`, `🎯 Interview`, `📊 Data`, `💻 Code`).
* **Prompt**: Type `Calculate the derivative of f(x) = 3*x^3 + 5*x - 12 and verify it.`
* **Action**: Press Enter.
* **Talking Point**:
  > *"Notice how SPARK-AI instantly identifies the mathematical intent without needing to select a calculator tool manually. It computes the derivative step-by-step using SymPy and independently recomputes the final result, displaying the verified badge."*
* **What to Highlight**: `✅ SymPy Verified` badge, intermediate steps, and instant sub-second response.

---

### Segment 2: Hybrid RAG & Page Citations (0:15 – 0:35)
* **Visual**: Click `📎 Attach` in dock search bar, attach a sample PDF or CSV (e.g., `report.pdf` or `dataset.csv`).
* **Prompt**: Type `Summarize key findings from page 1 and compare them.`
* **Action**: Press Enter.
* **Talking Point**:
  > *"Under the hood, SPARK-AI indexes the file using Hybrid Retrieval—combining BM25 keyword matching with dense semantic embeddings via Reciprocal Rank Fusion. It returns page-level grounded citations you can expand and verify directly."*
* **What to Highlight**: `📚 Verified Sources & Citations` expander and page numbers.

---

### Segment 3: Code Sandbox & AST Debugger (0:35 – 0:55)
* **Visual**: Switch dock mode to `💻 Code` or prompt:
* **Prompt**: `Analyze the time and space complexity of merge sort and check for recursive recurrence relations.`
* **Action**: Press Enter.
* **Talking Point**:
  > *"The AST analyzer evaluates loop depth, recursion branches, and Python built-ins like sorted() and slice copies. All outputs are labeled as Estimated Time Complexity with recurrence relation notes. If code runs, it tests it in an isolated subprocess with blocked system imports."*
* **What to Highlight**: Complexity summary: `Time O(N log N)`, `Space O(N)`, and `🛡️ Executed OK` badge.

---

### Segment 4: System Observability & Metrics (0:55 – 1:15)
* **Visual**: Click `📊 Metrics` in the sidebar footer.
* **Action**: Modal opens showing:
  - Total requests & Cache hit rate
  - Provider Circuit Breakers (Gemini, Groq, OpenAI, Ollama)
  - 100-Question benchmark pass rate: `99.0%`
* **Talking Point**:
  > *"Finally, SPARK-AI provides built-in enterprise observability with circuit breakers that apply exponential backoff on 429 rate limits, backed by an automated 100-question benchmark suite running in CI."*

---

### Quick Recording Tips:
1. Set browser zoom to 100% or 110% for crisp typography.
2. Use dark mode for modern visual contrast.
3. Keep screen recording resolution at 1080p (1920x1080) at 60 FPS.
