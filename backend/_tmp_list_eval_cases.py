import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db.supabase_client import supabase

r = supabase.table("eval_cases").select("id,category,query").order("category").execute()
c = Counter(x["category"] for x in r.data)
print("COUNT", len(r.data))
print("BY_CAT", dict(c))
for i, x in enumerate(r.data, 1):
    print(f"{i:02d} [{x['category']}] {x['id']} | {x['query'][:90]}")
