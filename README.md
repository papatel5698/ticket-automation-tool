# Ticket Automation Tool

> **Start with the [engagement brief](docs/brief.md):** the client, their problem, success metrics, constraints and what's out of scope. It describes the target system; the CLI below is today's Devin-based starting point. Design decisions are recorded in [`docs/decisions/`](docs/decisions/).

A Python CLI that uses the **Devin API** to analyze open GitHub issues, classify them, and optionally trigger automated fixes. Point it at any GitHub repo and get a structured breakdown of what Devin can fix automatically and what needs human review.

---

## What It Does

1. **Fetches all open issues** — Scans a GitHub repo for all open issues
2. **Analyzes each issue with Devin** — Sends each issue to the Devin API, which investigates the codebase and returns a structured assessment
3. **Caches results locally** — Stores analysis results in a local JSON cache so unchanged issues aren't re-analyzed on subsequent runs
4. **Generates a summary** — Aggregates results by type, priority, and recommended action
5. **Posts to GitHub** — Creates a new timestamped discussion for each analysis run (e.g., "Open Ticket Summary ran April 9th at 4:47 pm")
6. **Displays results in your terminal** — Shows a formatted table of the top tickets ranked by priority and confidence

You can also **automate fixes** — point the tool at a specific issue and Devin will investigate, fix the code, write tests, and open a PR.

---

## How the Analysis Works

For each open issue, the tool creates a Devin session with a prompt that includes the issue title, body, and labels. Devin investigates the issue against the actual codebase and returns a structured JSON response with these fields:

| Field | Values | Description |
|-------|--------|-------------|
| **Type** | `bug`, `feature`, `cleanup` | What kind of issue this is |
| **Action** | `automate`, `engineer_review`, `needs_more_info` | What should be done next |
| **Action Reasoning** | *(free text)* | Why this action was recommended — e.g., "Simple error handling fix in one function" |
| **Confidence** | `0–100%` | How confident Devin is in its analysis |
| **Priority** | `high`, `medium`, `low` | How urgent this issue is |
| **Complexity** | `high`, `medium`, `low` | How difficult the fix would be |
| **Complexity Reasoning** | *(free text)* | Why this complexity was assigned — e.g., "Requires rewriting the expression parser" |
| **Description** | *(free text)* | Generated summary of the issue and recommended approach |

### What the actions mean

- **`automate`** — Devin can fix this autonomously. These are typically simple bugs with clear reproduction steps and localized fixes (e.g., adding error handling, fixing a type conversion).
- **`engineer_review`** — The fix is too complex or risky for automation. A human should review and decide the approach (e.g., rewriting a parser for correct operator precedence).
- **`needs_more_info`** — The issue description is too vague to act on. Someone should ask the reporter for reproduction steps or clarification.

---

## Prerequisites

