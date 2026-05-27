"""
tools/groq_client.py
--------------------
Thin wrapper around the official Groq Python SDK.

WHY A WRAPPER?
--------------
If you called the Groq SDK directly in main.py, every change to model name,
temperature, or retry logic would require editing the orchestration file.
Wrapping it here means:
- main.py only calls `call_groq(prompt)`.
- You can swap Groq for OpenAI or a local Ollama model by editing one file.
- You can add retry logic, caching, or rate-limit handling in one place.

DEVELOPER FRICTION HERE:
- The Groq free tier has per-minute and per-day token limits.
  You will hit them if you run the agent many times quickly.
  The error looks like: "groq.RateLimitError: 429..."
  Fix: wait 60 seconds and retry, or add exponential backoff.
- `llama-3.3-70b-versatile` is a large model. If you need faster responses
  during development, try `llama-3.1-8b-instant` temporarily.
"""

import time
from typing import Optional

from utils.logger import get_logger
from utils.helpers import load_env_key

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Model configuration – change this in ONE place if you switch models.
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TEMPERATURE = 0.3      # Lower = more factual; higher = more creative.
DEFAULT_MAX_TOKENS = 2048      # Generous ceiling for email-length outputs.
MAX_RETRIES = 2                # How many times to retry on transient errors.
RETRY_WAIT_SECONDS = 5         # Seconds to wait between retries.


def call_groq(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """
    Send a prompt to the Groq API and return the assistant's reply.

    This function handles:
    - API key loading from environment.
    - Basic retry logic for transient network errors.
    - Logging of request / response metadata (NOT the full text, to keep
      logs readable; use DEBUG level for that).

    Args:
        prompt:      The full prompt string to send.
        model:       Groq model identifier.
        temperature: Sampling temperature (0.0–1.0).
        max_tokens:  Maximum tokens in the response.

    Returns:
        The assistant's reply as a plain string.

    Raises:
        EnvironmentError: If GROQ_API_KEY is missing.
        RuntimeError: If the API call fails after all retries.
    """
    api_key = load_env_key("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. "
            "Copy .env.example to .env and add your key."
        )

    try:
        from groq import Groq
    except ImportError:
        raise ImportError(
            "groq package is not installed. Run: pip install groq"
        )

    client = Groq(api_key=api_key)

    logger.info("Calling Groq API | model=%s | temp=%.1f | max_tokens=%d",
                model, temperature, max_tokens)
    logger.debug("Prompt length: %d chars", len(prompt))

    last_error: Optional[Exception] = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional research analyst and writer. "
                            "Be precise, factual, and well-structured."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Extract the text from the first choice.
            reply = response.choices[0].message.content.strip()

            logger.info(
                "Groq response received | attempt=%d | reply_length=%d chars",
                attempt, len(reply),
            )
            logger.debug("Reply preview: %.200s", reply)

            return reply

        except Exception as exc:
            last_error = exc
            logger.warning(
                "Groq API call failed (attempt %d/%d): %s",
                attempt, MAX_RETRIES, exc,
            )
            if attempt < MAX_RETRIES:
                logger.info("Retrying in %d seconds…", RETRY_WAIT_SECONDS)
                time.sleep(RETRY_WAIT_SECONDS)

    raise RuntimeError(
        f"Groq API failed after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )
