import os
import sys
import json
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
env_path = Path(__file__).resolve().parents[2] / ".env.local"
load_dotenv(dotenv_path=env_path)

from db.supabase_client import supabase
from graph.pipeline import build_pipeline
from utils.run_manager import create_run, create_attempt
from eval.evaluate_criteria import CriteriaEvaluator

USER_ID = "c0a65264-dc6c-4198-8e88-7c63c180d1cf"
GROQ_TPM_LIMIT = 8000

def parse_args():
    parser = argparse.ArgumentParser(description="Run Sentinel-RAG evaluation suite")
    parser.add_argument("--category", type=str, default=None, help="Filter by category (normal, adversarial, missing_data, edge_case)")
    parser.add_argument("--resume", action="store_true", help="Resume run and skip already evaluated cases")
    parser.add_argument("--output", type=str, default="eval_summary.json", help="Path to write JSON summary")
    parser.add_argument("--cooldown-mult", type=float, default=1.0, help="Multiplier for TPM cooldown")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 80)
    print("SENTINEL-RAG FULL EVALUATION SUITE (D25)")
    print(f"Rate-limit aware: {GROQ_TPM_LIMIT} TPM pacing with exponential backoff")
    print("=" * 80)

    # Initialize evaluator
    evaluator = CriteriaEvaluator()

    # Build pipeline
    try:
        pipeline = build_pipeline()
        print("Pipeline built successfully.")
    except Exception as e:
        print(f"Failed to build pipeline: {e}")
        sys.exit(1)

    # Fetch all eval cases from Supabase
    print("\nFetching eval cases from Supabase...")
    result = supabase.table("eval_cases").select("*").order("category").execute()
    all_cases = result.data
    print(f"Found {len(all_cases)} total eval cases in Supabase.")

    if args.category:
        cases_to_run = [c for c in all_cases if c["category"].lower() == args.category.lower()]
        print(f"Filtered by category '{args.category}': {len(cases_to_run)} cases.")
    else:
        cases_to_run = all_cases

    # Load previously saved results if resuming
    completed_ids = set()
    evaluation_results = []
    output_path = Path(args.output)
    if args.resume and output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
                evaluation_results = saved.get("results", [])
                completed_ids = {r["eval_case_id"] for r in evaluation_results if r.get("passed") is not None}
                print(f"Resuming: found {len(completed_ids)} previously evaluated cases. Skipping them.")
        except Exception as e:
            print(f"Could not load resume file {output_path}: {e}")

    total_to_evaluate = len([c for c in cases_to_run if c["id"] not in completed_ids])
    print(f"Cases to evaluate this run: {total_to_evaluate}")

    case_idx = 0
    for case in cases_to_run:
        case_id = case["id"]
        category = case["category"]
        query = case["query"]

        if case_id in completed_ids:
            print(f"\n[SKIP] [{category}] {case_id} already evaluated.")
            continue

        case_idx += 1
        print("\n" + "-" * 80)
        print(f"[{case_idx}/{total_to_evaluate}] Running [{category}] {case_id}")
        print(f"Query: {query}")

        start_time = time.time()
        run_id = None
        attempt_id = None

        try:
            run_id = create_run(USER_ID, query)
            attempt_id = create_attempt(run_id, attempt_number=1)

            initial_state = {
                "user_id": USER_ID,
                "original_query": query,
                "run_id": run_id,
                "attempt_id": attempt_id,
                "retry_count": 0,
                "input_guard_result": None,
                "chunk_guard_result": None,
                "blocked_reason": None,
                "output_guardrail_result": None,
            }

            print("  Invoking pipeline...")
            final_state = pipeline.invoke(initial_state)

            duration_s = time.time() - start_time
            answer = final_state.get("answer", "")
            verdict = final_state.get("verdict", "")
            retry_count = final_state.get("retry_count", 0)
            citations_verified = final_state.get("citations_verified")
            cited_chunk_ids = final_state.get("cited_chunk_ids", [])
            citations = final_state.get("citations", [])

            # Fetch token logs from Supabase for this run
            token_result = supabase.table("token_logs").select("tokens_in", "tokens_out").eq("run_id", run_id).execute()
            tokens_in = sum(log["tokens_in"] for log in token_result.data)
            tokens_out = sum(log["tokens_out"] for log in token_result.data)
            case_tokens = tokens_in + tokens_out

            print(f"  Verdict: {verdict}")
            print(f"  Retries: {retry_count}")
            print(f"  Citations verified: {citations_verified} ({len(cited_chunk_ids)} chunks cited)")
            print(f"  Tokens used: {case_tokens:,} (in: {tokens_in:,}, out: {tokens_out:,}) in {duration_s:.1f}s")

            # Evaluate against criteria
            print("  Evaluating against criteria...")
            eval_result = evaluator.evaluate_case(case, final_state)
            passed = eval_result["passed"]
            reason = eval_result["reason"]
            print(f"  Result: {'[PASS]' if passed else '[FAIL]'} - {reason}")

            entry = {
                "eval_case_id": case_id,
                "run_id": run_id,
                "category": category,
                "query": query,
                "passed": passed,
                "verdict": verdict,
                "retry_count": retry_count,
                "citations_verified": citations_verified,
                "cited_chunk_count": len(cited_chunk_ids),
                "tokens_used": case_tokens,
                "duration_seconds": round(duration_s, 2),
                "notes": reason,
                "details": eval_result.get("details", {})
            }
            evaluation_results.append(entry)

            # Insert into eval_results in Supabase
            try:
                supabase.table("eval_results").insert({
                    "eval_case_id": case_id,
                    "run_id": run_id,
                    "passed": passed,
                    "notes": reason
                }).execute()
            except Exception as dbe:
                print(f"  Warning: Supabase eval_results insert failed: {dbe}")

            # Save checkpoint
            _save_checkpoint(output_path, evaluation_results)

            # Cooldown to stay under Groq 8,000 TPM limit
            if case_idx < total_to_evaluate:
                # Minimum 4 seconds, plus token recovery time
                needed_cooldown = max(4.0, (case_tokens / GROQ_TPM_LIMIT) * 60.0 * args.cooldown_mult)
                print(f"  Rate-limit cooldown: waiting {needed_cooldown:.1f}s...")
                time.sleep(needed_cooldown)

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  ERROR evaluating case {case_id}: {e}")
            entry = {
                "eval_case_id": case_id,
                "run_id": run_id,
                "category": category,
                "query": query,
                "passed": False,
                "verdict": "error",
                "retry_count": 0,
                "citations_verified": False,
                "cited_chunk_count": 0,
                "tokens_used": 0,
                "duration_seconds": round(time.time() - start_time, 2),
                "notes": f"Pipeline exception: {str(e)}",
                "details": {}
            }
            evaluation_results.append(entry)
            _save_checkpoint(output_path, evaluation_results)
            time.sleep(5.0)

    # Compute and print comprehensive evaluation metrics
    print_summary_metrics(evaluation_results)


