import time
from rag.embeddings import get_embedding

test_text = "This is a test sentence about project Alpha for embedding cache testing."

print("=== First call (expect cache MISS — slower) ===")
start = time.time()
result1 = get_embedding(test_text)
elapsed1 = time.time() - start
print(f"Time: {elapsed1:.4f}s")
print(f"Type: {type(result1)}")
print(f"Length: {len(result1)}")
print(f"First 3 values: {result1[:3]}")

print("\n=== Second call, same text (expect cache HIT — faster) ===")
start = time.time()
result2 = get_embedding(test_text)
elapsed2 = time.time() - start
print(f"Time: {elapsed2:.4f}s")
print(f"Type: {type(result2)}")
print(f"Length: {len(result2)}")
print(f"First 3 values: {result2[:3]}")

print(f"\n=== Comparison ===")
print(f"Speedup: {elapsed1 / elapsed2:.1f}x faster" if elapsed2 > 0 else "Second call was instant")
print(f"Values match: {result1 == result2}")