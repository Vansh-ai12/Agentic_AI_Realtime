from db.supabase_client import supabase

result = supabase.table('eval_results').select('*').execute()
print(f'Total eval_results: {len(result.data)}')
print('Recent results:')
for r in result.data[-5:]:
    print(f"  case={r['eval_case_id'][:8]}... passed={r['passed']}")
