"""
main.py
-------
Entry point and orchestration layer for the Research Email Agent.

This file is intentionally kept thin. Its only job is to:
1. Boot up the environment (load .env, init logger).
2. Accept user input (the research topic).
3. Call each tool in the correct order.
4. Handle top-level errors gracefully.
5. Report the final result to the user.

All business logic lives in tools/ and utils/ — main.py just wires them
together. This is the "orchestration" pattern: a conductor that knows the
sequence of steps but delegates the actual work.

WHAT MAKES THIS AN AI AGENT?
------------------------------
A simple script calls one LLM once. An agent:
- Uses external tools (web search) to gather information.
- Feeds tool output back into the LLM as context.
- Makes sequential decisions (research → summarize → draft email).
- Has its own memory of the current task (the `state` dict below).
- Produces a structured artefact (the saved email).

This project doesn't have loops or self-correction yet, but the pattern
here scales directly to those more complex behaviours.
"""

import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Load .env BEFORE importing project modules that read os.environ
load_dotenv()

from utils.logger import get_logger
from utils.helpers import load_prompt, save_output
from tools.web_search import perform_web_search
from tools.groq_client import call_groq
from tools.email_formatter import format_email, validate_email_output

# ---------------------------------------------------------------------------
# Logger for the orchestration layer
# ---------------------------------------------------------------------------
logger = get_logger("main")


# ---------------------------------------------------------------------------
# Agent state – a plain dict that flows through all steps.
# In a more complex agent this would be a dataclass or Pydantic model.
# ---------------------------------------------------------------------------
def make_initial_state(topic: str) -> dict:
    return {
        "topic": topic,
        "search_results": None,       # Raw text from the web search tool
        "research_summary": None,     # LLM-generated research summary
        "email_body": None,           # LLM-generated email body
        "formatted_email": None,      # Final email with headers
        "output_path": None,          # Path to the saved file
        "start_time": datetime.now(),
        "errors": [],                 # Accumulated non-fatal errors
    }


# ---------------------------------------------------------------------------
# Individual agent steps
# ---------------------------------------------------------------------------

def step_web_search(state: dict) -> dict:
    """STEP 1 – Search the web for the research topic."""
    logger.info("-- STEP 1: Web Search --")

    try:
        raw_results = perform_web_search(state["topic"], max_results=5)
        state["search_results"] = raw_results
        logger.info("Web search completed. Retrieved %d chars.", len(raw_results))
    except RuntimeError as exc:
        # If both search providers fail, we cannot continue.
        logger.error("Web search failed completely: %s", exc)
        raise  # Re-raise to abort the run in main()

    return state


def step_research_summary(state: dict) -> dict:
    """STEP 2 – Ask the LLM to summarise the raw search results."""
    logger.info("-- STEP 2: Research Summarisation --")

    # Load the prompt template from disk and inject the current state values.
    # This is the "prompt management" pattern: templates live in prompts/,
    # Python only fills in the blanks.
    template = load_prompt("research_prompt.txt")
    prompt = template.format(
        topic=state["topic"],
        search_results=state["search_results"],
    )

    logger.debug("Research prompt built (%d chars). Calling Groq…", len(prompt))

    try:
        summary = call_groq(prompt)
        state["research_summary"] = summary
        logger.info(
            "Research summary generated (%d chars).", len(summary)
        )
    except (EnvironmentError, RuntimeError) as exc:
        logger.error("Research summarisation failed: %s", exc)
        raise

    return state


def step_email_generation(state: dict) -> dict:
    """STEP 3 – Ask the LLM to write the email body from the summary."""
    logger.info("-- STEP 3: Email Generation --")

    template = load_prompt("email_prompt.txt")
    prompt = template.format(
        topic=state["topic"],
        research_summary=state["research_summary"],
    )

    logger.debug("Email prompt built (%d chars). Calling Groq…", len(prompt))

    try:
        email_body = call_groq(prompt, temperature=0.5)  # Slightly more creative
        state["email_body"] = email_body
        logger.info("Email body generated (%d chars).", len(email_body))
    except (EnvironmentError, RuntimeError) as exc:
        logger.error("Email generation failed: %s", exc)
        raise

    return state


def step_format_and_save(state: dict) -> dict:
    """STEP 4 – Wrap the email body in headers and save to outputs/."""
    logger.info("-- STEP 4: Format & Save --")

    formatted = format_email(
        topic=state["topic"],
        llm_output=state["email_body"],
    )
    state["formatted_email"] = formatted

    # Validate before saving – don't save garbage output.
    if not validate_email_output(formatted):
        logger.error("Email failed validation – not saving.")
        state["errors"].append("Email validation failed.")
        return state

    try:
        output_path = save_output(formatted, filename="latest_email.txt")
        state["output_path"] = output_path
    except IOError as exc:
        logger.error("Could not save output file: %s", exc)
        state["errors"].append(f"File save failed: {exc}")

    return state


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_agent(topic: str) -> dict:
    """
    Execute all agent steps in sequence and return the final state.

    Args:
        topic: The research topic provided by the user.

    Returns:
        The final state dictionary (useful for testing / inspection).
    """
    logger.info("+==========================================+")
    logger.info("|    Research Email Agent - Starting       |")
    logger.info("+==========================================+")
    logger.info("Topic: '%s'", topic)

    state = make_initial_state(topic)

    # Each step mutates (and returns) the state dict.
    # This linear pipeline is easy to follow in a debugger:
    # set a breakpoint after any step to inspect intermediate results.
    try:
        state = step_web_search(state)
        state = step_research_summary(state)
        state = step_email_generation(state)
        state = step_format_and_save(state)
    except Exception as exc:
        # A fatal error in any step reaches here.
        logger.error("Agent run aborted: %s", exc)
        state["errors"].append(str(exc))
        return state

    elapsed = (datetime.now() - state["start_time"]).total_seconds()
    logger.info("Agent completed in %.1f seconds.", elapsed)

    if state["output_path"]:
        logger.info("Email saved -> %s", state["output_path"])
    if state["errors"]:
        logger.warning("Run completed with %d error(s): %s",
                       len(state["errors"]), state["errors"])

    return state


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """
    Command-line interface: prompt for a topic, run the agent, print results.
    """
    print("\n" + "=" * 55)
    print("  [Search] Research Email Agent")
    print("=" * 55)

    # Accept topic from command-line argument OR interactive prompt.
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
        print(f"\n  Topic (from CLI): {topic}")
    else:
        topic = input("\n  Enter a research topic: ").strip()

    if not topic:
        print("  [ERROR] No topic provided. Exiting.")
        sys.exit(1)

    print(f"\n  Starting research on: \"{topic}\"")
    print("  (Check logs/execution.log for detailed progress)\n")

    # Run the agent
    state = run_agent(topic)

    # Print final status to the terminal
    print("\n" + "-" * 55)
    if state.get("output_path"):
        print(f"  * Email saved -> {state['output_path']}")
        print("\n  Preview (first 400 chars):")
        print("  " + "-" * 40)
        preview = state["formatted_email"][:400]
        for line in preview.splitlines():
            print("  " + line)
        print("  ...")
    else:
        print("  [ERROR] Agent did not produce an output file.")

    if state["errors"]:
        print("\n  [WARNING] Errors encountered:")
        for err in state["errors"]:
            print(f"    - {err}")

    print("\n  Done. Full logs in logs/execution.log")
    print("-" * 55 + "\n")


if __name__ == "__main__":
    main()
