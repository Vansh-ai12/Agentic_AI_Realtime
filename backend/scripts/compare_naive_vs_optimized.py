"""
D21 -- Naive vs Optimized Pipeline Comparison
Runs the same query twice:
  1. Naive:     D17 compression disabled (full chunk content on every retry)
  2. Optimized: Current pipeline as-is (D17 compression + D16 memory context)

Compares total synthesizer token usage and prints a clear summary.
"""

import sys
import os
import time

# Force UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend root is on sys.path so imports work when run from scripts/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graph.pipeline import (
    PipelineState,
    build_pipeline,
    memory_reader_node,
    planner_node,
    retriever_node,
    citation_verifier_node,
    critic_node,
    unresolved_node,
    memory_writer_node,
    route_after_critic,
    MAX_RETRIES,
)
from agents.synthesizer import synthesize_answer
from trackings.trace_logger import log_trace_event
from utils.run_manager import create_run, create_attempt, update_run_status
from db.supabase_client import supabase
from langgraph.graph import StateGraph, END

# --- Estimated pricing (UNVERIFIED) ----------------------------------
EST_PRICING = {
    "openai/gpt-oss-20b":  {"input": 0.10 / 1_000_000, "output": 0.30 / 1_000_000},
    "openai/gpt-oss-120b": {"input": 0.60 / 1_000_000, "output": 1.80 / 1_000_000},
}
DEFAULT_PRICING = {"input": 0.30 / 1_000_000, "output": 0.90 / 1_000_000}


# --- Naive synthesizer node (no D17 compression) ---------------------
def naive_synthesizer_node(state: PipelineState) -> PipelineState:
    """Same as synthesizer_node but explicitly passes previous_cited_ids=None
    so _build_context_block always sends full chunk content, even on retries."""
    start = time.time()
    critic_feedback = state.get("critic_reason") if state.get("verdict") == "reject" else None
    result = synthesize_answer(
        state["original_query"],
        state["chunks"],
        memories=state.get("memories"),
        run_id=state.get("run_id"),
        attempt_id=state.get("attempt_id"),
        critic_feedback=critic_feedback,
        previous_answer=state.get("answer"),
        previous_cited_ids=None  # KEY DIFFERENCE: no compression
    )
    state["answer"] = result["answer"]
    state["cited_chunk_ids"] = result["cited_chunk_ids"]
    state["retry_count"] = state.get("retry_count", 0) + (1 if critic_feedback else 0)

    log_trace_event(
        run_id=state.get("run_id"), attempt_id=state.get("attempt_id"),
        node_name="synthesizer",
        input_data={"is_retry": critic_feedback is not None, "mode": "naive"},
        output_data={"answer": result["answer"], "cited_chunk_ids": result["cited_chunk_ids"]},
        tokens_used=result.get("tokens_in", 0) + result.get("tokens_out", 0),
        latency_ms=int((time.time() - start) * 1000)
    )
    return state


def build_naive_pipeline():
    """Identical to build_pipeline() but uses naive_synthesizer_node."""
    graph = StateGraph(PipelineState)
    graph.add_node("memory_reader", memory_reader_node)
    graph.add_node("planner", planner_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("synthesizer", naive_synthesizer_node)
    graph.add_node("citation_verifier", citation_verifier_node)
    graph.add_node("critic", critic_node)
    graph.add_node("unresolved", unresolved_node)
    graph.add_node("write_memory", memory_writer_node)

    graph.set_entry_point("memory_reader")
    graph.add_edge("memory_reader", "planner")
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "synthesizer")
    graph.add_edge("synthesizer", "citation_verifier")
    graph.add_edge("citation_verifier", "critic")
    graph.add_conditional_edges(
        "critic", route_after_critic,
        {"write_memory": "write_memory", "retry": "synthesizer", "unresolved": "unresolved"}
    )
    graph.add_edge("write_memory", END)
    graph.add_edge("unresolved", END)
    return graph.compile()


# --- Query token_logs from Supabase ----------------------------------
def get_synth_tokens(run_id: str):
    """Sum tokens_in + tokens_out for all synthesizer calls in a run."""
    rows = (
        supabase.table("token_logs")
        .select("tokens_in, tokens_out, model")
        .eq("run_id", run_id)
        .eq("agent_role", "synthesizer")
        .execute()
    ).data
    total_in = sum(r["tokens_in"] for r in rows)
    total_out = sum(r["tokens_out"] for r in rows)
    models = list(set(r["model"] for r in rows))
    return total_in, total_out, len(rows), models


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    p = EST_PRICING.get(model, DEFAULT_PRICING)
    return tokens_in * p["input"] + tokens_out * p["output"]


