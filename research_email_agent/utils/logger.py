"""
utils/logger.py
---------------
Centralized logging configuration for the Research Email Agent.

Why a separate logger module?
- Every file can import the same pre-configured logger instead of
  calling logging.basicConfig() in multiple places (which causes
  duplicate log entries in larger projects).
- The handler setup (file + console) lives in exactly one place,
  making it easy to add structured/JSON logging later.

Developer note: If you see duplicate log lines in the terminal,
you have probably called basicConfig() more than once somewhere.
"""

import logging
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# Resolve the logs directory relative to this file so the logger works
# regardless of which directory you launch python from.
ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "execution.log"

# Create the logs directory if it doesn't exist yet.
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------
def get_logger(name: str = "research_agent") -> logging.Logger:
    """
    Return a configured logger.

    Usage in any module:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")

    Args:
        name: Logger name. Using __name__ in each module gives you
              per-module prefixes in the log file (helpful for debugging).

    Returns:
        A Logger instance with both a file handler and a console handler.
    """
    logger = logging.getLogger(name)

    # Guard: don't add duplicate handlers if get_logger() is called twice
    # for the same name (common mistake when reloading modules in notebooks).
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  # Capture everything; handlers filter below.

    # ------------------------------------------------------------------
    # Formatter – include timestamp, level, logger name, and message.
    # The %(name)s field shows which module emitted the log line.
    # ------------------------------------------------------------------
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ------------------------------------------------------------------
    # File handler – DEBUG and above, appends to logs/execution.log
    # ------------------------------------------------------------------
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    # ------------------------------------------------------------------
    # Console handler – INFO and above so the terminal isn't noisy with
    # debug-level internals during normal runs.
    # ------------------------------------------------------------------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
