from rag.embeddings import get_embedding
from db.supabase_client import supabase

def retrieve_chunks(query: str, user_id: str, top_k: int = 5) -> list[dict]:
    query_embedding = get_embedding(query)

    result = supabase.rpc("match_chunks", {
        "query_embedding": query_embedding,
        "match_user_id": user_id,
        "match_count": top_k
    }).execute()

    return result.data