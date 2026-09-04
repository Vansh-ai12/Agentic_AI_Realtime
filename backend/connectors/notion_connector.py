from notion_client import Client
from rag.chunking import chunk_text
from rag.embeddings import get_embedding
from db.supabase_client import supabase

def fetch_notion_pages(access_token: str) -> list[dict]:
    notion = Client(auth=access_token)
    results = notion.search(filter={"property": "object", "value": "page"}).get("results", [])

    pages = []
    for page in results:
        page_id = page["id"]
        last_edited = page["last_edited_time"]
        title = "Untitled"
        # Try to extract a title from properties
        props = page.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title" and prop["title"]:
                title = prop["title"][0]["plain_text"]
                break

        blocks = notion.blocks.children.list(block_id=page_id).get("results", [])
        text_parts = []
        for block in blocks:
            block_type = block.get("type")
            rich_text = block.get(block_type, {}).get("rich_text", [])
            for rt in rich_text:
                text_parts.append(rt.get("plain_text", ""))

        pages.append({
            "external_id": page_id,
            "title": title,
            "raw_content": "\n".join(text_parts),
            "source_updated_at": last_edited
        })
    return pages


def ingest_notion(user_id: str, connection_id: str, access_token: str):
    pages = fetch_notion_pages(access_token)
    ingested_count = 0

    for page in pages:
        if not page["raw_content"].strip():
            continue

        # skip if already ingested and unchanged
        existing = supabase.table("documents").select("id, source_updated_at") \
            .eq("connection_id", connection_id) \
            .eq("external_id", page["external_id"]).execute()

        if existing.data and existing.data[0]["source_updated_at"] == page["source_updated_at"]:
            continue  # no change since last sync

        doc_result = supabase.table("documents").upsert({
            "user_id": user_id,
            "connection_id": connection_id,
            "source": "notion",
            "external_id": page["external_id"],
            "title": page["title"],
            "raw_content": page["raw_content"],
            "source_updated_at": page["source_updated_at"]
        }, on_conflict="connection_id,external_id").execute()

        document_id = doc_result.data[0]["id"]

        # clear old chunks before re-inserting (in case content changed)
        supabase.table("chunks").delete().eq("document_id", document_id).execute()

        chunks = chunk_text(page["raw_content"])
        for idx, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            supabase.table("chunks").insert({
                "document_id": document_id,
                "chunk_index": idx,
                "content": chunk,
                "embedding": embedding
            }).execute()

        ingested_count += 1

    supabase.table("connections").update({"last_synced_at": "now()"}) \
        .eq("id", connection_id).execute()

    return {"pages_ingested": ingested_count}