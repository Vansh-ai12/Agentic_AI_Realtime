import json
from utils.groq_client import groq_chat_completion

CRITIC_MODEL = "qwen/qwen3.8-27b"  

CRITIC_SYSTEM_PROMPT = """You are a critic agent reviewing an AI-generated answer before it's shown to the user.

You will receive: the original user question, the generated answer, and whether all citations were independently verified as accurate.

Approve the answer only if it:
1. Directly and completely answers the user's question
2. Is clear and well-organized
3. Had all citations verified as supported (if citations_verified is False, you should generally reject)

Respond ONLY with valid JSON in this exact format, no other text:
{"verdict": "approve", "reason": "brief explanation"}
or
{"verdict": "reject", "reason": "specific, actionable explanation of what's wrong, so the answer can be improved"}
"""

import re

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


def critique_answer(user_query: str, answer: str, citations_verified: bool, run_id: str = None, attempt_id: str = None) -> dict:
    user_message = (
        f"Original question: {user_query}\n\n"
        f"Generated answer: {answer}\n\n"
        f"Citations verified as accurate: {citations_verified}"
    )

    response = groq_chat_completion(
        model=CRITIC_MODEL,
        messages=[
            {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0.2,
        max_tokens=600,
    )

    raw_output = response.choices[0].message.content or ""
    usage = response.usage

    parsed = _extract_json(raw_output)
    if parsed:
        verdict = parsed.get("verdict", "reject")
        reason = parsed.get("reason", "")
    else:
        verdict = "reject"
        reason = "Failed to parse critic output"

    # Nuanced override: if unverified citations, check if LLM already noticed or reject with specific feedback
    if not citations_verified and verdict == "approve":
        verdict = "reject"
    try:
        print(f"[Critic] Verdict: {verdict} - {reason}")
    except UnicodeEncodeError:
        safe_msg = f"[Critic] Verdict: {verdict} - {reason}".encode("ascii", errors="replace").decode("ascii")
        print(safe_msg)

    if run_id and attempt_id:
        from utils.token_logger import log_tokens
        log_tokens(run_id, attempt_id, "critic", CRITIC_MODEL, usage.prompt_tokens, usage.completion_tokens)

    return {
        "verdict": verdict,
        "reason": reason,
        "tokens_in": usage.prompt_tokens,
        "tokens_out": usage.completion_tokens
    }