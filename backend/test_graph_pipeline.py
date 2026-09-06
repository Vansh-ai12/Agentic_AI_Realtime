print("Starting script...")
from graph.pipeline import build_pipeline
print("Import succeeded")

pipeline = build_pipeline()
print("Pipeline built")

initial_state = {
    "user_id": "c0a65264-dc6c-4198-8e88-7c63c180d1cf",
    "original_query": "What internships have I received and what's blocking Project Alpha?",
    "run_id": None,
    "attempt_id": None,
    "retry_count": 0,
}

print("Invoking pipeline...")
final_state = pipeline.invoke(initial_state)
print("Invoke complete")

print("Sub-questions:", final_state["sub_questions"])
print("\nAnswer:", final_state["answer"])
print("Cited chunks:", final_state["cited_chunk_ids"])
print("Citations verified:", final_state["citations_verified"])
print("Verdict:", final_state["verdict"])
print("Critic reason:", final_state["critic_reason"])
print("Retry count:", final_state["retry_count"])