# --- Main ------------------------------------------------------------
def main():
    USER_ID = "c0a65264-dc6c-4198-8e88-7c63c180d1cf"
    QUERY = "What is my exact salary history for the last 5 years and my bank account balance?"

    print("=" * 72)
    print("D21 -- Naive vs Optimized Pipeline Comparison")
    print("=" * 72)
    print(f"\nQuery: {QUERY}")
    print(f"User:  {USER_ID}\n")

    # --- Run 1: NAIVE -------------------------------------------------
    print("-" * 72)
    print("Running NAIVE pipeline (D17 compression DISABLED)...")
    print("-" * 72)
    naive_run_id = create_run(USER_ID, f"[D21-naive] {QUERY}")
    naive_attempt_id = create_attempt(naive_run_id, 1)
    naive_pipeline = build_naive_pipeline()
    naive_state = {
        "user_id": USER_ID,
        "original_query": QUERY,
        "run_id": naive_run_id,
        "attempt_id": naive_attempt_id,
        "retry_count": 0,
    }
    naive_final = naive_pipeline.invoke(naive_state)
    naive_retries = naive_final.get("retry_count", 0)
    print(f"  -> Verdict: {naive_final.get('verdict')} | Retries: {naive_retries}")

    # --- Run 2: OPTIMIZED ---------------------------------------------
    print()
    print("-" * 72)
    print("Running OPTIMIZED pipeline (D17 compression + D16 memory ACTIVE)...")
    print("-" * 72)
    opt_run_id = create_run(USER_ID, f"[D21-optimized] {QUERY}")
    opt_attempt_id = create_attempt(opt_run_id, 1)
    opt_pipeline = build_pipeline()
    opt_state = {
        "user_id": USER_ID,
        "original_query": QUERY,
        "run_id": opt_run_id,
        "attempt_id": opt_attempt_id,
        "retry_count": 0,
    }
    opt_final = opt_pipeline.invoke(opt_state)
    opt_retries = opt_final.get("retry_count", 0)
    print(f"  -> Verdict: {opt_final.get('verdict')} | Retries: {opt_retries}")

    # --- Fetch token data ---------------------------------------------
    print()
    print("=" * 72)
    print("RESULTS -- Synthesizer Token Comparison")
    print("=" * 72)

    n_in, n_out, n_calls, n_models = get_synth_tokens(naive_run_id)
    o_in, o_out, o_calls, o_models = get_synth_tokens(opt_run_id)
    n_total = n_in + n_out
    o_total = o_in + o_out

    if n_total > 0:
        pct_reduction = ((n_total - o_total) / n_total) * 100
    else:
        pct_reduction = 0.0

    print()
    print(f"  Naive:     {n_total:>8,} tokens  ({n_calls} synthesizer calls, {naive_retries} retries)")
    print(f"    |- in:   {n_in:>8,}")
    print(f"    |- out:  {n_out:>8,}")
    print()
    print(f"  Optimized: {o_total:>8,} tokens  ({o_calls} synthesizer calls, {opt_retries} retries)")
    print(f"    |- in:   {o_in:>8,}")
    print(f"    |- out:  {o_out:>8,}")
    print()
    print(f"  +-----------------------------------------+")
    print(f"  |  Token Reduction:  {pct_reduction:>6.1f}%               |")
    print(f"  |  Tokens Saved:     {n_total - o_total:>8,}              |")
    print(f"  +-----------------------------------------+")

    # --- Estimated cost (clearly labeled) -----------------------------
    print()
    print("  ---- Estimated cost (unverified Groq pricing) ----")
    n_model = n_models[0] if n_models else "openai/gpt-oss-120b"
    o_model = o_models[0] if o_models else "openai/gpt-oss-120b"
    n_cost = estimate_cost(n_model, n_in, n_out)
    o_cost = estimate_cost(o_model, o_in, o_out)
    cost_saved = n_cost - o_cost
    print(f"    Naive cost (est.):     ${n_cost:.5f}")
    print(f"    Optimized cost (est.): ${o_cost:.5f}")
    print(f"    Saved (est.):          ${cost_saved:.5f}")
    print(f"    [!] These dollar figures use hardcoded, unverified pricing.")
    print(f"        Only the token counts above are real, measured values.")

    print()
    print(f"  Run IDs for manual inspection:")
    print(f"    Naive:     {naive_run_id}")
    print(f"    Optimized: {opt_run_id}")
    print()


if __name__ == "__main__":
    main()
