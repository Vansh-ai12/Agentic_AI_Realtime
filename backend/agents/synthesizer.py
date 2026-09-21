import json
import re
from utils.groq_client import groq_chat_completion

def _extract_json(text: str) -> dict:
    if not text:
        return {}
    cleaned = text.strip()
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if match:
            cleaned = match.group(1).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return {}

SYNTHESIZER_MODEL = "qwen/qwen3.8-27b" 

SYNTHESIZER_SYSTEM_PROMPT = """You are an answer synthesis agent. You will be given a user's question and a list of retrieved text chunks, each with a chunk_id.

Write a clear, direct answer to the question using ONLY information present in the chunks.
Guidelines:
1. For every factual claim you make, link it to the chunk_id it came from. Include inline [chunk_id] citations in the answer text, and also provide the list of explicit claim-to-chunk mappings.
2. Only cite a chunk when the chunk explicitly contains the positive evidence supporting that claim. Do NOT cite a chunk to support a statement that information is missing or absent.
3. Always use the full, exact chunk_id (e.g. [0a5c3941-5d6d-4d78-becb-01a8d4008b35]). Never shorten, truncate, or abbreviate chunk IDs.
4. If the chunks don't contain enough information to answer part or all of the question, state so honestly without inventing citations.

Respond ONLY with valid JSON in this exact format, no other text:
{
  "answer": "your answer text with [chunk_id] citations inline",
  "citations": [
    {"claim": "specific factual statement from the answer", "chunk_id": "exact_chunk_id_here"}
  ],
  "cited_chunk_ids": ["exact_chunk_id_here"]
}
"""


def _build_context_block(chunks: list[dict], is_retry: bool = False, previously_cited_ids: list[str] = None) -> str:
    # If retry and we have lots of chunks, prioritize the ones that were cited, but keep their content!
    parts = []
    for c in chunks:
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

    context_block = _build_context_block(chunks, is_retry=is_retry, previously_cited_ids=previous_cited_ids)

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

    response = groq_chat_completion(
        model=SYNTHESIZER_MODEL,
        messages=[
            {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0.2,
        max_tokens=1000,
    )

    raw_output = response.choices[0].message.content or ""
    usage = response.usage

    parsed = _extract_json(raw_output)
    if parsed:
        answer = parsed.get("answer", "")
        citations = parsed.get("citations", [])
        cited_chunk_ids = parsed.get("cited_chunk_ids", [])
        
        # If cited_chunk_ids is empty but citations is populated, infer cited_chunk_ids
        if not cited_chunk_ids and citations:
            cited_chunk_ids = list(dict.fromkeys(c.get("chunk_id") for c in citations if c.get("chunk_id")))
    else:
        answer = raw_output
        citations = []
        cited_chunk_ids = []

    print(f"[Synthesizer] Generated answer (retry: {is_retry}, tokens_in: {usage.prompt_tokens}, tokens_out: {usage.completion_tokens})")

    if run_id and attempt_id:
        from utils.token_logger import log_tokens
        log_tokens(run_id, attempt_id, "synthesizer", SYNTHESIZER_MODEL, usage.prompt_tokens, usage.completion_tokens)

    return {
        "answer": answer,
        "citations": citations,
        "cited_chunk_ids": cited_chunk_ids,
        "tokens_in": usage.prompt_tokens,
        "tokens_out": usage.completion_tokens,
        "model": SYNTHESIZER_MODEL
    }