from agents.planner import plan_query
from agents.retrieval_orchestrator import retrieve_for_all_subquestions
from agents.synthesizer import synthesize_answer
from agents.citation_verifier import verify_all_citations
from agents.critic import critique_answer

USER_ID = "c0a65264-dc6c-4198-8e88-7c63c180d1cf"
ORIGINAL_QUERY = "What internships have I received and what's blocking Project Alpha?"

# 1. Planner splits the compound question
plan_result = plan_query(ORIGINAL_QUERY)
print("Sub-questions:", plan_result["sub_questions"])

# 2. Orchestrator retrieves + merges + dedupes chunks across all sub-questions
merged_chunks = retrieve_for_all_subquestions(plan_result["sub_questions"], user_id=USER_ID)
print(f"\nMerged chunks ({len(merged_chunks)} total, deduped):")
for c in merged_chunks:
    print(f"  [{c['similarity']:.3f}] {c['content'][:70]}")

# 3. Synthesizer answers the ORIGINAL question using all merged chunks
synth_result = synthesize_answer(ORIGINAL_QUERY, merged_chunks)
print("\nFinal Answer:", synth_result["answer"])
print("Cited chunks:", synth_result["cited_chunk_ids"])

verification = verify_all_citations(synth_result, merged_chunks)
print("\nCitation verification:")
for detail in verification["details"]:
    print(f"  {detail['chunk_id']}: supported={detail['supported']} — {detail['reason']}")
print(f"\nAll citations supported: {verification['all_supported']}")


critic_result = critique_answer(ORIGINAL_QUERY, synth_result["answer"], verification["all_supported"])
print("\nCritic verdict:", critic_result["verdict"])
print("Critic reason:", critic_result["reason"])