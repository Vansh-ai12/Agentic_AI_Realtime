import os
import json
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parents[1] / ".env.local"
load_dotenv(dotenv_path=env_path)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CRITIC_MODEL = "openai/gpt-oss-20b"

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

def critique_answer(user_query: str, answer: str, citations_verified: bool, run_id: str = None, attempt_id: str = None) -> dict:
    user_message = (
        f"Original question: {user_query}\n\n"
        f"Generated answer: {answer}\n\n"
        f"Citations verified as accurate: {citations_verified}"
    )

    response = client.chat.completions.create(
        model=CRITIC_MODEL,
        messages=[
            {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0.2,
    )

    raw_output = response.choices[0].message.content
    usage = response.usage

    try:
        parsed = json.loads(raw_output)
        verdict = parsed.get("verdict", "reject")
        reason = parsed.get("reason", "")
    except (json.JSONDecodeError, AttributeError):
        verdict = "reject"
        reason = "Failed to parse critic output"

    if run_id and attempt_id:
        from utils.token_logger import log_tokens
        log_tokens(run_id, attempt_id, "critic", CRITIC_MODEL, usage.prompt_tokens, usage.completion_tokens)

    return {
        "verdict": verdict,
        "reason": reason,
        "tokens_in": usage.prompt_tokens,
        "tokens_out": usage.completion_tokens
    }