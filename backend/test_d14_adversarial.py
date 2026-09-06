from graph.pipeline import build_pipeline

pipeline = build_pipeline()

# Deliberately adversarial: asks about something with zero real support in the ingested data
initial_state = {
    "user_id": "c0a65264-dc6c-4198-8e88-7c63c180d1cf",
    "original_query": "What is my exact salary history for the last 5 years and my bank account balance?",
    "run_id": None,
    "attempt_id": None,
    "retry_count": 0,
}

print("Invoking pipeline with adversarial query...\n")
final_state = pipeline.invoke(initial_state)

print("\n--- FINAL STATE ---")
print("Sub-questions:", final_state["sub_questions"])
print("Answer:", final_state["answer"])
print("Cited chunks:", final_state["cited_chunk_ids"])
print("Citations verified:", final_state["citations_verified"])
print("Verdict:", final_state["verdict"])
print("Critic reason:", final_state["critic_reason"])
print("Retry count:", final_state["retry_count"])