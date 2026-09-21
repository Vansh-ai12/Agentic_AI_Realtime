import re
import json
from utils.groq_client import groq_chat_completion

VERIFIER_MODEL = "qwen/qwen3.8-27b"  
VERIFIER_SYSTEM_PROMPT = """You are a citation verification agent. You will be given a specific claim made in an answer and the source chunk it cites.

Your job: determine whether the source chunk directly supports or reasonably entails the claim.
Be fair and objective: minor differences in phrasing or obvious summaries are acceptable, but factual inaccuracies, hallucinated numbers/names, or claims not mentioned in the chunk must be rejected.

Respond ONLY with valid JSON in this exact format, no other text:
{"supported": true, "reason": "brief explanation"}
or
{"supported": false, "reason": "brief explanation of what is unsupported or missing"}
"""

BATCH_VERIFIER_SYSTEM_PROMPT = """You are a citation verification agent. You will be given multiple claims made in an answer and their corresponding source chunks.

Your job: determine whether each source chunk directly supports or reasonably entails its corresponding claim.
Be fair and objective: minor differences in phrasing or obvious summaries are acceptable, but factual inaccuracies, hallucinated numbers/names, or claims not mentioned in the chunk must be rejected.

For each citation, evaluate independently and return a verdict.

Respond ONLY with valid JSON in this exact format, no other text:
{
  "citation_results": [
    {"citation_index": 0, "supported": true, "reason": "brief explanation"},
    {"citation_index": 1, "supported": false, "reason": "brief explanation of what is unsupported or missing"},
    ...
  ]
}

Evaluate each citation independently - do not let one citation's verdict influence another.
"""

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


