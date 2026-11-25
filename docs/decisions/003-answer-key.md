# 003: How the answer key is judged

**Status:** accepted (#24)

## Context

The M2 eval scores the triage against `evals/answer_key.json`, so the key is the definition of "right". Two of the seven demo issues report crashes that don't happen. "Division by zero crashes the program" and "Empty input crashes the program" both just print "Invalid input", because `main()` catches every exception. The calculator-demo README also lists an intended category for each issue. A key copied from it would reward a model for believing the report rather than checking the code.

## Options

1. **Judge by the report alone.** It's quick to write, and it matches the original README. But it teaches the eval to reward a model that never looks at the code, which is the exact failure the tool exists to prevent.
2. **Judge against the code at `demo-baseline`.** Each entry says whether the report reproduces and what the real defect is. That takes more work, and it rewards triage that checks its claims.

## Choice

Option 2. Each entry records the type, action and priority, plus a reason that says whether the report reproduces and why the action is safe or not. The rules:

- **`automate`**: the report reproduces (or the real defect is clear), the expected behaviour is stated, and the fix is local with a test to prove it.
- **`engineer_review`**: the fix needs a design choice (the parser rework for precedence, parentheses, negatives and exponents), or the change is a policy call (raising the minimum Python version). A proposal that looks like a one-line fix but is unsafe (replacing the parser with `eval()`) is `engineer_review`, never `automate`. These are the cases the unsafe-automation metric exists for.
- **`needs_more_info`**: the report doesn't reproduce, or the request is too vague to build.
- **Priority**:
  - `high`: silently wrong answers.
  - `medium`: a crash, or an error on input users normally type.
  - `low`: a minor inconvenience with an obvious workaround, cleanups with no user impact, and anything vague or non-reproducing.
- **Duplicates** get the same type, action and priority as the original, plus `duplicate_of` naming it (always the original, never another duplicate). The triage schema has no "duplicate" action yet. Recording it now lets the M2 eval score duplicate detection when the triage can report it.

Two entries differ from what calculator-demo's README implies:

- **Division by zero:** still `automate`, because the unhelpful message is a real, well-specified defect. Priority is `medium`, not high, because nothing crashes.
- **Empty input:** `needs_more_info`, `low`. The current behaviour already meets the report's stated expectation.

## Consequences

- **The set has 23 issues (#25):** clear and vague reports, three duplicates, reports that don't reproduce, cleanups, features and two unsafe "easy" changes.
- **Entries are keyed by title** (see [002](002-demo-reset.md)), and a test checks that the key covers exactly the titles in calculator-demo's `demo/issues.json`. CI checks out that file; locally the test runs when `../calculator-demo` exists.
- **The key needs updating when the demo code changes.** When the `demo-baseline` tag moves, recheck every reason.
- **Priority is the most subjective field**, which is why its target in [001](001-success-metrics-and-targets.md) is lower.
- **calculator-demo's README contradicts the key and leaks the intended categories.** #48 removes them before the first eval.
