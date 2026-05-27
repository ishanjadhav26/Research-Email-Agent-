# 🔍 Research Email Agent

A pure-Python AI agent that researches any topic on the web and produces a
professional email summary — no LangChain, no CrewAI, no magic.

```
python main.py "quantum computing breakthroughs 2024"
```

---

## Table of Contents

1. [What This Project Demonstrates](#1-what-this-project-demonstrates)
2. [Why This Counts as an AI Agent](#2-why-this-counts-as-an-ai-agent)
3. [Folder Structure Explained](#3-folder-structure-explained)
4. [Setup Instructions](#4-setup-instructions)
5. [How to Run](#5-how-to-run)
6. [Tool Calling Explained](#6-tool-calling-explained)
7. [Prompt Management Explained](#7-prompt-management-explained)
8. [Context Flow Explained](#8-context-flow-explained)
9. [Logging Explained](#9-logging-explained)
10. [Expected Output](#10-expected-output)
11. [Production Considerations](#11-production-considerations)
12. [Common Debugging Problems](#12-common-debugging-problems)
13. [What Becomes Painful at Scale](#13-what-becomes-painful-at-scale)
14. [What Frameworks Would Simplify](#14-what-frameworks-would-simplify)
15. [What Pure Python Makes Easier](#15-what-pure-python-makes-easier)
16. [Where Developer Friction Lives](#16-where-developer-friction-lives)
17. [Future Improvements](#17-future-improvements)

---

## 1. What This Project Demonstrates

This is not a "look how smart the AI is" demo. It's a "look how much
engineering goes into making an AI useful" demo.

You will see:

| Concern | Where it lives |
|---|---|
| Environment management | `.env`, `python-dotenv` |
| External tool calls | `tools/web_search.py` |
| LLM API communication | `tools/groq_client.py` |
| Prompt management | `prompts/*.txt` |
| Output formatting | `tools/email_formatter.py` |
| Orchestration / sequencing | `main.py` |
| Logging at every step | `utils/logger.py`, `logs/` |
| Error handling | Every tool file |
| State management | `state` dict in `main.py` |
| Output persistence | `utils/helpers.py`, `outputs/` |
| Scheduling (stub) | `scheduler.py` |

---

## 2. Why This Counts as an AI Agent

A **script** calls an LLM once and returns the response.

An **agent** uses external tools, feeds results back to the LLM, and
takes sequential actions toward a goal. Here's the difference in practice:

```
Script:  user_input → LLM → output

Agent:   user_input
             ↓
         [Tool: Web Search]       ← external world
             ↓
         search_results
             ↓
         [LLM: Summarise]         ← reasoning
             ↓
         research_summary
             ↓
         [LLM: Write Email]       ← generation
             ↓
         email_body
             ↓
         [Tool: Save File]        ← side effect
             ↓
         output_path
```

The agent:
- **Perceives** its environment (web search results).
- **Reasons** about the information (LLM summarisation).
- **Acts** on the world (saves a file).
- **Maintains state** between steps (the `state` dict).

This is the minimal viable agent loop. Add loops, self-correction, and
multi-step planning and you have a more complex agent — but it's the
same pattern.

---

## 3. Folder Structure Explained

```
research_email_agent/
│
├── main.py              ← Orchestrator. Reads like a recipe: step 1, 2, 3, 4.
├── scheduler.py         ← Stub for automated/scheduled runs.
├── requirements.txt     ← Pinned dependencies.
├── README.md            ← You are here.
├── .env.example         ← Template for secrets (never commit .env).
│
├── prompts/             ← Plain-text prompt templates. Non-engineers can edit these.
│   ├── research_prompt.txt
│   └── email_prompt.txt
│
├── tools/               ← One file per external capability.
│   ├── web_search.py    ← Tavily + DuckDuckGo with fallback logic.
│   ├── groq_client.py   ← Groq SDK wrapper with retry logic.
│   └── email_formatter.py ← Assembles the final email string.
│
├── outputs/             ← Agent's written output (gitignore in production).
│   └── latest_email.txt
│
├── logs/                ← Execution logs (gitignore in production).
│   └── execution.log
│
└── utils/               ← Shared helpers that don't belong to a specific tool.
    ├── logger.py        ← Centralised logging config (one source of truth).
    └── helpers.py       ← Prompt loading, file saving, env key loading.
```

**Design rule**: every file has exactly one reason to exist. If you can't
explain a file's purpose in one sentence, it needs to be split or merged.

---

## 4. Setup Instructions

### Prerequisites
- Python 3.10+
- A [Groq API key](https://console.groq.com/) (free tier available)
- A [Tavily API key](https://tavily.com/) (free tier: 1000 searches/month) — optional

### Step 1: Clone / download the project

```bash
cd research_email_agent
```

### Step 2: Create a virtual environment

```bash
python -m venv venv

# Activate it:
# macOS / Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure secrets

```bash
cp .env.example .env
```

Open `.env` in your editor and fill in:

```
GROQ_API_KEY=gsk_your_actual_key_here
TAVILY_API_KEY=tvly-your_actual_key_here
```

**Never commit `.env` to git.** Add it to `.gitignore`:

```
echo ".env" >> .gitignore
```

---

## 5. How to Run

### Interactive mode
```bash
python main.py
# You will be prompted: "Enter a research topic:"
```

### CLI argument mode
```bash
python main.py "impact of AI on software engineering jobs"
```

### Expected terminal output
```
═══════════════════════════════════════════════════════
  🔍 Research Email Agent
═══════════════════════════════════════════════════════

  Starting research on: "impact of AI on software engineering jobs"
  (Check logs/execution.log for detailed progress)

─────────────────────────────────────────────────────
  ✓ Email saved → /path/to/outputs/latest_email.txt

  Preview (first 400 chars):
  ────────────────────────────────────────
  To: research-team@example.com
  From: research-agent@example.com
  Date: Monday, 15 January 2024 at 08:00
  Subject: Research Summary – impact of AI on software engineering jobs
  ────────────────────────────────────────────────────────────

  Dear Research Team,
  …

  Done. Full logs in logs/execution.log
─────────────────────────────────────────────────────
```

---

## 6. Tool Calling Explained

In frameworks like LangChain, "tools" are objects registered in a registry
and invoked by the LLM itself. Here, tools are just Python functions that
the orchestrator calls explicitly.

**Tavily tool (`tools/web_search.py`)**

```python
# The agent calls this, not the LLM.
raw_results = perform_web_search(state["topic"], max_results=5)
```

The function returns plain text. The agent stores it in `state["search_results"]`
and passes it to the LLM in the next step. The LLM never "knows" it called
a tool — it just receives text as part of the prompt.

**Why this matters for debugging:**
You can inspect `state["search_results"]` after step 1 to see exactly what
the LLM will receive. No magic, no abstraction. Set a breakpoint in VS Code
after `step_web_search()` returns and inspect the `state` dict.

**Fallback pattern:**
```python
result = search_tavily(query)   # Try primary
if not result:
    result = search_duckduckgo(query)  # Try fallback
if not result:
    raise RuntimeError("Both providers failed")
```

This is a simple but production-realistic pattern. In a real system you'd
also add circuit-breaker logic (stop calling a provider if it's failed 5
times in a row).

---

## 7. Prompt Management Explained

Prompts live in `prompts/*.txt`, not in Python strings. Here's why:

| Approach | Problem |
|---|---|
| Hardcoded string in Python | Every prompt change requires a code review |
| Database | Overkill for small projects |
| `.txt` files | Editable by anyone, diff-able in git, loadable dynamically |

**How it works:**

```
prompts/research_prompt.txt:
---
You are a professional research analyst...
RESEARCH TOPIC: {topic}
RAW SEARCH RESULTS: {search_results}
...
```

```python
# In main.py:
template = load_prompt("research_prompt.txt")   # Read the file
prompt = template.format(                        # Fill in the blanks
    topic=state["topic"],
    search_results=state["search_results"],
)
summary = call_groq(prompt)                      # Send to LLM
```

**The `{placeholder}` pattern** uses Python's built-in `str.format()`.
This is deliberately simple. As prompts get more complex, you'd move to
Jinja2 templates (which support conditionals and loops) or a prompt
versioning tool like LangSmith.

---

## 8. Context Flow Explained

The agent's "memory" is the `state` dictionary. Here's what flows through:

```
Step 0: state = {"topic": "quantum computing", ...}

Step 1: [Web Search]
        state["search_results"] = "Source 1: IBM announced..."

Step 2: [Groq: Research Summary]
        prompt = research_prompt.format(
            topic    = state["topic"],          ← from step 0
            results  = state["search_results"]  ← from step 1
        )
        state["research_summary"] = groq(prompt)

Step 3: [Groq: Email]
        prompt = email_prompt.format(
            topic   = state["topic"],              ← from step 0
            summary = state["research_summary"]   ← from step 2
        )
        state["email_body"] = groq(prompt)

Step 4: [Save File]
        state["output_path"] = save(state["email_body"])
```

Each step reads from state (what's already known) and writes back to state
(what was just learned). This is the simplest possible form of context
management.

**What you're NOT doing here** that you would in a more advanced agent:
- Conversation history (multi-turn back-and-forth with the LLM)
- Vector memory (semantic search over past runs)
- Self-reflection (the agent checking its own output quality)

---

## 9. Logging Explained

Every meaningful event is logged. Here's the philosophy:

| Level | When to use |
|---|---|
| `DEBUG` | Internal details: prompt lengths, file paths, API parameters |
| `INFO` | Step milestones: "Search completed", "Email saved" |
| `WARNING` | Unexpected but non-fatal: "Tavily failed, using DuckDuckGo" |
| `ERROR` | Something failed: "API key missing", "File write failed" |

**Console** shows INFO and above (readable at a glance).
**Log file** (`logs/execution.log`) captures DEBUG and above (full trace for post-mortems).

**Why a central logger module?**

If you call `logging.basicConfig()` in two files, you get duplicate log
lines. `utils/logger.py` configures logging once and every module imports
the same configured logger:

```python
# In any module:
from utils.logger import get_logger
logger = get_logger(__name__)
logger.info("Something happened")
```

The `__name__` argument makes log lines show which module emitted them:
```
08:00:07 | INFO | tools.groq_client | Groq response received
```

---

## 10. Expected Output

**`outputs/latest_email.txt`:**

```
To: research-team@example.com
From: research-agent@example.com
Date: Monday, 15 January 2024 at 08:00
Subject: Research Summary – quantum computing breakthroughs 2024
────────────────────────────────────────────────────────────

Dear Research Team,

I wanted to share a brief summary of our latest research into quantum
computing developments in 2024, which has seen significant milestones
across both hardware and software fronts.

**Key Findings:**

• IBM unveiled its 1,121-qubit Condor processor in late 2023, with 2024
  benchmarks showing a 40% improvement in error correction rates compared
  to its predecessor.

• Google's DeepMind published a paper demonstrating quantum advantage in
  protein folding simulations, potentially accelerating drug discovery
  timelines by a factor of 10–100x.

• The US NIST finalised three post-quantum cryptography standards, which
  are now being adopted by major cloud providers ahead of the anticipated
  "cryptographically relevant quantum computer" threshold.

**Implications / So What?**

These developments suggest that quantum computing is transitioning from
laboratory curiosity to commercial relevance faster than most 2020
projections anticipated. Teams working on cryptography, logistics
optimisation, and drug discovery should begin assessing quantum readiness
roadmaps within the next 12–18 months.

I'd welcome a discussion on which of these areas are most relevant to our
current work. Happy to dig deeper into any specific thread.

Best regards,
Research Agent

────────────────────────────────────────────────────────────
This email was generated automatically by the Research Email Agent.
Generated at: Monday, 15 January 2024 at 08:00
```

---

## 11. Production Considerations

These are not hypothetical concerns — they're the real issues you'll hit
when moving from "it works on my machine" to "it runs every day without me":

**1. API rate limits and costs**
- Groq free tier: ~14,400 requests/day, but with per-minute limits.
  If you run the agent rapidly in a loop, you'll hit `429 RateLimitError`.
- Tavily free tier: 1000 searches/month. At daily runs, you exhaust this in
  a month. Budget for the paid tier or cache results aggressively.
- **Solution**: Add exponential backoff in `groq_client.py` and a result
  cache (pickle or SQLite) in `web_search.py`.

**2. Secrets management**
- `.env` files are fine locally. In CI/CD, use GitHub Secrets or a vault.
- Never log API keys. `utils/helpers.py` logs that a key was *found*, not
  its value.

**3. Output file management**
- `latest_email.txt` gets overwritten every run. After 30 runs you've lost
  29 emails.
- **Solution**: Name outputs with timestamps: `email_2024-01-15_08-00.txt`.
  Implement a cleanup policy (keep last 30 days).

**4. Error alerting**
- If the agent crashes at 3am during a scheduled run, you won't know until
  morning. Add a Slack/email alert on `ERROR` log events.

**5. Input validation**
- The topic input isn't sanitised. A topic of `""` or `"<script>"` will
  produce unhelpful results.
- **Solution**: Add minimum length check and strip HTML before passing to
  the search tool.

**6. LLM output quality**
- `llama-3.3-70b-versatile` sometimes produces inconsistent formatting.
  The email validation step catches the worst cases, but you'll want a
  human review loop for high-stakes use cases.

---

## 12. Common Debugging Problems

### "GROQ_API_KEY is not set"
Your `.env` file isn't loaded. Make sure:
1. The file is named `.env` (not `.env.txt` or `.env.example`).
2. You're running from the project root directory.
3. `load_dotenv()` is the **first** call in `main.py` (it is, but verify
   you haven't moved it below the imports that read `os.environ`).

### "Tavily returned zero results"
- Check your Tavily key in the [console](https://app.tavily.com).
- Try a simpler, shorter query.
- Check if you've exhausted your free-tier quota.
- DuckDuckGo fallback should kick in automatically — if it doesn't, check
  `logs/execution.log` for the warning message.

### Duplicate log lines in the terminal
You've called `logging.basicConfig()` somewhere, which adds a second root
handler. Search the codebase for `basicConfig` and remove it.

### "groq.RateLimitError: 429"
You've hit the per-minute token limit. Wait 60 seconds. To avoid this,
reduce `max_tokens` in `groq_client.py` or add `time.sleep(5)` between
the two Groq calls in `main.py`.

### DuckDuckGo returns a 202 or empty result
DuckDuckGo's unofficial API rate-limits aggressively. Add `time.sleep(2)`
before the `DDGS.text()` call in `web_search.py`.

### Email output looks like the raw prompt
The LLM echoed the prompt instead of completing it. This usually means
the prompt template had a formatting issue and `str.format()` left
placeholders unfilled. Add `print(prompt)` before the `call_groq()` call
to inspect the final prompt.

### VS Code / Antigravity: breakpoints not hitting
Confirm the interpreter path in VS Code matches your virtual environment:
`Ctrl+Shift+P` → "Python: Select Interpreter" → choose the venv.

### Import errors (`ModuleNotFoundError`)
Run `pip install -r requirements.txt` inside the activated virtual
environment. If you see `(base)` in your terminal instead of `(venv)`,
you're in the base conda environment.

---

## 13. What Becomes Painful at Scale

When you run this agent 10x per day across 5 topics:

1. **No result caching** — the same Tavily query runs each time, consuming
   quota and adding latency. Fix: SQLite cache keyed by `hash(query)`.

2. **No concurrency** — steps run sequentially. Two Groq calls at 4s each
   = 8s minimum. Fix: `asyncio` or `ThreadPoolExecutor` for independent steps.

3. **One output file** — you lose history. Fix: timestamp-based filenames
   and an index file.

4. **No observability** — log files grow unboundedly. Fix: log rotation
   (`RotatingFileHandler`), structured JSON logs, and a log aggregator.

5. **No retry budget tracking** — retries are silent. Fix: emit a metric
   (even a counter in a file) every time a retry fires.

6. **Manual prompt iteration** — when you change a prompt, there's no
   A/B test framework. Fix: version prompts with git tags and compare
   output quality across versions.

---

## 14. What Frameworks Would Simplify

| Pain point | LangChain / LangGraph solution |
|---|---|
| Tool registry + LLM-driven tool selection | `@tool` decorator + `AgentExecutor` |
| Multi-turn conversation memory | `ConversationBufferMemory` |
| Retry logic, fallbacks | `with_fallbacks()`, `RunnableWithRetry` |
| Prompt versioning | LangSmith Prompt Hub |
| Streaming responses | `stream()` on any chain |
| Parallel step execution | `RunnableParallel` |

**CrewAI** would simplify multi-agent coordination (e.g., a "researcher
agent" and a "writer agent" running in parallel).

**The trade-off**: frameworks add 3 layers of abstraction between you and
the API call. When something breaks, the stack trace points to framework
internals, not your code. For learning and debugging, pure Python wins.

---

## 15. What Pure Python Makes Easier

1. **Debuggability** — set a breakpoint anywhere, inspect the `state` dict,
   understand exactly what's happening. No framework magic.

2. **Dependency transparency** — `requirements.txt` has 5 lines. You know
   exactly what's installed.

3. **Error messages** — stack traces point to *your* code, not 10 layers
   of framework code.

4. **Customisation** — you can change the fallback logic, the retry
   strategy, the state shape, or the output format without reading framework
   docs.

5. **Interview clarity** — you can explain every line. "We call Groq here,
   pass the state dict through, and save the result here." No hand-waving.

---

## 16. Where Developer Friction Lives

In order of how often it will actually slow you down:

1. **API key setup** — 30% of debugging sessions are "the key isn't loaded".
   Solution: add a startup check that logs which keys are present/missing.

2. **Prompt iteration** — the LLM output quality depends heavily on the
   prompt. You'll edit `research_prompt.txt` and `email_prompt.txt` a lot
   before results are consistently good.

3. **Search result quality** — Tavily/DuckDuckGo return wildly different
   content for the same query. You'll need to experiment with query wording
   and `max_results`.

4. **Rate limits** — always unexpected, always during demos.

5. **Context length** — if the search results are very long and the prompt
   + results exceed the model's context window, Groq returns an error.
   The `truncate()` helper mitigates this, but you may need to tune
   `max_chars`.

---

## 17. Future Improvements

**Easy (weekend project):**
- [ ] Timestamp-based output filenames
- [ ] Log rotation with `RotatingFileHandler`
- [ ] `--topic` CLI flag with `argparse`
- [ ] Email validation: require at least 3 "Key Findings" bullets

**Medium (1–2 days):**
- [ ] SQLite cache for search results (avoid re-querying the same topic)
- [ ] Async Groq calls using `asyncio` and `groq.AsyncGroq`
- [ ] Slack webhook notification when email is generated
- [ ] HTML email output option

**Hard (production-ready):**
- [ ] Self-reflection loop: the agent evaluates its own email and rewrites
      if quality score < threshold
- [ ] Multi-topic batch mode with progress bar (`tqdm`)
- [ ] Prompt versioning and A/B testing framework
- [ ] SMTP integration to actually send the email
- [ ] Vector store (ChromaDB) for semantic search over past research
