import os
import json
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path
import re

env_path = Path(__file__).resolve().parents[1] / ".env.local"
load_dotenv(dotenv_path=env_path)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

VERIFIER_MODEL = "openai/gpt-oss-20b"

VERIFIER_SYSTEM_PROMPT = """You are a citation verification agent. You will be given an answer text and the specific source chunk it cites.

Your job: determine whether the source chunk actually supports the claims made in the answer. Be strict — the chunk must genuinely contain the information, not just share related topics or keywords.

Respond ONLY with valid JSON in this exact format, no other text:
{"supported": true, "reason": "brief explanation"}
or
{"supported": false, "reason": "brief explanation of what's missing or unsupported"}
"""

def verify_citation(answer: str, chunk_content: str, run_id: str = None, attempt_id: str = None) -> dict:
    user_message = f"Answer: {answer}\n\nSource chunk content:\n{chunk_content}"

    response = client.chat.completions.create(
        model=VERIFIER_MODEL,
        messages=[
            {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0.1,
    )

    raw_output = response.choices[0].message.content
    usage = response.usage

    try:
        parsed = json.loads(raw_output)
        supported = parsed.get("supported", False)
        reason = parsed.get("reason", "")
    except (json.JSONDecodeError, AttributeError):
        supported = False
        reason = "Failed to parse verifier output"

    if run_id and attempt_id:
        from utils.token_logger import log_tokens
        log_tokens(run_id, attempt_id, "citation_verifier", VERIFIER_MODEL, usage.prompt_tokens, usage.completion_tokens)

    return {
        "supported": supported,
        "reason": reason,
        "tokens_in": usage.prompt_tokens,
        "tokens_out": usage.completion_tokens
    }

def _extract_claim_for_citation(answer: str, chunk_id: str) -> str:
    """Extracts the sentence(s) containing this specific chunk_id citation."""
    sentences = re.split(r'(?<=[.!?])\s+', answer)
    matching = [s for s in sentences if chunk_id in s]
    return " ".join(matching) if matching else answer  # fallback to full answer if not found


def verify_all_citations(synthesizer_result: dict, chunks: list[dict], run_id: str = None, attempt_id: str = None) -> dict:
    """Verifies every cited chunk_id against the SPECIFIC claim it was cited for, not the whole answer."""
    chunk_lookup = {c["chunk_id"]: c["content"] for c in chunks}
    results = []

    for chunk_id in synthesizer_result["cited_chunk_ids"]:
        chunk_content = chunk_lookup.get(chunk_id)
        if chunk_content is None:
            results.append({"chunk_id": chunk_id, "supported": False, "reason": "Cited chunk_id not found in retrieved chunks"})
            continue

        claim = _extract_claim_for_citation(synthesizer_result["answer"], chunk_id)
        verification = verify_citation(claim, chunk_content, run_id, attempt_id)
        results.append({"chunk_id": chunk_id, **verification})

    all_supported = all(r["supported"] for r in results) if results else False

    return {
        "all_supported": all_supported,
        "details": results
    }