def verify_citation(claim: str, chunk_content: str, run_id: str = None, attempt_id: str = None) -> dict:
    user_message = f"Claim: {claim}\n\nSource chunk content:\n{chunk_content}"

    response = groq_chat_completion(
        model=VERIFIER_MODEL,
        messages=[
            {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0.1,
        max_tokens=600,
    )

    raw_output = response.choices[0].message.content or ""
    usage = response.usage

    parsed = _extract_json(raw_output)
    if parsed:
        supported = parsed.get("supported", False)
        reason = parsed.get("reason", "")
    else:
        supported = False
        reason = f"Failed to parse verifier output: {raw_output[:120]}"

    if run_id and attempt_id:
        from utils.token_logger import log_tokens
        # Map to valid agent_role in token_logs table
        log_tokens(run_id, attempt_id, "retriever", VERIFIER_MODEL, usage.prompt_tokens, usage.completion_tokens)

    return {
        "supported": supported,
        "reason": reason,
        "tokens_in": usage.prompt_tokens,
        "tokens_out": usage.completion_tokens
    }

def _extract_claim_for_citation(answer: str, chunk_id: str) -> str:
    """Extracts only the specific sentence containing this chunk_id citation."""
    sentences = re.split(r'(?<=[.!?])\s+', answer)
    matching = [s.strip() for s in sentences if chunk_id in s]
    return " ".join(matching) if matching else answer


def _resolve_chunk_id(chunk_id: str, chunk_lookup: dict) -> str | None:
    if not chunk_id:
        return None
    if chunk_id in chunk_lookup:
        return chunk_id
    for cid in chunk_lookup:
        if cid.startswith(chunk_id) or chunk_id.startswith(cid):
            return cid
    return None


def verify_all_citations(synthesizer_result: dict, chunks: list[dict], run_id: str = None, attempt_id: str = None) -> dict:
    """Verifies every cited chunk against the specific claim it was cited for."""
    chunk_lookup = {c["chunk_id"]: c["content"] for c in chunks}
    results = []
    
    citations = synthesizer_result.get("citations", [])
    cited_chunk_ids = synthesizer_result.get("cited_chunk_ids", [])
    answer = synthesizer_result.get("answer", "")

    if citations and isinstance(citations, list):
        for item in citations:
            raw_chunk_id = item.get("chunk_id")
            claim = item.get("claim", "")
            if not raw_chunk_id:
                continue
            resolved_id = _resolve_chunk_id(raw_chunk_id, chunk_lookup)
            if not resolved_id:
                results.append({
                    "chunk_id": raw_chunk_id,
                    "claim": claim,
                    "supported": False,
                    "reason": f"Cited chunk_id '{raw_chunk_id}' not found in retrieved chunks"
                })
                continue
            
            chunk_content = chunk_lookup[resolved_id]
            verification = verify_citation(claim or answer, chunk_content, run_id, attempt_id)
            results.append({
                "chunk_id": resolved_id,
                "claim": claim,
                **verification
            })
    elif cited_chunk_ids:
        for raw_chunk_id in cited_chunk_ids:
            resolved_id = _resolve_chunk_id(raw_chunk_id, chunk_lookup)
            if not resolved_id:
                results.append({
                    "chunk_id": raw_chunk_id,
                    "supported": False,
                    "reason": f"Cited chunk_id '{raw_chunk_id}' not found in retrieved chunks"
                })
                continue

            chunk_content = chunk_lookup[resolved_id]
            claim = _extract_claim_for_citation(answer, raw_chunk_id)
            verification = verify_citation(claim, chunk_content, run_id, attempt_id)
            results.append({
                "chunk_id": resolved_id,
                "claim": claim,
                **verification
            })

    # If no citations were made (e.g. refusal or no info in chunks), all_supported is True (nothing unsupported)
    if not results:
        all_supported = True
    else:
        all_supported = all(r["supported"] for r in results)

    return {
        "all_supported": all_supported,
        "details": results
    }


def verify_all_citations_batch(synthesizer_result: dict, chunks: list[dict], run_id: str = None, attempt_id: str = None) -> dict:
    """
    Batch version: Verifies all cited chunks in a SINGLE LLM call.
    This reduces API calls from N citations to 1 call, regardless of citation count.
    
    Args:
        synthesizer_result: Dict with 'answer', 'citations', and 'cited_chunk_ids'
        chunks: List of chunk dictionaries with 'chunk_id' and 'content'
        run_id: Optional run ID for token logging
        attempt_id: Optional attempt ID for token logging
    
    Returns:
        Dict with:
        - all_supported: bool (True if all citations pass)
        - details: List of per-citation verification results
    """
    chunk_lookup = {c["chunk_id"]: c["content"] for c in chunks}
    results = []
    
    citations = synthesizer_result.get("citations", [])
    cited_chunk_ids = synthesizer_result.get("cited_chunk_ids", [])
    answer = synthesizer_result.get("answer", "")
    
    # Build list of citations to verify
    citations_to_verify = []
    
    if citations and isinstance(citations, list):
        for idx, item in enumerate(citations):
            raw_chunk_id = item.get("chunk_id")
            claim = item.get("claim", "")
            if not raw_chunk_id:
                continue
            resolved_id = _resolve_chunk_id(raw_chunk_id, chunk_lookup)
            if not resolved_id:
                results.append({
                    "chunk_id": raw_chunk_id,
                    "claim": claim,
                    "supported": False,
                    "reason": f"Cited chunk_id '{raw_chunk_id}' not found in retrieved chunks"
                })
                continue
            citations_to_verify.append({
                "index": idx,
                "chunk_id": resolved_id,
                "claim": claim or answer,
                "chunk_content": chunk_lookup[resolved_id]
            })
    elif cited_chunk_ids:
        for idx, raw_chunk_id in enumerate(cited_chunk_ids):
            resolved_id = _resolve_chunk_id(raw_chunk_id, chunk_lookup)
            if not resolved_id:
                results.append({
                    "chunk_id": raw_chunk_id,
                    "supported": False,
                    "reason": f"Cited chunk_id '{raw_chunk_id}' not found in retrieved chunks"
                })
                continue
            claim = _extract_claim_for_citation(answer, raw_chunk_id)
            citations_to_verify.append({
                "index": idx,
                "chunk_id": resolved_id,
                "claim": claim,
                "chunk_content": chunk_lookup[resolved_id]
            })
    
    # If no citations to verify (all were missing), return early
    if not citations_to_verify:
        all_supported = all(r["supported"] for r in results) if results else True
        return {
            "all_supported": all_supported,
            "details": results
        }
    
    # If only 1 citation, use the original single-call function (no benefit to batching)
    if len(citations_to_verify) == 1:
        citation = citations_to_verify[0]
        verification = verify_citation(
            citation["claim"],
            citation["chunk_content"],
            run_id,
            attempt_id
        )
        results.append({
            "chunk_id": citation["chunk_id"],
            "claim": citation["claim"],
            **verification
        })
        return {
            "all_supported": verification["supported"],
            "details": results
        }
    
    # Build batch message for 2+ citations
    batch_claims = []
    for citation in citations_to_verify:
        batch_claims.append(f"Citation {citation['index']}: {citation['claim']}\nSource chunk: {citation['chunk_content']}")
    
    batch_input = "\n\n---\n\n".join(batch_claims)
    
    try:
        response = groq_chat_completion(
            model=VERIFIER_MODEL,
            messages=[
                {"role": "system", "content": BATCH_VERIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": batch_input}
            ],
            temperature=0.1,
            max_tokens=1200,
        )
        
        raw_output = response.choices[0].message.content or ""
        usage = response.usage
        
        parsed = _extract_json(raw_output)
        if parsed:
            citation_results = parsed.get("citation_results", [])
            
            # Map batch results back to citations
            for batch_result in citation_results:
                batch_index = batch_result.get("citation_index")
                if batch_index < len(citations_to_verify):
                    citation = citations_to_verify[batch_index]
                    results.append({
                        "chunk_id": citation["chunk_id"],
                        "claim": citation["claim"],
                        "supported": batch_result.get("supported", False),
                        "reason": batch_result.get("reason", ""),
                        "tokens_in": usage.prompt_tokens // len(citations_to_verify),  # Approximate split
                        "tokens_out": usage.completion_tokens // len(citations_to_verify)
                    })
        else:
            # Parse error - fail closed, mark all as unsupported
            for citation in citations_to_verify:
                results.append({
                    "chunk_id": citation["chunk_id"],
                    "claim": citation["claim"],
                    "supported": False,
                    "reason": f"Failed to parse batch verifier output: {raw_output[:120]}",
                    "tokens_in": usage.prompt_tokens // len(citations_to_verify),
                    "tokens_out": usage.completion_tokens // len(citations_to_verify)
                })
        
        if run_id and attempt_id:
            from utils.token_logger import log_tokens
            log_tokens(run_id, attempt_id, "retriever", VERIFIER_MODEL, usage.prompt_tokens, usage.completion_tokens)
        
    except Exception as e:
        # Error - fail closed, mark all as unsupported
        for citation in citations_to_verify:
            results.append({
                "chunk_id": citation["chunk_id"],
                "claim": citation["claim"],
                "supported": False,
                "reason": f"Batch verifier error: {str(e)}",
                "tokens_in": 0,
                "tokens_out": 0
            })
    
    # Determine overall supported status
    all_supported = all(r["supported"] for r in results) if results else True
    
    return {
        "all_supported": all_supported,
        "details": results
    }