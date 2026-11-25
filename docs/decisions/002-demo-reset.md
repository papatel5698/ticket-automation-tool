# 002: How the demo reset works

**Status:** accepted (#23, papatel5698/calculator-demo#53)

## Context

Every demo changes calculator-demo: fix PRs remove the intentional bugs, and issues get closed, labeled and commented on. Until now, resetting meant fixing and re-introducing bugs by hand (calculator-demo #43, #47, #51). By November the division bug had been fixed for good and only 4 of 7 issues were still open, so the demo no longer matched its own README. Evals (M2) and the live demo (M4) both need the same starting state every time.

## Options

**Where the buggy code comes from**
1. **A git tag (`demo-baseline`)** on the commit with the intended bugs; the reset makes `src/` and `tests/` match it.
2. **A copy of the buggy files** in a `demo/` folder. That puts two copies of the code in the repo the triage reads, and a fix agent might "fix" the copy.
3. **Force-push `main` back to a known commit.** This is simple, but it destroys history, including later changes to workflows, scripts and docs.

**How the issues come back**
1. **Reopen** the closed originals. Issue numbers stay stable, but old triage comments and labels remain, and reopening fires `issues.reopened`, not `issues.opened`.
2. **Recreate** fresh copies and close everything that was open before. The copies are clean, and they fire `issues.opened` exactly as a real new issue would. Numbers grow with every reset.

## Choice

- **Code: tag + restore commit (option 1).** The reset is a normal commit on `main` ("Reset demo code to demo-baseline"), so history stays readable and nothing outside `src/` and `tests/` is touched. When the demo itself should change, the tag moves; calculator-demo's README has the commands.
- **Issues: recreate (option 2).** The tool must work on brand-new issues, so the demo should start with brand-new issues. Leftover triage comments would make re-runs look like updates rather than first triage.
- **Issues are matched by title, not number.** The answer key (#24) and evals (M2) key on titles. The reset rejects duplicate titles. A hidden ID in the issue body was considered and rejected: the model would see it, and a telling ID ("vague-crash") would leak the expected answer.
- **Open new issues before closing old ones.** If GitHub fails partway through, the worst case is duplicates (a rerun cleans them up), never a repo with no open issues.
- **Check before changing anything.** The issue set is validated first, and the code reset refuses unless `main` is clean and matches `origin/main`. Dry runs apply the same checks.
- **Script first, Action as a wrapper.** `scripts/reset_demo.py` works locally and in CI; the "Reset demo" `workflow_dispatch` Action just runs it. `--dry-run` shows the plan before anything changes.

## Consequences

- **Pull requests are not touched.** Leftover fix PRs are closed by hand; automating that risks closing real work.
- **Issues created by the Action's `GITHUB_TOKEN` don't trigger other workflows.** Once the triage Action exists (M4), the reset needs a PAT or GitHub App token if it should kick off triage. Each full reset would then cost about $0.06 per issue in triage: about $0.42 for today's 7 issues, about $1.50 once #25 grows the set to 25. That matters under the $50/month cap.
- **Branch protection on calculator-demo's `main`** will need a bypass for the reset's direct push, or the reset will have to open a PR instead.
