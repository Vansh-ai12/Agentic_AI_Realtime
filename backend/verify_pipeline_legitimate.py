import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[0]))

from dotenv import load_dotenv
env_path = Path(__file__).resolve().parents[1] / ".env.local"
load_dotenv(dotenv_path=env_path)

print("=" * 80)
print("VERIFICATION STEP 4: TEST FULL PIPELINE WITH LEGITIMATE QUERY")
print("=" * 80)

try:
    from graph.pipeline import build_pipeline
    from utils.run_manager import create_run, create_attempt
    
    print("PASS: Successfully imported pipeline and utilities")
except ImportError as e:
    print(f"FAIL: Import failed: {e}")
    sys.exit(1)

try:
    pipeline = build_pipeline()
    print("PASS: Pipeline built successfully")
except Exception as e:
    print(f"FAIL: Pipeline build failed: {e}")
    sys.exit(1)

user_id = "c0a65264-dc6c-4198-8e88-7c63c180d1cf"
legitimate_query = "What internships have I received and what's blocking Project Alpha?"

print(f"\nTest query: '{legitimate_query}'")

try:
    run_id = create_run(user_id, legitimate_query)
    attempt_id = create_attempt(run_id, attempt_number=1)
    print(f"PASS: Created run_id: {run_id}")
except Exception as e:
    print(f"FAIL: Run creation failed: {e}")
    sys.exit(1)

initial_state = {
    "user_id": user_id,
    "original_query": legitimate_query,
    "run_id": run_id,
    "attempt_id": attempt_id,
    "retry_count": 0,
    "input_guard_result": None,
    "chunk_guard_result": None,
    "blocked_reason": None,
    "output_guardrail_result": None,
}

print("\nInvoking pipeline with legitimate query...")
try:
    final_state = pipeline.invoke(initial_state)
    print("PASS: Pipeline invocation completed")
except Exception as e:
    print(f"FAIL: Pipeline invocation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("FINAL STATE ANALYSIS")
print("=" * 80)

print(f"\nInput guard result: {final_state.get('input_guard_result')}")
print(f"Sub-questions: {final_state.get('sub_questions')}")
print(f"Chunk guard result has injection: {final_state.get('chunk_guard_result', {}).get('has_injection', 'N/A')}")
print(f"Chunk guard excluded chunks: {len(final_state.get('chunk_guard_result', {}).get('excluded_chunks', []))}")
print(f"Answer exists: {bool(final_state.get('answer'))}")
print(f"Cited chunks: {final_state.get('cited_chunk_ids')}")
print(f"Citations verified: {final_state.get('citations_verified')}")
print(f"Verdict: {final_state.get('verdict')}")
print(f"Critic reason: {final_state.get('critic_reason')}")
print(f"Output guardrail result: {final_state.get('output_guardrail_result')}")

# Verify the legitimate query was processed normally
if final_state.get('blocked_reason'):
    print("\nFAIL: Legitimate query was incorrectly blocked")
    print(f"  Blocked reason: {final_state.get('blocked_reason')}")
elif final_state.get('answer'):
    print("\nPASS: Legitimate query was processed successfully")
    print(f"  Answer generated: {final_state.get('answer')[:100]}...")
else:
    print("\nFAIL: Legitimate query did not produce an answer")
    print(f"  Verdict: {final_state.get('verdict')}")

print("\n" + "=" * 80)
print("FULL PIPELINE LEGITIMATE QUERY TEST COMPLETE")
print("=" * 80)
