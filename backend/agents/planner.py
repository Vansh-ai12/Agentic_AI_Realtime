import os
import json
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parents[1] / ".env.local"
load_dotenv(dotenv_path=env_path)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PLANNER_MODEL = "openai/gpt-oss-20b"

PLANNER_SYSTEM_PROMPT = """You are a query planning agent. Given a user's question, break it down into 1-4 focused sub-questions that, together, would let a retrieval system find all the information needed to answer the original question.

If the question is already simple and specific, return just one sub-question (the original, possibly cleaned up).

Respond ONLY with valid JSON in this exact format, no other text:
{"sub_questions": ["question 1", "question 2"]}
"""

def plan_query(user_query: str, run_id: str = None, attempt_id: str = None) -> dict:
    response = client.chat.completions.create(
        model=PLANNER_MODEL,
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ],
        temperature=0.3,
    )

    raw_output = response.choices[0].message.content
    usage = response.usage

    try:
        parsed = json.loads(raw_output)
        sub_questions = parsed.get("sub_questions", [user_query])
    except (json.JSONDecodeError, AttributeError):
        sub_questions = [user_query]

    if run_id and attempt_id:
        from utils.token_logger import log_tokens
        log_tokens(run_id, attempt_id, "planner", PLANNER_MODEL, usage.prompt_tokens, usage.completion_tokens)

    return {
        "sub_questions": sub_questions,
        "tokens_in": usage.prompt_tokens,
        "tokens_out": usage.completion_tokens,
        "model": PLANNER_MODEL
    }