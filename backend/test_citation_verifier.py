from rag.retrievals import retrieve_chunks
from agents.synthesizer import synthesize_answer
from agents.citation_verifier import verify_all_citations

USER_ID = "c0a65264-dc6c-4198-8e88-7c63c180d1cf"
query = "What is currently blocking Project Alpha?"

chunks = retrieve_chunks(query=query, user_id=USER_ID, top_k=3)
synth_result = synthesize_answer(query, chunks)

print("Answer:", synth_result["answer"])
print("Cited:", synth_result["cited_chunk_ids"])

verification = verify_all_citations(synth_result, chunks)
print("\nVerification result:")
print(verification)