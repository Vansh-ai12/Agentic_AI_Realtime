import os
import json
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parents[1] / ".env.local"
load_dotenv(dotenv_path=env_path)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYNTHESIZER_MODEL = "openai/gpt-oss-120b"

SYNTHESIZER_SYSTEM_PROMPT = """You are an answer synthesis agent. You will be given a user's question and a list of retrieved text chunks, each with a chunk_id.

Write a clear, direct answer to the question using ONLY information present in the chunks. For every factual claim, cite the chunk_id it came from in square brackets, e.g. [chunk_id_here].

If the chunks don't contain enough information to answer the question, say so honestly instead of guessing.

Respond ONLY with valid JSON in this exact format, no other text:
{"answer": "your answer text with [chunk_id] citations inline", "cited_chunk_ids": ["id1", "id2"]}
if someone asks about Maths answer them :- "Sorry I cant answer your question as I am not trained in Maths, please ask another question."
"""


def _build_context_block(chunks: list[dict], previously_cited_ids: list[str] = None) -> str:
    previously_cited_ids = previously_cited_ids or []
    parts = []
    for c in chunks:
        if c["chunk_id"] in previously_cited_ids:
            parts.append(f"chunk_id: {c['chunk_id']}\n(already used in previous attempt — content omitted to save tokens)")
        else:
            parts.append(f"chunk_id: {c['chunk_id']}\ncontent: {c['content']}")
    return "\n\n".join(parts)


def synthesize_answer(
    user_query: str,
    chunks: list[dict],
    memories: list[dict] = None,
    run_id: str = None,
    attempt_id: str = None,
    critic_feedback: str = None,
    previous_answer: str = None,
    previous_cited_ids: list[str] = None
) -> dict:
    is_retry = critic_feedback is not None

    context_block = _build_context_block(chunks, previous_cited_ids if is_retry else None)

    memory_block = ""
    if memories:
        memory_lines = "\n".join(f"- {m['summary']}" for m in memories)
        memory_block = f"\n\nKnown facts from prior conversations (context only, not citable sources):\n{memory_lines}"

    user_message = f"Question: {user_query}{memory_block}\n\nRetrieved chunks:\n{context_block}"

    if is_retry:
        user_message += (
            f"\n\nYour previous answer was: {previous_answer}"
            f"\n\nIt was rejected for this reason — revise it to address this specifically: {critic_feedback}"
        )

    response = client.chat.completions.create(
        model=SYNTHESIZER_MODEL,
        messages=[
            {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0.2,
    )

    raw_output = response.choices[0].message.content
    usage = response.usage

    try:
        parsed = json.loads(raw_output)
        answer = parsed.get("answer", "")
        cited_chunk_ids = parsed.get("cited_chunk_ids", [])
    except (json.JSONDecodeError, AttributeError):
        answer = raw_output
        cited_chunk_ids = []

    print(f"[Synthesizer] Generated answer (retry: {is_retry}, tokens_in: {usage.prompt_tokens})")

    if run_id and attempt_id:
        from utils.token_logger import log_tokens
        log_tokens(run_id, attempt_id, "synthesizer", SYNTHESIZER_MODEL, usage.prompt_tokens, usage.completion_tokens)

    return {
        "answer": answer,
        "cited_chunk_ids": cited_chunk_ids,
        "tokens_in": usage.prompt_tokens,
        "tokens_out": usage.completion_tokens,
        "model": SYNTHESIZER_MODEL
    }