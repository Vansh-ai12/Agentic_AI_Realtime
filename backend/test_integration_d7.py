from db.supabase_client import supabase
from agents.planner import plan_query
from rag.retrievals import retrieve_chunks

USER_ID = "c0a65264-dc6c-4198-8e88-7c63c180d1cf"  # your user_id
TEST_QUERY = "What internships have I received and what's blocking Project Alpha?"


run_result = supabase.table("agent_runs").insert({
    "user_id": USER_ID,
    "query": TEST_QUERY,
    "status": "in_progress"
}).execute()
run_id = run_result.data[0]["id"]
print(f"Created run: {run_id}")

# 2. Create a real agent_attempts row (attempt #1)
attempt_result = supabase.table("agent_attempts").insert({
    "run_id": run_id,
    "attempt_number": 1
}).execute()
attempt_id = attempt_result.data[0]["id"]
print(f"Created attempt: {attempt_id}")

# 3. Run the planner — this logs tokens automatically since we pass run_id/attempt_id
plan_result = plan_query(TEST_QUERY, run_id=run_id, attempt_id=attempt_id)
print(f"Planner output: {plan_result}")

# 4. For each sub-question, retrieve relevant chunks
all_retrieved = []
for sub_q in plan_result["sub_questions"]:
    chunks = retrieve_chunks(query=sub_q, user_id=USER_ID, top_k=3)
    print(f"\nSub-question: {sub_q}")
    for c in chunks:
        print(f"  [{c['similarity']:.3f}] {c['content'][:80]}")
    all_retrieved.append({"sub_question": sub_q, "chunks": chunks})

# 5. Update the planner_subquestions field on the attempt for record-keeping
supabase.table("agent_attempts").update({
    "planner_subquestions": plan_result["sub_questions"]
}).eq("id", attempt_id).execute()

# 6. Verify token log landed
token_log_check = supabase.table("token_logs").select("*").eq("attempt_id", attempt_id).execute()
print(f"\nToken logs for this attempt: {token_log_check.data}")