"""
tools/web_search.py
-------------------
Web search tool with Tavily as primary provider and DuckDuckGo as fallback.

WHY TWO PROVIDERS?
------------------
Tavily is purpose-built for LLM research workflows: it returns clean,
pre-extracted snippets rather than raw HTML, which means less text
cleaning and better Groq results. DuckDuckGo requires no API key, making
it useful for quick local testing or when the Tavily quota is exhausted.

This "primary + fallback" pattern is common in production agents. You want
the agent to degrade gracefully, not crash, when one dependency is down.

DEVELOPER FRICTION HERE:
- DuckDuckGo's unofficial Python library sometimes rate-limits aggressively.
  If you see 202/429 errors, add time.sleep(2) between calls or reduce
  max_results.
- Tavily's free tier allows ~1000 searches/month; watch your usage.
"""

import time
from typing import Optional

from utils.logger import get_logger
from utils.helpers import load_env_key, truncate

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Tavily search
# ---------------------------------------------------------------------------

def search_tavily(query: str, max_results: int = 5) -> Optional[str]:
    """
    Search the web using the Tavily API and return a plain-text summary
    of the top results.

    Args:
        query:       The search query string.
        max_results: How many results to request from Tavily.

    Returns:
        A formatted string of research notes, or None on failure.
    """
    api_key = load_env_key("TAVILY_API_KEY")
    if not api_key:
        logger.warning("TAVILY_API_KEY missing – skipping Tavily search.")
        return None

    try:
        # Import here (not at module top) so the app doesn't crash at startup
        # if the package is missing – we can still fall back to DuckDuckGo.
        from tavily import TavilyClient

        logger.info("Running Tavily search for: '%s'", query)
        client = TavilyClient(api_key=api_key)

        # search_depth="advanced" gives richer content at the cost of
        # slightly higher latency and quota usage.
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
        )

        results = response.get("results", [])
        if not results:
            logger.warning("Tavily returned zero results for query: '%s'", query)
            return None

        logger.info("Tavily returned %d results.", len(results))

        # Format results into structured research notes that the LLM can
        # summarize easily. Numbered sections help the model refer back to
        # individual sources in the email.
        notes = []
        for i, r in enumerate(results, start=1):
            title = r.get("title", "No title")
            url = r.get("url", "")
            content = truncate(r.get("content", ""), max_chars=800)
            notes.append(f"[Source {i}] {title}\nURL: {url}\n{content}")

        return "\n\n".join(notes)

    except ImportError:
        logger.error("tavily-python is not installed. Run: pip install tavily-python")
        return None
    except Exception as exc:
        # Broad catch is intentional: Tavily can raise various HTTP/auth errors.
        # We log the full error and return None so the fallback is triggered.
        logger.error("Tavily search failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# DuckDuckGo fallback search
# ---------------------------------------------------------------------------

def search_duckduckgo(query: str, max_results: int = 5) -> Optional[str]:
    """
    Search the web using the DuckDuckGo unofficial API (no key required).

    Args:
        query:       The search query string.
        max_results: How many results to fetch.

    Returns:
        A formatted string of research notes, or None on failure.
    """
    try:
        from duckduckgo_search import DDGS

        logger.info("Running DuckDuckGo search for: '%s'", query)

        # DDGS is a context manager; using 'with' ensures the underlying
        # HTTP session is closed cleanly even on exception.
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=max_results))

        if not raw:
            logger.warning("DuckDuckGo returned zero results for: '%s'", query)
            return None

        logger.info("DuckDuckGo returned %d results.", len(raw))

        notes = []
        for i, r in enumerate(raw, start=1):
            title = r.get("title", "No title")
            url = r.get("href", "")
            body = truncate(r.get("body", ""), max_chars=800)
            notes.append(f"[Source {i}] {title}\nURL: {url}\n{body}")

        return "\n\n".join(notes)

    except ImportError:
        logger.error(
            "duckduckgo-search is not installed. Run: pip install duckduckgo-search"
        )
        return None
    except Exception as exc:
        logger.error("DuckDuckGo search failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public interface – single entry point used by main.py
# ---------------------------------------------------------------------------

def perform_web_search(query: str, max_results: int = 5) -> str:
    """
    Perform a web search using Tavily (primary) or DuckDuckGo (fallback).

    This is the ONLY function that main.py needs to import from this module.
    The primary/fallback logic is hidden here so the orchestration layer
    stays clean.

    Args:
        query:       Research topic or question.
        max_results: Number of results to retrieve.

    Returns:
        Research notes as a plain string.

    Raises:
        RuntimeError: If both search providers fail.
    """
    logger.info("=== WEB SEARCH TOOL CALLED ===")
    logger.debug("Query: '%s' | max_results: %d", query, max_results)

    # Try Tavily first
    result = search_tavily(query, max_results=max_results)
    if result:
        logger.info("Search completed via Tavily.")
        return result

    # Fall back to DuckDuckGo
    logger.warning("Tavily failed or unavailable – falling back to DuckDuckGo.")
    result = search_duckduckgo(query, max_results=max_results)
    if result:
        logger.info("Search completed via DuckDuckGo (fallback).")
        return result

    # Both providers failed
    error_msg = (
        "Both Tavily and DuckDuckGo searches failed. "
        "Check your API keys and network connection."
    )
    logger.error(error_msg)
    raise RuntimeError(error_msg)
