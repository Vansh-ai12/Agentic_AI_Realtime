import hashlib
import ast
from sentence_transformers import SentenceTransformer
from db.supabase_client import supabase

_model = SentenceTransformer("all-MiniLM-L6-v2")

def _hash_content(text: str) -> str:
    normalized = " ".join(text.split()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def get_embedding(text: str) -> list[float]:
    content_hash = _hash_content(text)

    cached = supabase.table("embedding_cache").select("embedding") \
        .eq("content_hash", content_hash).execute()

    if cached.data:
        raw = cached.data[0]["embedding"]
        if isinstance(raw, str):
            return ast.literal_eval(raw)  # parse "[-0.02,0.006,...]" into a real list
        return raw  # already a list, return as-is

    embedding = _model.encode(text).tolist()

    supabase.table("embedding_cache").insert({
        "content_hash": content_hash,
        "embedding": embedding
    }).execute()

    return embedding