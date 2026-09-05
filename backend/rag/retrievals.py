from rag.embeddings import get_embedding
from db.supabase_client import supabase

DEDUP_SIMILARITY_THRESHOLD = 0.95  

def retrieve_chunks(query: str, user_id: str, top_k: int = 5) -> list[dict]:
    query_embedding = get_embedding(query)

    
    result = supabase.rpc("match_chunks", {
        "query_embedding": query_embedding,
        "match_user_id": user_id,
        "match_count": top_k * 3
    }).execute()

    candidates = result.data
    deduped = _dedup_chunks(candidates)
    return deduped[:top_k]


def _dedup_chunks(chunks: list[dict]) -> list[dict]:
    """Drop chunks whose content is a near-exact match of one already kept."""
    kept = []
    seen_content = []

    for chunk in chunks:
        content_normalized = " ".join(chunk["content"].split()).lower()
        is_duplicate = any(
            _text_similarity(content_normalized, seen) > DEDUP_SIMILARITY_THRESHOLD
            for seen in seen_content
        )
        if not is_duplicate:
            kept.append(chunk)
            seen_content.append(content_normalized)

    return kept


def _text_similarity(a: str, b: str) -> float:
    """Cheap overlap-based similarity — good enough for catching near-identical text."""
    if a == b:
        return 1.0
    set_a, set_b = set(a.split()), set(b.split())
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union