- **Python 3.11+** — check with `python3 --version`
- **pip** — comes with Python
- **GitHub personal access token** — with `repo` scope ([create one here](https://github.com/settings/tokens/new))
- **Devin API token** — from your [Devin settings](https://app.devin.ai/settings)

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/papatel5698/ticket-automation-tool.git
cd ticket-automation-tool

# 2. Install in editable mode (this also installs click and requests)
pip install -e .

# 3. Verify the CLI is available
ticket-analyzer --help
```

After step 2, the `ticket-analyzer` command is available globally in your shell.

---

## Configuration

### Option A: Environment Variables

```bash
export DEVIN_API_TOKEN=your_devin_token
export GITHUB_TOKEN=your_github_token
export GITHUB_REPO=papatel5698/calculator-demo
```

### Option B: CLI Flags

Every command accepts `--token`, `--github-token`, and `--repo` flags. Flags take precedence over environment variables.

```bash
ticket-analyzer analyze --token YOUR_DEVIN_TOKEN --github-token YOUR_GITHUB_TOKEN --repo owner/repo
```

---

## Usage

### Full Analysis

Analyze all open issues in the target repo:

```bash
ticket-analyzer analyze
```

This will:
1. Fetch all open issues from the repo
2. Check the local cache for previously analyzed issues (skipping unchanged ones)
3. Send uncached issues to Devin for analysis
4. Post a markdown summary as a new timestamped discussion on GitHub
5. Print a summary and top-10 table to your terminal

**Example output:**

```
Tickets Summary
───────────────
Total tickets:        20
By type:              8 bugs, 4 features, 4 cleanup
By action:            4 automate, 8 engineer review, 4 needs more info
By priority:          5 high, 9 medium, 6 low

Top 10 Tickets
──────────────
#   | Priority  | Type      | Action            | Confidence  | Complexity  | Title
2   | high      | bug       | automate          | 95%         | low         | Division by zero crashes the program
3   | high      | bug       | automate          | 92%         | low         | Empty input crashes the program
4   | high      | bug       | automate          | 93%         | low         | Division returns integer instead of decimal
6   | high      | bug       | engineer_review   | 88%         | high        | Operator precedence is wrong
5   | medium    | bug       | automate          | 90%         | low         | Whitespace in expressions causes parse error
7   | medium    | bug       | engineer_review   | 85%         | medium      | Negative number input causes parse error
8   | medium    | bug       | engineer_review   | 80%         | medium      | Repeated calculations show previous result
11  | medium    | feature   | engineer_review   | 70%         | high        | Add support for parentheses
9   | low       | bug       | needs_more_info   | 30%         | unknown     | Calculator gives wrong answer for large numbers
10  | low       | bug       | needs_more_info   | 20%         | unknown     | It crashed yesterday
```

### Override Defaults Per-Run

```bash
# Show top 20 instead of top 10
ticket-analyzer analyze --top 20
```

### Single Ticket Deep-Dive

Get a detailed analysis of one specific issue:

```bash
ticket-analyzer analyze --ticket 2
```

**Example output:**

```
Ticket #2: Division by zero crashes the program
────────────────────────────────────────────────
Type:                 bug
Action:               automate
Action Reasoning:     This is a simple error handling fix. The division operation
                      in calculator.py lacks a try/except block. Adding a
                      ZeroDivisionError catch with a user-friendly message is a
                      one-function change.
Confidence:           95%
Priority:             high
Complexity:           low
Complexity Reasoning: The fix requires adding a 3-line try/except block in the
                      divide() function in calculator.py. No other files are affected.
```

### Filtered Analysis

Filter the ticket list by type, action, or priority. Filters can be combined (AND logic). The summary section always shows the full picture — only the ticket list is filtered.

```bash
# Show only tickets Devin can automate
ticket-analyzer analyze --action automate

# Show only bugs
ticket-analyzer analyze --type bug

# Show only high-priority issues
ticket-analyzer analyze --priority high

# Combine filters: high-priority bugs that can be automated
ticket-analyzer analyze --type bug --action automate --priority high
```

### Skip Cache

Force re-analysis of all issues, ignoring cached results:

```bash
ticket-analyzer analyze --no-cache
```

### Clear Cache

Remove all cached analysis results:

```bash
ticket-analyzer clear-cache
```

### Automate a Fix

Tell Devin to fix a specific issue and open a PR:

```bash
ticket-analyzer automate --ticket 2
```

This creates a Devin session that:
1. Investigates the issue and the codebase
2. Writes a fix
3. Adds or updates tests
4. Opens a PR with a description in this format:

```markdown
## What
[Description of what the issue was]

## Why
[Explanation of why it needed to be fixed]

## How
[Description of how it was fixed]

Resolves #2
```

---

## Caching

Analysis results are cached locally in `.cache/analysis_cache.json` to avoid re-analyzing unchanged issues. The cache key is based on a SHA-256 hash of each issue's number, title, and body — so the cache is automatically invalidated when the issue content changes, but not when metadata like labels or timestamps are updated.

- **Cache is used by default** — previously analyzed issues are loaded from cache on subsequent runs
- **Skip cache per-run** — use `ticket-analyzer analyze --no-cache` to re-analyze everything from scratch
- **Clear cache** — use `ticket-analyzer clear-cache` to delete all cached results

The `.cache/` directory is gitignored and safe to delete at any time.

---

## Workflow Diagrams

### Architecture

```mermaid
graph TD
    CLI["cli.py"] --> Analyzer["analyzer.py"]
    Analyzer --> GitHub["github_client.py"]
    Analyzer --> Devin["devin_client.py"]
    Analyzer --> Cache["cache.py"]
    Analyzer --> Models["models.py"]
    GitHub --> GitHubAPI["GitHub REST API"]
    Devin --> DevinAPI["Devin API"]
    Cache --> CacheFile[".cache/analysis_cache.json"]
```

### Analyze Command Flow

```mermaid
flowchart TD
    Start["ticket-analyzer analyze"] --> FetchIssues["Fetch all open issues from GitHub"]
    FetchIssues --> CheckCache["Check local cache for each issue"]
    CheckCache --> SendToDevin["Send uncached issues to Devin for analysis"]
    SendToDevin --> CollectResults["Collect structured analysis results"]
    CollectResults --> UpdateCache["Cache new analysis results"]
    UpdateCache --> GenSummary["Generate aggregate summary"]
    GenSummary --> ApplyFilters["Apply CLI filters (type, action, priority)"]
    ApplyFilters --> PostGitHub["Post markdown summary to GitHub discussion"]
    PostGitHub --> Display["Display results in terminal"]
```

### Automate Command Flow

```mermaid
flowchart TD
    Start["ticket-analyzer automate --ticket N"] --> Fetch["Fetch issue #N from GitHub"]
    Fetch --> CreateSession["Create Devin automation session"]
    CreateSession --> Investigate["Devin investigates the issue and codebase"]
    Investigate --> Fix["Devin writes the fix"]
    Fix --> Test["Devin writes or updates tests"]
    Test --> PR["Devin opens a PR with What/Why/How description"]
    PR --> Report["Report PR link to user"]
```

---

## Demo Target

The demo runs against [papatel5698/calculator-demo](https://github.com/papatel5698/calculator-demo), a small calculator with intentional bugs and a standard set of issues. To start each demo from the same state, run its **Reset demo** Action (or `scripts/reset_demo.py` there). It restores the buggy code from the `demo-baseline` tag and recreates the issue set. Why it works this way: [decision 002](docs/decisions/002-demo-reset.md).

---

## Evals

`evals/answer_key.json` holds the expected triage (type, action, priority and a reason) for every issue in calculator-demo's standard issue set (23 issues). Duplicates also carry `duplicate_of`, naming the original issue. Entries are keyed by issue title, because the demo reset recreates issues with new numbers. The key is judged against what the code actually does, not just what each report claims: two of the demo issues report crashes that don't happen. Why: [decision 003](docs/decisions/003-answer-key.md). `src/answer_key.py` loads and validates the key; the eval command that scores against it comes in M2.

`tests/test_answer_key.py` checks that the key covers exactly the titles in calculator-demo's `demo/issues.json`. CI checks out that file; locally, the test runs when `calculator-demo` is cloned next to this repo (or `CALCULATOR_DEMO_DIR` points at it), and skips otherwise.

---

## Running Tests

All tests use mocked API responses — no tokens or network access needed.

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v
```

Use Python 3.11 or newer, as CI does. If your system `python3` is older, make a virtual environment first, e.g. `python3.12 -m venv .venv && source .venv/bin/activate`.

**Expected result: all tests pass.**

Tests cover:
- **`test_github_client.py`** — Fetching issues, adding labels, posting comments, pagination, PR filtering
- **`test_devin_client.py`** — Session creation, status polling, result parsing, timeouts
- **`test_analyzer.py`** — Summary generation, filtering, sorting, formatting, full analysis flow

### CI and test-driven development

Every pull request and push to `main` runs `.github/workflows/ci.yml`: `pytest` on Python 3.11 and 3.12 with a coverage floor (`--cov-fail-under=70`, just below CI's measured 70.6%; raise it as coverage grows toward the 100% goal, never lower it). Local runs can report a few points lower than CI; #46 tracks why. To see coverage locally:

```bash
pytest --cov=src --cov-report=term-missing
```

Work is test-first: write a failing test, then the code that makes it pass. `.github/workflows/tests-required.yml` enforces the visible part: a PR that changes `src/` must also change `tests/` or `evals/`. For a change that truly needs no test, add the `no-tests-needed` label and explain why in the PR.

`main` is protected: changes land only through a pull request with green CI. Every PR also gets a Claude Code review (`.github/workflows/claude-code-review.yml`).

---

## Project Structure

```
ticket-automation-tool/
├── src/
│   ├── __init__.py
│   ├── cli.py              # Click-based CLI — entry point for all commands
│   ├── cache.py            # Local JSON cache for analysis results
│   ├── github_client.py    # GitHub REST API — issues, labels, comments
│   ├── devin_client.py     # Devin API — session creation, polling, parsing
│   ├── analyzer.py         # Orchestration — analysis, formatting, caching
│   ├── models.py           # Data models (TicketAnalysis, AnalysisSummary)
│   └── answer_key.py       # Loads and validates evals/answer_key.json
├── evals/
│   └── answer_key.json     # Expected triage for each calculator-demo issue
├── docs/
│   ├── brief.md            # Engagement brief: client, problem, success metrics, scope
│   └── decisions/          # Decision records (NNN-title.md): context, options, choice and why
├── tests/
│   ├── __init__.py
│   ├── test_answer_key.py
│   ├── test_github_client.py
│   ├── test_devin_client.py
│   └── test_analyzer.py
├── requirements.txt         # click, requests
├── requirements-dev.txt     # pytest
├── setup.py                 # console_scripts entry point: ticket-analyzer
├── .env.example             # Template for environment variables
├── .gitignore
└── README.md
```

---

## Next Steps

These features are planned for future releases:

- **Knowledge Store** (`knowledge.py`, `knowledge_store.json`) — Local learning across runs. The tool would remember past analyses and improve recommendations over time by building a local database of issue patterns, fix outcomes, and confidence calibration.

- **GitHub Actions Weekly Workflow** (`.github/workflows/weekly_analysis.yml`) — Automated weekly runs. A scheduled GitHub Action that runs `ticket-analyzer analyze` every week and posts the summary to the tracking issue automatically — no manual execution needed.
