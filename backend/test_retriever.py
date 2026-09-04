from rag.retrievals import retrieve_chunks

results = retrieve_chunks(
    query="internship opportunities matching my profile",
    user_id="c0a65264-dc6c-4198-8e88-7c63c180d1cf"  # your user_id
)

for r in results:
    print(f"[{r['similarity']:.3f}] {r['content'][:100]}")