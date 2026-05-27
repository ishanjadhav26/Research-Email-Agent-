"""
scheduler.py
------------
Placeholder for scheduled / automated agent runs.

CURRENT STATE: Not implemented. This file exists to show WHERE scheduling
would live and what decisions you'd need to make.

WHY YOU'D NEED THIS:
--------------------
Right now the agent runs when you type `python main.py`. In production you
might want it to:
- Run every morning and email a daily briefing.
- Trigger when a Slack message matches a pattern.
- Run on a cron job inside a container.

THREE COMMON APPROACHES:
------------------------
1. OS cron job (simplest):
      0 8 * * * /usr/bin/python3 /path/to/main.py "AI news"
   No Python code needed beyond main.py.

2. APScheduler (pure Python, shown below as a stub):
      pip install APScheduler
   Keeps everything in Python; good for complex schedules.

3. Celery + Redis (distributed, for scale):
   Overkill for a single agent. Use when you need retries, task queues,
   and multiple workers.

DEVELOPER FRICTION AT SCALE:
-----------------------------
- Scheduled runs produce lots of output files. You'll need a naming
  convention (e.g., email_2024-01-15_08-00.txt) and a cleanup strategy.
- If the agent crashes, you need alerting (email, Slack webhook).
- Secrets management becomes harder when running as a cron job vs a shell
  where you sourced .env manually.

UNCOMMENT AND ADAPT the stub below when you're ready to automate.
"""

# ---------------------------------------------------------------------------
# APScheduler stub (uncomment to use)
# ---------------------------------------------------------------------------

# import time
# from apscheduler.schedulers.blocking import BlockingScheduler
# from main import run_agent
# from utils.logger import get_logger

# logger = get_logger("scheduler")

# scheduler = BlockingScheduler()

# @scheduler.scheduled_job("cron", hour=8, minute=0)
# def daily_research_job():
#     """Run the agent every day at 08:00 local time."""
#     topic = "latest AI research breakthroughs"
#     logger.info("Scheduled job triggered for topic: '%s'", topic)
#     try:
#         state = run_agent(topic)
#         if state.get("output_path"):
#             logger.info("Scheduled run completed. Output: %s", state["output_path"])
#         else:
#             logger.error("Scheduled run produced no output.")
#     except Exception as exc:
#         logger.error("Scheduled run failed: %s", exc)

# if __name__ == "__main__":
#     logger.info("Scheduler starting. Press Ctrl+C to stop.")
#     scheduler.start()

# ---------------------------------------------------------------------------
# Simple polling loop alternative (no extra dependency)
# ---------------------------------------------------------------------------

def run_on_interval(topic: str, interval_seconds: int = 86400):
    """
    Run the agent repeatedly with a fixed sleep interval.

    This is the simplest possible scheduler: no extra packages, no cron.
    It has no error recovery or drift correction, but it works for
    weekend projects and demos.

    Usage:
        python scheduler.py

    Args:
        topic:            The research topic to repeat.
        interval_seconds: Seconds between runs (default 86400 = 24 hours).
    """
    import time
    from main import run_agent
    from utils.logger import get_logger

    log = get_logger("scheduler")
    log.info("Simple scheduler starting. Interval: %ds. Topic: '%s'",
             interval_seconds, topic)

    while True:
        log.info("Starting scheduled agent run…")
        try:
            run_agent(topic)
        except Exception as exc:
            log.error("Scheduled run error: %s", exc)

        log.info("Sleeping for %d seconds until next run…", interval_seconds)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    # Change the topic and interval to suit your use case.
    run_on_interval(
        topic="latest developments in artificial intelligence",
        interval_seconds=86400,  # 24 hours
    )
