import json

print("Starting script...")
from graph.pipeline import build_pipeline
from utils.run_manager import create_run, create_attempt
from db.supabase_client import supabase
print("Import succeeded")

pipeline = build_pipeline()
print("Pipeline built")

user_id = "c0a65264-dc6c-4198-8e88-7c63c180d1cf"
query = "What internships have I received and what's blocking Project Alpha?"

run_id = create_run(user_id, query)
attempt_id = create_attempt(run_id, attempt_number=1)
print(f"Created run_id: {run_id}")

initial_state = {
    "user_id": user_id,
    "original_query": query,
    "run_id": run_id,
    "attempt_id": attempt_id,
    "retry_count": 0,
    "input_guard_result": None,
    "chunk_guard_result": None,
    "blocked_reason": None,
    "output_guardrail_result": None,
}

print("Invoking pipeline...\n")
final_state = pipeline.invoke(initial_state)
print("Invoke complete\n")


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)



section("RUN SUMMARY")
print(f"Run ID:        {run_id}")
print(f"Query:         {query}")
print(f"Verdict:       {final_state.get('verdict')}")
print(f"Retry count:   {final_state.get('retry_count')}")
print(f"Blocked?:      {final_state.get('blocked_reason') or 'No'}")


section("GUARDRAILS")
print("Input guard result: ", final_state.get("input_guard_result"))
print("Chunk guard result: ", final_state.get("chunk_guard_result"))
print("Output guard result:", final_state.get("output_guardrail_result"))


section("PLANNING")
sub_qs = final_state.get("sub_questions") or []
for i, q in enumerate(sub_qs, 1):
    print(f"  {i}. {q}")


section("RETRIEVAL")
chunks = final_state.get("chunks") or []
print(f"Chunks retrieved: {len(chunks)}")
for c in chunks:
    preview = (c.get("content", "")[:80] + "...") if c.get("content") else ""
    print(f"  - {c.get('chunk_id')}: {preview}")


section("MEMORY USED")
memories = final_state.get("memories") or []
print(f"Relevant memories found: {len(memories)}")
for m in memories:
    print(f"  - ({m.get('similarity', 0):.3f}) {m.get('summary')}")


section("FINAL ANSWER")
print(final_state.get("answer"))
print(f"\nCited chunks:       {final_state.get('cited_chunk_ids')}")
print(f"Citations verified: {final_state.get('citations_verified')}")
print(f"Critic verdict:     {final_state.get('verdict')}")
print(f"Critic reason:      {final_state.get('critic_reason')}")


section("MEMORY WRITE")
print(json.dumps(final_state.get("memory_write_result"), indent=2))


section("FULL NODE-BY-NODE TRACE")
events = supabase.table("trace_events").select("*") \
    .eq("run_id", run_id).order("created_at").execute()

total_tokens = 0
total_latency = 0
for e in events.data:
    tokens = e.get("tokens_used", 0) or 0
    latency = e.get("latency_ms", 0) or 0
    total_tokens += tokens
    total_latency += latency
    print(f"  [{e['node_name']:<20}] tokens={tokens:<6} latency={latency}ms")

print(f"\nTotal events:  {len(events.data)}")
print(f"Total tokens:  {total_tokens}")
print(f"Total latency: {total_latency}ms ({total_latency / 1000:.1f}s)")


section("TOKEN BREAKDOWN BY AGENT ROLE")
token_logs = supabase.table("token_logs").select("*") \
    .eq("run_id", run_id).execute()

role_totals = {}
for t in token_logs.data:
    role = t["agent_role"]
    role_totals[role] = role_totals.get(role, 0) + t["tokens_in"] + t["tokens_out"]

for role, total in sorted(role_totals.items(), key=lambda x: -x[1]):
    pct = (total / sum(role_totals.values()) * 100) if role_totals else 0
    print(f"  {role:<20} {total:>6} tokens  ({pct:.1f}%)")


section("FINAL RUN STATUS (from agent_runs)")
run_row = supabase.table("agent_runs").select("*").eq("id", run_id).execute()
if run_row.data:
    r = run_row.data[0]
    print(f"Status:         {r.get('status')}")
    print(f"Total attempts: {r.get('total_attempts')}")
    print(f"Completed at:   {r.get('completed_at')}")

print("\nDone.")