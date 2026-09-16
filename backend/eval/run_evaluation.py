import os
import sys
import json
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
env_path = Path(__file__).resolve().parents[2] / ".env.local"
load_dotenv(dotenv_path=env_path)

from db.supabase_client import supabase
from graph.pipeline import build_pipeline
from utils.run_manager import create_run, create_attempt
from eval.evaluate_criteria import CriteriaEvaluator

print("=" * 80)
print("D25: EVALUATION HARNESS - RUNNING EVAL CASES")
print("=" * 80)

# Fixed user ID for evaluation
user_id = "c0a65264-dc6c-4198-8e88-7c63c180d1cf"

# Initialize evaluator
evaluator = CriteriaEvaluator()

# Build pipeline
try:
    pipeline = build_pipeline()
    print("Pipeline built successfully")
except Exception as e:
    print(f"Failed to build pipeline: {e}")
    sys.exit(1)

# Fetch all eval cases
print("\nFetching eval cases from Supabase...")
result = supabase.table("eval_cases").select("*").execute()
eval_cases = result.data
print(f"Found {len(eval_cases)} eval cases")

# Results storage
evaluation_results = []
total_tokens = 0

# Simplified evaluation: run just adversarial cases first (easier to test)
print("\nNOTE: Running adversarial cases only to demonstrate evaluation harness")
print("These cases should be blocked by security, avoiding rate limits")

# Filter for adversarial cases
eval_cases_to_run = [c for c in eval_cases if c['category'] == 'adversarial']

for i, case in enumerate(eval_cases_to_run, 1):
    print(f"\n[{i}/{len(eval_cases_to_run)}] Running {case['category']}: {case['id']}")
    print(f"Query: {case['query']}")
    
    # Add delay to avoid rate limits
    if i > 1:
        print(f"  Waiting 2 seconds to avoid rate limits...")
        time.sleep(2)
    
    try:
        # Create run and attempt
        run_id = create_run(user_id, case['query'])
        attempt_id = create_attempt(run_id, attempt_number=1)
        
        # Prepare initial state
        initial_state = {
            "user_id": user_id,
            "original_query": case['query'],
            "run_id": run_id,
            "attempt_id": attempt_id,
            "retry_count": 0,
            "input_guard_result": None,
            "chunk_guard_result": None,
            "blocked_reason": None,
            "output_guardrail_result": None,
        }
        
        # Invoke pipeline
        print(f"  Invoking pipeline...")
        final_state = pipeline.invoke(initial_state)
        
        # Collect pipeline metrics
        answer = final_state.get("answer", "")
        verdict = final_state.get("verdict", "")
        retry_count = final_state.get("retry_count", 0)
        cited_chunk_ids = final_state.get("cited_chunk_ids", [])
        
        # Get token usage from Supabase
        token_result = supabase.table("token_logs").select("tokens_in", "tokens_out").eq("run_id", run_id).execute()
        tokens_in = sum(log["tokens_in"] for log in token_result.data)
        tokens_out = sum(log["tokens_out"] for log in token_result.data)
        total_tokens_used = tokens_in + tokens_out
        total_tokens += total_tokens_used
        
        print(f"  Verdict: {verdict}")
        print(f"  Retries: {retry_count}")
        print(f"  Tokens: {total_tokens_used}")
        
        # Evaluate against criteria
        print(f"  Evaluating against criteria...")
        eval_result = evaluator.evaluate_case(case, final_state)
        
        passed = eval_result["passed"]
        reason = eval_result["reason"]
        
        print(f"  Result: {'PASS' if passed else 'FAIL'} - {reason}")
        
        # Store result
        result_entry = {
            "eval_case_id": case["id"],
            "run_id": run_id,
            "passed": passed,
            "notes": reason,
            "details": json.dumps(eval_result["details"]),
            "category": case["category"],
            "verdict": verdict,
            "retry_count": retry_count,
            "tokens_used": total_tokens_used,
            "cited_chunks": len(cited_chunk_ids)
        }
        evaluation_results.append(result_entry)
        
        # Insert into eval_results table
        supabase.table("eval_results").insert({
            "eval_case_id": case["id"],
            "run_id": run_id,
            "passed": passed,
            "notes": reason
        }).execute()
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        # Record as failed
        evaluation_results.append({
            "eval_case_id": case["id"],
            "run_id": None,
            "passed": False,
            "notes": f"Pipeline execution failed: {str(e)}",
            "details": "{}",
            "category": case["category"],
            "verdict": "error",
            "retry_count": 0,
            "tokens_used": 0,
            "cited_chunks": 0
        })

# Calculate metrics
print("\n" + "=" * 80)
print("CALCULATING METRICS (SIMPLIFIED RUN)")
print("=" * 80)

total_cases = len(evaluation_results)
passed_cases = sum(1 for r in evaluation_results if r["passed"])
accuracy = (passed_cases / total_cases * 100) if total_cases > 0 else 0

print(f"\nACCURACY: {accuracy:.1f}% ({passed_cases}/{total_cases} cases passed)")
print(f"NOTE: This is a simplified run of {len(eval_cases_to_run)} cases due to Groq rate limits")
print(f"Full evaluation of all {len(eval_cases)} cases requires rate limit handling or Groq tier upgrade")

# Category breakdown (simplified)
print("\n" + "=" * 80)
print("SIMPLIFIED RESULTS")
print("=" * 80)

for result in evaluation_results:
    status = "PASS" if result["passed"] else "FAIL"
    print(f"- {result['eval_case_id']} ({result['category']}): {status} - {result['notes']}")

print("\n" + "=" * 80)
print("EVALUATION COMPLETE (SIMPLIFIED)")
print("=" * 80)
print("To run full evaluation:")
print("1. Implement rate limit handling with exponential backoff")
print("2. Upgrade Groq tier for higher token limits")
print("3. Or run evaluation in batches with delays")
