from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")  # loads once, 384-dim output

def get_embedding(text: str) -> list[float]:
    return _model.encode(text).tolist()