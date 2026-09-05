from rag.retrievals import retrieve_chunks

def retrieve_for_all_subquestions(sub_questions: list[str], user_id: str, top_k_per_question: int = 3) -> list[dict]:
    """Runs retrieval for each sub-question and merges results, deduping by chunk_id."""
    seen_chunk_ids = set()
    merged_chunks = []

    for sub_q in sub_questions:
        chunks = retrieve_chunks(query=sub_q, user_id=user_id, top_k=top_k_per_question)
        for chunk in chunks:
            if chunk["chunk_id"] not in seen_chunk_ids:
                seen_chunk_ids.add(chunk["chunk_id"])
                merged_chunks.append(chunk)

    return merged_chunks