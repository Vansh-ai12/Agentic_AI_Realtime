import os
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
env_path = Path(__file__).resolve().parents[2] / ".env.local"
load_dotenv(dotenv_path=env_path)

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from db.supabase_client import supabase

print("=" * 80)
print("VERIFYING RESTRUCTURED EVAL CASES")
print("=" * 80)

result = supabase.table("eval_cases").select("*").order("created_at").execute()
cases = result.data

print(f"\nTotal cases: {len(cases)}")

for i, case in enumerate(cases[:3], 1):  # Show first 3 examples
    print(f"\n{'='*80}")
    print(f"CASE {i}: {case['category']}")
    print(f"{'='*80}")
    print(f"Query: {case['query']}")
    print(f"\nStructured Criteria (parsed JSON):")
    try:
        criteria = json.loads(case['expected_answer'])
        print(json.dumps(criteria, indent=2))
    except:
        print(f"Raw: {case['expected_answer'][:200]}...")

print(f"\n{'='*80}")
print("D25 EVALUATION APPROACH")
print(f"{'='*80}")

print("\nFor LLM evaluator cases:")
print("1. Parse expected_answer JSON")
print("2. Extract evaluation_prompt and pass_criteria")
print("3. Send answer + criteria to LLM evaluator")
print("4. LLM checks pass_criteria against actual answer")
print("5. Return pass/fail based on LLM judgment")

print("\nFor behavioral check cases:")
print("1. Parse expected_answer JSON")
print("2. Check pipeline state against expected_verdict")
print("3. Verify agents reached/not reached")
print("4. Check for required/forbidden content")
print("5. Return pass/fail based on state verification")

print(f"\n{'='*80}")
print("VERIFICATION COMPLETE")
print(f"{'='*80}")
