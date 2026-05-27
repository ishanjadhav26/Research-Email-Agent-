"""
utils/helpers.py
----------------
Shared utility functions used across the project.

Keeping generic helpers here prevents circular imports and makes
it easy to unit-test them in isolation.
"""

import os
from pathlib import Path
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def load_env_key(key_name: str) -> Optional[str]:
    """
    Read an environment variable and return its value.

    Returns None (instead of raising) so the caller can decide whether
    to abort, fall back, or log a warning. This avoids cryptic KeyError
    tracebacks for end-users.

    Args:
        key_name: The name of the environment variable (e.g. "GROQ_API_KEY").

    Returns:
        The value string, or None if missing / empty.
    """
    value = os.environ.get(key_name, "").strip()
    if not value:
        logger.warning("Environment variable '%s' is missing or empty.", key_name)
        return None
    logger.debug("Environment variable '%s' loaded successfully.", key_name)
    return value


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

def load_prompt(filename: str) -> str:
    """
    Load a prompt template from the prompts/ directory.

    Storing prompts in .txt files (not hardcoded strings) means:
    - Non-engineers can edit them without touching Python.
    - You can diff prompt changes in version control.
    - It's trivial to A/B test different prompt versions.

    Args:
        filename: File name inside the prompts/ directory (e.g. "research_prompt.txt").

    Returns:
        The raw prompt string.

    Raises:
        FileNotFoundError: If the prompt file doesn't exist.
        IOError: If the file can't be read.
    """
    root = Path(__file__).resolve().parent.parent
    prompt_path = root / "prompts" / filename

    logger.debug("Loading prompt from: %s", prompt_path)

    if not prompt_path.exists():
        logger.error("Prompt file not found: %s", prompt_path)
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    try:
        text = prompt_path.read_text(encoding="utf-8")
        logger.debug("Prompt '%s' loaded (%d chars).", filename, len(text))
        return text
    except IOError as exc:
        logger.error("Failed to read prompt file '%s': %s", filename, exc)
        raise


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def save_output(content: str, filename: str = "latest_email.txt") -> Path:
    """
    Save text content to the outputs/ directory.

    Args:
        content:  The text to write.
        filename: Target filename inside outputs/ (default: latest_email.txt).

    Returns:
        The absolute Path of the saved file.

    Raises:
        IOError: If writing fails (disk full, permissions, etc.).
    """
    root = Path(__file__).resolve().parent.parent
    output_dir = root / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / filename
    logger.debug("Saving output to: %s", output_path)

    try:
        output_path.write_text(content, encoding="utf-8")
        logger.info("Output saved successfully -> %s", output_path)
        return output_path
    except IOError as exc:
        logger.error("Failed to save output to '%s': %s", output_path, exc)
        raise


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def truncate(text: str, max_chars: int = 4000) -> str:
    """
    Truncate text to stay within LLM context / token budgets.

    Tavily can return very long page excerpts. Sending the full text
    straight to Groq is wasteful and may hit rate limits on smaller
    models. This helper gives a safe ceiling.

    Args:
        text:      Input text.
        max_chars: Maximum number of characters to keep.

    Returns:
        The (possibly truncated) string.
    """
    if len(text) > max_chars:
        logger.debug(
            "Text truncated from %d to %d chars.", len(text), max_chars
        )
        return text[:max_chars] + "\n...[truncated]"
    return text
