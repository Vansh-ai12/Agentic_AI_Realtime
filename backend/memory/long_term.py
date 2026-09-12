import os
import json
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path
from db.supabase_client import supabase
from rag.embeddings import get_embedding

env_path = Path(__file__).resolve().parents[1] / ".env.local"
load_dotenv(dotenv_path=env_path)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MEMORY_SUMMARY_MODEL = "openai/gpt-oss-20b"
DEDUP_THRESHOLD = 0.85

MEMORY_SUMMARY_PROMPT = """You are a memory summarization agent. Given a user's question and the final answer they received, write a single concise sentence (under 30 words) capturing the key fact or outcome worth remembering for future conversations.

Only summarize genuinely useful, reusable facts. If the interaction produced no durable fact worth remembering (e.g. it was a refusal or unresolved), respond with the JSON: {"summary": null, "memory_type": null}

Otherwise, also classify the fact into one of three types:
- "status": a current-state fact likely to change over time (e.g. a project blocker, an in-progress task)
- "fact": a stable fact unlikely to change soon (e.g. an offer received, a decision made)
- "preference": something about how the user likes things done

Respond ONLY with valid JSON in this exact format, no other text:
{"summary": "your summary sentence", "memory_type": "fact"}
"""


def write_memory(user_id: str, user_query: str, answer: str, source_run_id: str = None) -> dict:
    response = client.chat.completions.create(
        model=MEMORY_SUMMARY_MODEL,
        messages=[
            {"role": "system", "content": MEMORY_SUMMARY_PROMPT},
            {"role": "user", "content": f"Question: {user_query}\n\nAnswer: {answer}"}
        ],
        temperature=0.1,
    )

    raw_output = response.choices[0].message.content
    print(f"[Memory Writer] Raw LLM output: {raw_output[:100]}...")

    try:
        parsed = json.loads(raw_output)
        summary = parsed.get("summary")
        memory_type = parsed.get("memory_type")
    except (json.JSONDecodeError, AttributeError):
        summary = None
        memory_type = None

    if not summary:
        return {"stored": False, "action": "none", "summary": None}

    embedding = get_embedding(summary)

    # Check for an existing similar memory before inserting
    existing = supabase.rpc("match_memories", {
        "query_embedding": embedding,
        "match_user_id": user_id,
        "similarity_threshold": DEDUP_THRESHOLD
    }).execute()

    if existing.data:
        # Update the existing similar memory instead of creating a duplicate
        match = existing.data[0]
        supabase.table("memory_long_term").update({
            "summary": summary,
            "embedding": embedding,
            "memory_type": memory_type,
            "source_run_id": source_run_id
        }).eq("id", match["memory_id"]).execute()

        return {
            "stored": True,
            "action": "updated",
            "summary": summary,
            "memory_type": memory_type,
            "memory_id": match["memory_id"],
            "previous_summary": match["summary"]
        }

    # No similar memory found — insert new
    result = supabase.table("memory_long_term").insert({
        "user_id": user_id,
        "summary": summary,
        "embedding": embedding,
        "memory_type": memory_type,
        "source_run_id": source_run_id
    }).execute()

    return {
        "stored": True,
        "action": "inserted",
        "summary": summary,
        "memory_type": memory_type,
        "memory_id": result.data[0]["id"]
    }


def read_relevant_memories(user_id: str, query: str, top_k: int = 3, min_similarity: float = 0.3) -> list[dict]:
    query_embedding = get_embedding(query)

    result = supabase.rpc("match_memories", {
        "query_embedding": query_embedding,
        "match_user_id": user_id,
        "similarity_threshold": min_similarity
    }).execute()

    return result.data[:top_k] if result.data else []