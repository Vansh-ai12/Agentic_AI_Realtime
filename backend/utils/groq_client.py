"""
Shared Groq client with exponential backoff for rate-limit (429) handling.

Usage:
    from utils.groq_client import groq_chat_completion

    response = groq_chat_completion(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.2,
    )
"""

import os
import time
import logging
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

_here = Path(__file__).resolve()
for _env in (_here.parents[2] / ".env.local", _here.parents[1] / ".env.local", Path.cwd() / ".env.local"):
    if _env.exists():
        load_dotenv(dotenv_path=_env, override=False)

logger = logging.getLogger(__name__)

# Shared client instance — reused across all agents
_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Retry configuration
MAX_RETRIES = 5
BASE_DELAY_SECONDS = 1.0       # First retry waits 1s
MAX_DELAY_SECONDS = 60.0       # Cap at 60s
BACKOFF_MULTIPLIER = 2.0       # 1s → 2s → 4s → 8s → 16s


def groq_chat_completion(
    model: str,
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int = None,
    **kwargs,
):
    """
    Wrapper around Groq chat completions with exponential backoff on 429s.

    Returns the full Groq response object (same as client.chat.completions.create()).
    Raises the last exception if all retries are exhausted.
    """
    delay = BASE_DELAY_SECONDS

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            call_kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                **kwargs,
            }
            if max_tokens is not None:
                call_kwargs["max_tokens"] = max_tokens

            response = _client.chat.completions.create(**call_kwargs)
            return response

        except Exception as e:
            error_str = str(e)
            is_rate_limit = (
                "429" in error_str
                or "rate_limit" in error_str.lower()
                or "rate limit" in error_str.lower()
                or "too many requests" in error_str.lower()
            )

            if not is_rate_limit or attempt == MAX_RETRIES:
                # Non-rate-limit error or final retry — propagate
                if is_rate_limit:
                    logger.error(
                        f"[GroqClient] Rate limit exhausted after {MAX_RETRIES} retries "
                        f"(model={model}). Last error: {error_str}"
                    )
                raise

            # Parse Retry-After header if available in the error
            retry_after = _parse_retry_after(e)
            wait_time = retry_after if retry_after else delay

            logger.warning(
                f"[GroqClient] Rate limited (429) on attempt {attempt}/{MAX_RETRIES}. "
                f"Waiting {wait_time:.1f}s before retry. Model: {model}"
            )
            print(
                f"[GroqClient] Rate limited — waiting {wait_time:.1f}s "
                f"(attempt {attempt}/{MAX_RETRIES}, model={model})"
            )

            time.sleep(wait_time)
            delay = min(delay * BACKOFF_MULTIPLIER, MAX_DELAY_SECONDS)


def _parse_retry_after(exception) -> float | None:
    """
    Attempt to extract a Retry-After value from a Groq API error.
    Returns seconds to wait, or None if not parseable.
    """
    try:
        # Groq Python SDK wraps HTTP errors; try to get the response
        if hasattr(exception, "response") and exception.response is not None:
            retry_after = exception.response.headers.get("retry-after")
            if retry_after:
                return float(retry_after)
        # Also try parsing from the error message string
        error_str = str(exception)
        if "retry after" in error_str.lower():
            # Try to find a number after "retry after"
            import re
            match = re.search(r"retry\s+after\s+(\d+\.?\d*)", error_str, re.IGNORECASE)
            if match:
                return float(match.group(1))
    except (ValueError, AttributeError, TypeError):
        pass
    return None
