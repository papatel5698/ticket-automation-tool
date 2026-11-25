# 004: Coverage target

**Status:** accepted (#46)

## Context

Coverage was 63–72% depending on where you ran it, and the CI floor was 70% (60% until #24). `cli.py`, the command people actually run, had no tests at all. The local and CI numbers disagreed because the tests read and wrote the repo's real `.cache/analysis_cache.json`. After the first local run, later runs found a cached entry and skipped the uncached code paths, so a local run reported less than CI, which always starts clean.

## Options

1. **Keep a modest floor (70–80%)** and test what feels important. That's the usual compromise, but it leaves the choice of what to skip to whoever is in a hurry.
2. **Aim for 100% line coverage**, with every exclusion justified in the code. That costs more test-writing up front, but untested code becomes visible and deliberate.

## Choice

Option 2, approached gradually:

- **The floor ratchets.** `--cov-fail-under` sits just below the current level (now 97%) and is raised whenever coverage rises. It is never lowered.
- **New code lands fully covered**, test-first.
- **Exclusions need a reason on the same line**, e.g. `# pragma: no cover - entry point; tests call cli() via CliRunner`. Today the only exclusion is the `if __name__ == "__main__"` guard in `cli.py`.
- **`devin_client.py` is the one known gap** (81%). It is deleted in M3, so tests written for it now would be thrown away.
- **Tests never touch real state.** An autouse fixture in `tests/conftest.py` gives every test its own empty cache directory, and `tests/test_test_isolation.py` guards that.

## Consequences

- **This is line coverage; branch coverage is off.** It may be worth turning on once line coverage reaches 100%.
- **100% line coverage proves every line runs under test, not that the tests check the right things.** Assertions still have to be meaningful; review looks at them.
- **The characterization tests for `cli.py` and the error paths describe current behaviour.** When M3 replaces Devin, they show exactly what changed.
- **Removing `devin_client.py` in M3 should bring coverage close to 100%,** and the floor rises with it.
