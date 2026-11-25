# 001: Success metrics and targets

**Status:** provisional (revisit after the first M2 eval run)

## Context

The [engagement brief](../brief.md) needs success metrics the client can check. The tool makes two kinds of mistakes with very different costs: under-automating (a fixable issue goes to an engineer, or a clear one gets a needless "please clarify") and over-automating (a risky issue is labeled `automate`). There's no baseline yet. The answer key (#24) and eval (M2) don't exist, so any number set now is a guess.

## Options

1. **Overall accuracy only.** Simple, but it treats every mistake the same, so a model that over-automates could still score well.
2. **Accuracy plus a separate unsafe-automation count.** Accuracy measures usefulness; the unsafe count measures the one error that erodes trust.
3. **Wait for a baseline before setting any targets.** Honest, but leaves the brief without a definition of success and makes it easy to move the goalposts after seeing the results.

## Choice

Option 2, with targets set now and marked provisional:

- **Action accuracy ≥ 80%**: high enough that maintainers trust the labels more often than not, low enough to be reachable on a deliberately tricky issue set (vague reports, duplicates, risky changes).
- **Unsafe automation = 0**: an `automate` label on an issue that needs a human invites a maintainer to approve a risky change because the tool called it safe. The `/approve-fix` gate catches it, but a triage tool that leans on its backstop isn't doing its job. The eval reports this separately from accuracy so it can't be averaged away.
- **Type ≥ 80%, priority ≥ 70%**: priority is the most subjective field, so it gets a lower bar.
- **≤ $0.10 per issue**: comfortably above the ~$0.06 estimate for Opus 5.5, and low enough that a 25-issue eval on every prompt change fits under the $50/month cap.
- **≤ 2 minutes latency**: a reporter should see the triage comment while they still have the issue open.
- **Hours saved: 10 minutes per triaged issue, 30 minutes per merged fix PR**: rough figures for reading an issue thread and deciding what it is, and for a small fix with a test. They are reported with the assumptions shown next to them, not targeted, because they can't be measured directly.
- **Install in under 30 minutes**: one workflow file and one secret should take that long including reading the guide. It keeps the install guide (M5) honest.

Setting targets before measuring (rather than option 3) means the first eval can fail them. If it does, we'll revise the targets in this record and say why, rather than quietly adjusting them.
