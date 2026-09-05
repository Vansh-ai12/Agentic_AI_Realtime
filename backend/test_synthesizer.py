from rag.retrievals import retrieve_chunks
from agents.synthesizer import synthesize_answer

USER_ID = "c0a65264-dc6c-4198-8e88-7c63c180d1cf"
query = "What is currently blocking Project Alpha?"

chunks = retrieve_chunks(query=query, user_id=USER_ID, top_k=3)
result = synthesize_answer(query, chunks)

print("Answer:", result["answer"])
print("Cited chunks:", result["cited_chunk_ids"])
print("Tokens:", result["tokens_in"], result["tokens_out"])