def _save_checkpoint(path: Path, results: list):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"results": results}, f, indent=2)
    except Exception as e:
        print(f"Warning: could not write checkpoint to {path}: {e}")


def print_summary_metrics(results: list):
    if not results:
        print("\nNo results to evaluate.")
        return

    print("\n" + "=" * 80)
    print("D25 EVALUATION FINAL METRICS REPORT")
    print("=" * 80)

    total_cases = len(results)
    passed_cases = sum(1 for r in results if r["passed"])
    overall_accuracy = (passed_cases / total_cases * 100) if total_cases > 0 else 0

    total_tokens = sum(r["tokens_used"] for r in results)
    avg_tokens = (total_tokens / total_cases) if total_cases > 0 else 0

    # Citation correctness rate
    cases_with_citations = [r for r in results if r.get("cited_chunk_count", 0) > 0]
    cases_with_verified_citations = [r for r in cases_with_citations if r.get("citations_verified") is True]
    citation_correctness_rate = (
        (len(cases_with_verified_citations) / len(cases_with_citations) * 100)
        if cases_with_citations else 100.0
    )

    # Retry resolution rate: of cases that retried, how many resolved?
    cases_with_retries = [r for r in results if r.get("retry_count", 0) > 0]
    cases_retry_resolved = [r for r in cases_with_retries if r.get("verdict") in ("resolved", "approve")]
    retry_resolution_rate = (
        (len(cases_retry_resolved) / len(cases_with_retries) * 100)
        if cases_with_retries else 100.0
    )

    print(f"\n1. Overall Accuracy:          {overall_accuracy:.1f}% ({passed_cases}/{total_cases} passed)")
    print(f"2. Citation Correctness Rate:  {citation_correctness_rate:.1f}% ({len(cases_with_verified_citations)}/{len(cases_with_citations)} cited cases verified)")
    print(f"3. Retry-Resolution Rate:      {retry_resolution_rate:.1f}% ({len(cases_retry_resolved)}/{len(cases_with_retries)} cases with retries resolved)")
    print(f"4. Average Tokens / Query:     {int(avg_tokens):,} tokens (Total: {total_tokens:,})")

    # Category breakdown
    print("\n" + "-" * 80)
    print("CATEGORY BREAKDOWN:")
    print("-" * 80)
    categories = sorted(list(set(r["category"] for r in results)))

    print(f"{'Category':<16} | {'Count':<6} | {'Passed':<6} | {'Accuracy':<10} | {'Avg Tokens':<12} | {'Avg Retries':<10}")
    print("-" * 72)

    for cat in categories:
        cat_results = [r for r in results if r["category"] == cat]
        c_total = len(cat_results)
        c_passed = sum(1 for r in cat_results if r["passed"])
        c_acc = (c_passed / c_total * 100) if c_total > 0 else 0
        c_tokens = sum(r["tokens_used"] for r in cat_results) / c_total if c_total > 0 else 0
        c_retries = sum(r.get("retry_count", 0) for r in cat_results) / c_total if c_total > 0 else 0

        print(f"{cat:<16} | {c_total:<6} | {c_passed:<6} | {c_acc:>6.1f}%    | {int(c_tokens):>8,}     | {c_retries:>6.2f}")

    print("\n" + "=" * 80)
    print("CASE-BY-CASE SUMMARY:")
    print("=" * 80)
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"[{status}] [{r['category']:<12}] {r['eval_case_id'][:8]}... | Retries: {r['retry_count']} | Tokens: {r['tokens_used']:,} | {r['notes'][:60]}")
    print("=" * 80)


if __name__ == "__main__":
    main()
