"""
Empirical Benchmark Suite:
1. 20-run Single-LLM Generation Benchmark (process_message with per-provider 8s timeout)
2. 20-run Streaming Time-To-First-Token (TTFT) Benchmark (generate_stream first chunk timestamp)
Computes: Cold Start (Run 1), Warm p50, Warm p95, Warm Mean, Overall p50, Overall p95.
"""

import os
import sys
import time
import json
import numpy as np
from dotenv import load_dotenv

# Ensure repo root is in sys.path
repo_root = os.path.dirname(os.path.abspath(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

load_dotenv(override=False)

from core.conversation import ConversationSession
from core.orchestrator import ChatbotOrchestrator
from core.llm_provider import LLMProvider
from core.config import PROVIDER_TIMEOUT_SECONDS
from core.circuit_breaker import circuit_breaker
from core.rate_limiter import reset_circuit_breaker
from core.provider_status import reset_provider_status

def reset_all_provider_states():
    for prov in ["gemini", "groq", "openai", "ollama"]:
        reset_provider_status(prov)
        circuit_breaker.record_success(prov)
        reset_circuit_breaker(prov)

SINGLE_LLM_PROMPTS = [
    f"Explain concept #{i+1}: in one concise sentence, what is the core benefit of {concept}?"
    for i, concept in enumerate([
        "binary search trees", "hash tables", "Dijkstra algorithm", "quicksort", "merge sort",
        "dynamic programming", "breadth-first search", "depth-first search", "tries", "heaps",
        "memoization", "topological sort", "union find", "LRU cache", "prefix sums",
        "sliding window", "two pointers", "monotonic stack", "greedy algorithms", "AVL trees"
    ])
]

STREAMING_PROMPTS = [
    f"Query #{i+1}: What is the primary purpose of {tech} in software engineering? Answer in 1-2 sentences."
    for i, tech in enumerate([
        "Docker containerization", "Kubernetes orchestration", "Redis in-memory caching",
        "PostgreSQL WAL mode", "Git distributed version control", "RESTful APIs",
        "GraphQL schema querying", "WebSocket duplex protocol", "Kafka event streaming",
        "OAuth 2.0 authorization", "JWT stateless authentication", "gRPC protocol buffers",
        "Nginx reverse proxy", "Terraform infrastructure as code", "Prometheus telemetry",
        "Grafana observability dashboards", "Elasticsearch full text search", "CI/CD automated pipelines",
        "Microservices architecture", "Event-driven messaging architecture"
    ])
]

def calc_stats(times):
    cold = times[0]
    warm = times[1:]
    return {
        "cold_ms": round(float(cold), 2),
        "warm_mean_ms": round(float(np.mean(warm)), 2),
        "warm_p50_ms": round(float(np.percentile(warm, 50)), 2),
        "warm_p95_ms": round(float(np.percentile(warm, 95)), 2),
        "warm_min_ms": round(float(np.min(warm)), 2),
        "warm_max_ms": round(float(np.max(warm)), 2),
        "overall_p50_ms": round(float(np.percentile(times, 50)), 2),
        "overall_p95_ms": round(float(np.percentile(times, 95)), 2),
    }

def run_single_llm_benchmark():
    print("=" * 70)
    print("1. SINGLE-LLM GENERATION BENCHMARK (N=20 RUNS)")
    print(f"Per-provider timeout: {PROVIDER_TIMEOUT_SECONDS}s")
    print("=" * 70)

    reset_all_provider_states()
    orchestrator = ChatbotOrchestrator()
    times = []
    providers = []

    for i, prompt in enumerate(SINGLE_LLM_PROMPTS):
        reset_all_provider_states()
        session = ConversationSession(session_id=f"bench_single_llm_{i}_{time.time()}")
        session.user_id = f"bench_user_llm_{i}_{time.time()}"
        
        t0 = time.perf_counter()
        res = orchestrator.process_message(
            session=session,
            user_message=prompt
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        times.append(elapsed_ms)
        prov = res.get("provider", "unknown")
        providers.append(prov)
        status = "OK" if res.get("success") else "FAIL"
        
        print(f"  Run {i+1:02d}: {elapsed_ms:7.1f} ms | Status: {status} | Provider: {prov}")
        time.sleep(0.4)  # Rate limit gap

    stats = calc_stats(times)
    print("\n--- SINGLE-LLM RESULTS ---")
    print(f"Cold Start (Run 1): {stats['cold_ms']} ms")
    print(f"Warm p50:           {stats['warm_p50_ms']} ms")
    print(f"Warm p95:           {stats['warm_p95_ms']} ms")
    print(f"Warm Mean:          {stats['warm_mean_ms']} ms (Min: {stats['warm_min_ms']} ms, Max: {stats['warm_max_ms']} ms)")
    print(f"Overall p50:        {stats['overall_p50_ms']} ms")
    print(f"Overall p95:        {stats['overall_p95_ms']} ms")
    return {"raw_times": times, "stats": stats, "providers": providers}

def run_streaming_ttft_benchmark():
    print("\n" + "=" * 70)
    print("2. STREAMING PATH TIME-TO-FIRST-TOKEN (TTFT) BENCHMARK (N=20 RUNS)")
    print(f"Per-provider timeout: {PROVIDER_TIMEOUT_SECONDS}s")
    print("=" * 70)

    reset_all_provider_states()
    provider = LLMProvider(provider="gemini")
    ttft_times = []
    total_times = []
    chunk_counts = []

    for i, prompt in enumerate(STREAMING_PROMPTS):
        reset_all_provider_states()
        messages = [{"role": "user", "content": prompt}]
        system_prompt = "You are a concise engineering assistant. Answer in 1-2 sentences."

        t0 = time.perf_counter()
        first_chunk_time = None
        chunks = []

        try:
            for chunk in provider.generate_stream(
                messages=messages,
                system_prompt=system_prompt,
                timeout=PROVIDER_TIMEOUT_SECONDS
            ):
                if first_chunk_time is None and chunk and chunk.strip():
                    first_chunk_time = time.perf_counter()
                chunks.append(chunk)
            
            t_end = time.perf_counter()
            
            if first_chunk_time is not None:
                ttft_ms = (first_chunk_time - t0) * 1000.0
                total_ms = (t_end - t0) * 1000.0
                ttft_times.append(ttft_ms)
                total_times.append(total_ms)
                chunk_counts.append(len(chunks))
                print(f"  Run {i+1:02d}: TTFT = {ttft_ms:6.1f} ms | Total = {total_ms:6.1f} ms | Chunks = {len(chunks):2d}")
            else:
                print(f"  Run {i+1:02d}: No tokens received")
        except Exception as e:
            print(f"  Run {i+1:02d} FAILED: {e}")

        time.sleep(0.4)

    stats_ttft = calc_stats(ttft_times)
    stats_total = calc_stats(total_times)

    print("\n--- STREAMING TTFT RESULTS ---")
    print(f"Cold Start TTFT (Run 1): {stats_ttft['cold_ms']} ms")
    print(f"Warm p50 TTFT:           {stats_ttft['warm_p50_ms']} ms")
    print(f"Warm p95 TTFT:           {stats_ttft['warm_p95_ms']} ms")
    print(f"Warm Mean TTFT:          {stats_ttft['warm_mean_ms']} ms (Min: {stats_ttft['warm_min_ms']} ms, Max: {stats_ttft['warm_max_ms']} ms)")
    print(f"Overall p50 TTFT:        {stats_ttft['overall_p50_ms']} ms")
    print(f"Overall p95 TTFT:        {stats_ttft['overall_p95_ms']} ms")

    return {
        "ttft_times": ttft_times,
        "total_times": total_times,
        "chunk_counts": chunk_counts,
        "stats_ttft": stats_ttft,
        "stats_total": stats_total
    }

if __name__ == "__main__":
    res_single = run_single_llm_benchmark()
    res_stream = run_streaming_ttft_benchmark()

    out_file = os.path.join(repo_root, "benchmarks_measured.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "single_llm": res_single,
            "streaming_ttft": res_stream
        }, f, indent=2)
    print("\nSaved empirical benchmark results to benchmarks_measured.json")
