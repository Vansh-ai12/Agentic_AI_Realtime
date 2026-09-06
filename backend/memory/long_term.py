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

MEMORY_SUMMARY_PROMPT = """You are a memory summarization agent. Given a user's question and the final answer they received, write a single concise sentence (under 30 words) capturing the key fact or outcome worth remembering for future conversations.

Only summarize genuinely useful, reusable facts (e.g. "User has two internship offers: X and Y" or "Project Alpha is blocked on third-party API delay"). If the interaction produced no durable fact worth remembering (e.g. it was a refusal or unresolved), respond with exactly: NONE

Respond with ONLY the summary sentence, or exactly NONE. No other text."""


def write_memory(user_id: str, user_query: str, answer: str, source_run_id: str = None) -> dict:
    response = client.chat.completions.create(
        model=MEMORY_SUMMARY_MODEL,
        messages=[
            {"role": "system", "content": MEMORY_SUMMARY_PROMPT},
            {"role": "user", "content": f"Question: {user_query}\n\nAnswer: {answer}"}
        ],
        temperature=0.1,
    )

    summary = response.choices[0].message.content.strip()

    if summary == "NONE" or not summary:
        return {"stored": False, "summary": None}

    embedding = get_embedding(summary)

    result = supabase.table("memory_long_term").insert({
        "user_id": user_id,
        "summary": summary,
        "embedding": embedding,
        "source_run_id": source_run_id
    }).execute()

    return {"stored": True, "summary": summary, "memory_id": result.data[0]["id"]}