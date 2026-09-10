print("Starting script...")
from graph.pipeline import build_pipeline
from utils.run_manager import create_run, create_attempt
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
}

print("Invoking pipeline...")
final_state = pipeline.invoke(initial_state)
print("Invoke complete")

print(f"\nRun ID: {run_id}")
print("Sub-questions:", final_state["sub_questions"])
print("\nAnswer:", final_state["answer"])
print("Cited chunks:", final_state["cited_chunk_ids"])
print("Citations verified:", final_state["citations_verified"])
print("Verdict:", final_state["verdict"])
print("Critic reason:", final_state["critic_reason"])
print("Retry count:", final_state["retry_count"])
print("Memory write result:", final_state.get("memory_write_result"))
print("Memories used:", final_state.get("memories"))