# Engagement brief

What this engagement is for, who it serves, how we'll know it worked, and what it won't do. Read this before the code.

## The client

A small product engineering team: four to six engineers, one engineering manager, no dedicated support or QA staff. Their product's issues live in a single GitHub repository. Customers, support and the engineers themselves all file issues there.

For this portfolio engagement the client's repository is [papatel5698/calculator-demo](https://github.com/papatel5698/calculator-demo), a small CLI calculator with deliberate bugs. Its issue set is being expanded to about 25 (clear bugs, vague reports, duplicates and risky-to-automate changes) in M1.

## The problem

The backlog has gone stale. Issues arrive faster than anyone reads them, and nobody owns triage, so it happens in bursts before planning or not at all. As a result:

- **Nobody knows what kind of work is sitting there.** Five-minute fixes sit next to multi-day refactors and reports too vague to act on, all looking the same in the issue list.
- **Senior time goes to sorting, not fixing.** The engineers who can judge an issue fastest are the ones who end up reading every ticket.
- **Reporters wait with no response.** A vague report ("it crashed yesterday") can sit for weeks before anyone asks for steps to reproduce it, by which time the reporter has moved on.
- **Easy wins don't get taken.** Small, well-described bugs stay open because nobody has flagged them as small.

## What we're delivering

A triage system installed on the client's repo:

1. **Sorts every new and stale issue** into a type (`bug`, `feature`, `cleanup`), an action (`automate`, `engineer_review`, `needs_more_info`), a priority and a complexity, and **explains its reasoning** in a comment on the issue.
2. **Opens fix PRs for the safe ones, only after a maintainer approves** with `/approve-fix`. Nothing is changed in the codebase without a human saying yes, and every fix arrives as a normal PR for normal review.
3. **Shows its value on a dashboard**: issues triaged, the action split, estimated hours saved, fix PRs opened and merged, and money spent.

It runs as a GitHub Action in the client's repo: one workflow file and one secret to install, no server to host.

**Where the code is today:** a Devin-based CLI (`ticket-analyzer`, described in the [README](../README.md)). This brief describes the target. M3 moves triage to Claude and M4 turns it into a GitHub Action.

## Who uses it

| Who | What they do with it |
|-----|----------------------|
| **Engineers** | Read the triage comment instead of the whole thread; pick up `automate` and `engineer_review` issues with a head start on the reasoning. |
| **Maintainers / tech lead** | Approve or reject fix PRs with `/approve-fix`; correct a triage label when it's wrong. |
| **Engineering manager** | Uses the dashboard to see backlog health, time saved and spend, and to decide whether the tool is worth keeping. |
| **Issue reporters** | Get a quick, specific request for more information when their report is too vague to act on. |

## Success metrics

We measure against an answer key: the expected triage for every demo issue (`evals/answer_key.json`, planned in M1). The targets below are starting points set before the first measurement. We'll revise them once the M2 evals give us a baseline, and say so when we do. Why these numbers: [decision 001](decisions/001-success-metrics-and-targets.md).

| Metric | How it's measured | Target |
|--------|-------------------|--------|
| **Action accuracy** | Share of issues where the action matches the answer key (`ticket-analyzer eval`, planned in M2) | ≥ 80% |
| **Unsafe automation** | Issues the answer key marks `engineer_review` or `needs_more_info` that the tool labels `automate` | 0 |
| **Type and priority accuracy** | Share matching the answer key | ≥ 80% type, ≥ 70% priority |
| **Cost per issue** | Anthropic API spend per triaged issue, from token counts in the eval | ≤ $0.10 (estimate: ~$0.06 on the starting model, Opus 5.5) |
| **Latency** | Time from issue opened to triage comment posted | ≤ 2 minutes |
| **Hours saved** | Issues triaged × an assumed 10 minutes of manual triage each, plus engineer time on merged fix PRs (assumed 30 minutes each). The dashboard shows the assumptions next to the number. | Reported, not targeted |

Unsafe automation is the metric that matters most. A wrong `needs_more_info` costs a reporter one extra comment; a wrong `automate` invites a maintainer to approve a risky change because the label said it was safe. The approval gate is the backstop, but the triage should not lean on it.

## Constraints

- **Budget:** a hard cap of $50/month on Anthropic API spend, shared with other projects. Triage must stay cheap per issue, and evals must be cheap enough to run on every prompt change.
- **Human in the loop:** no code changes without explicit maintainer approval.
- **GitHub-native:** runs where the team already works (issues, comments, labels, Actions). The dashboard is the only new place to look, and nobody needs it to use the triage.
- **Privacy:** issue titles, bodies and labels, plus relevant repository code, are sent to the Anthropic API, both for triage and for approved fixes. Triage results are stored in the dashboard's database. The optional Slack summary (M4) posts issue titles and triage results to the client's Slack. Nothing else leaves GitHub. The handoff docs (M5) spell out exactly what is sent and stored.
- **Small install:** a client should be able to install it on a new repo in under 30 minutes by following the install guide.

## Out of scope

- **Closing, assigning or editing issues.** The tool labels and comments; people decide what happens next.
- **Merging anything.** Fix PRs go through the client's normal review and CI.
- **Fixing complex or risky issues.** Anything labeled `engineer_review` is left to engineers, even if the model thinks it could try.
- **Other issue trackers** (Jira, Linear, Zendesk). GitHub Issues only.
- **A hosted service or GitHub App.** It runs as an Action in the client's repo. A GitHub App is a possible later step.
- **Multiple repositories per install.** One install per repo.
- **Learning from corrections automatically.** When a maintainer fixes a label, that's feedback for the next eval and prompt change, not online training.

## How we'll get there

The milestones in this repository's GitHub issues: a repeatable demo environment (M1), evals (M2), moving the triage from Devin to Claude (M3), running as a GitHub Action in the client's repo (M4), and the dashboard and handoff docs (M5). Each milestone ends with a short client-style update.
