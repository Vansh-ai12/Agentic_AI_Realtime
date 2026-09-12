import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
env_path = Path(__file__).resolve().parents[2] / ".env.local"
load_dotenv(dotenv_path=env_path)

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from db.supabase_client import supabase

print("=" * 80)
print("VERIFYING EVAL CASES IN SUPABASE")
print("=" * 80)

# Query 1: Select all eval cases
print("\n" + "=" * 80)
print("QUERY 1: SELECT id, category, query, expected_answer, created_at FROM eval_cases ORDER BY created_at;")
print("=" * 80)
try:
    result = supabase.table("eval_cases").select("*").order("created_at").execute()
    cases = result.data
    print(f"Row count: {len(cases)}")
    
    for i, case in enumerate(cases, 1):
        print(f"\n{i}. ID: {case['id']}")
        print(f"   Category: {case['category']}")
        print(f"   Query: {case['query']}")
        print(f"   Expected Answer: {case['expected_answer'][:100]}...")
        print(f"   Created At: {case['created_at']}")
except Exception as e:
    print(f"Error: {e}")

# Query 2: Count rows
print("\n" + "=" * 80)
print("QUERY 2: SELECT COUNT(*) FROM eval_cases;")
print("=" * 80)
try:
    # Supabase doesn't support COUNT(*) directly via the client, so we count in Python
    result = supabase.table("eval_cases").select("id", count="exact").execute()
    print(f"Count: {result.count}")
except Exception as e:
    print(f"Error: {e}")

# Query 3: Distinct categories
print("\n" + "=" * 80)
print("QUERY 3: SELECT DISTINCT category FROM eval_cases;")
print("=" * 80)
try:
    result = supabase.table("eval_cases").select("category").execute()
    categories = set(case['category'] for case in result.data)
    print(f"Distinct categories: {sorted(categories)}")
    
    # Check against schema constraint
    schema_categories = {'normal', 'adversarial', 'missing_data', 'edge_case'}
    if categories == schema_categories:
        print("PASS: Categories match schema constraint")
    else:
        print(f"FAIL: Categories don't match schema constraint")
        print(f"  Expected: {schema_categories}")
        print(f"  Actual: {categories}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
