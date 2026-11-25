"""Tests for the ticket-analyzer command line. All clients are mocked."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from src import cache, cli

CREDS = ["--token", "devin", "--github-token", "gh", "--repo", "o/r"]


@pytest.fixture
def runner(monkeypatch):
    for var in ("DEVIN_API_TOKEN", "GITHUB_TOKEN", "GITHUB_REPO"):
        monkeypatch.delenv(var, raising=False)
    return CliRunner()


# --- credentials -------------------------------------------------------------


@pytest.mark.parametrize("command", [["analyze"], ["automate", "--ticket", "1"]])
@pytest.mark.parametrize("missing,message", [
    ("--token", "Devin API token required"),
    ("--github-token", "GitHub token required"),
    ("--repo", "Repository required"),
])
def test_commands_exit_with_a_message_when_a_credential_is_missing(runner, command, missing, message):
    i = CREDS.index(missing)
    args = CREDS[:i] + CREDS[i + 2:]
    result = runner.invoke(cli.cli, command + args)
    assert result.exit_code == 1
    assert message in result.output


def test_credentials_can_come_from_the_environment(runner, monkeypatch):
    monkeypatch.setenv("DEVIN_API_TOKEN", "devin")
    monkeypatch.setenv("GITHUB_TOKEN", "gh")
    monkeypatch.setenv("GITHUB_REPO", "o/r")
    with patch.object(cli.analyzer, "run_full_analysis", return_value=("out", [], None, [])) as run:
        result = runner.invoke(cli.cli, ["analyze"])
    assert result.exit_code == 0
    assert run.call_args.args == ("gh", "devin", "o/r")


# --- analyze -----------------------------------------------------------------


def test_analyze_runs_the_full_analysis_and_prints_it(runner):
    with patch.object(cli.analyzer, "run_full_analysis",
                      return_value=("the report", [], None, [])) as run:
        result = runner.invoke(cli.cli, ["analyze"] + CREDS)

    assert result.exit_code == 0
    assert "the report" in result.output
    kwargs = run.call_args.kwargs
    assert kwargs["top_n"] is None
    assert kwargs["filters"] is None
    assert kwargs["use_cache"] is True
    assert kwargs["progress_callback"] is cli._progress_callback


def test_analyze_passes_filters_top_and_no_cache(runner):
    with patch.object(cli.analyzer, "run_full_analysis", return_value=("", [], None, [])) as run:
        result = runner.invoke(cli.cli, ["analyze", *CREDS, "--top", "5", "--action", "automate",
                                         "--type", "bug", "--priority", "high", "--no-cache"])

    assert result.exit_code == 0
    kwargs = run.call_args.kwargs
    assert kwargs["top_n"] == 5
    assert kwargs["filters"] == {"action": "automate", "type": "bug", "priority": "high"}
    assert kwargs["use_cache"] is False


def test_analyze_rejects_an_unknown_filter_value(runner):
    result = runner.invoke(cli.cli, ["analyze", *CREDS, "--action", "fix_everything"])
    assert result.exit_code == 2
    assert "fix_everything" in result.output


def test_analyze_single_ticket(runner):
    issue = {"number": 7, "title": "T"}
    with patch.object(cli.github_client, "get_issue", return_value=issue) as get_issue, \
         patch.object(cli.analyzer, "analyze_single_ticket", return_value="analysis") as single, \
         patch.object(cli.analyzer, "format_single_ticket", return_value="formatted") as fmt, \
         patch.object(cli.analyzer, "run_full_analysis") as full:
        result = runner.invoke(cli.cli, ["analyze", *CREDS, "--ticket", "7"])

    assert result.exit_code == 0
    assert "formatted" in result.output
    get_issue.assert_called_once_with("o/r", 7, "gh")
    single.assert_called_once_with(issue, "gh", "devin", "o/r")
    fmt.assert_called_once_with("analysis")
    full.assert_not_called()


# --- progress output ---------------------------------------------------------


@pytest.mark.parametrize("kwargs,expected", [
    (dict(event="start", total=0), "No open issues found."),
    (dict(event="start", total=1, cached_count=1), "Loading 1 cached result..."),
    (dict(event="start", total=3, cached_count=3), "Loading 3 cached results..."),
    (dict(event="start", total=3, cached_count=2), "Analyzing 1 issue in parallel (2 cached)..."),
    (dict(event="start", total=4, cached_count=1), "Analyzing 3 issues in parallel (1 cached)..."),
    (dict(event="start", total=1), "Analyzing 1 issue in parallel..."),
    (dict(event="start", total=2), "Analyzing 2 issues in parallel..."),
    (dict(event="session_creating", total=2, issue_num=4), "  #4 Creating Devin session..."),
    (dict(event="session_waiting", total=2, issue_num=4), "  #4 Waiting for analysis..."),
    (dict(event="done", total=2, completed=1, issue_num=4, detail="bug"), "  [1/2] #4 Done - bug"),
    (dict(event="error", total=2, completed=2, issue_num=4, detail="timeout"),
     "  [2/2] #4 FAILED: timeout"),
])
def test_progress_callback_messages(capsys, kwargs, expected):
    cli._progress_callback(**kwargs)
    assert capsys.readouterr().out == expected + "\n"


def test_progress_callback_ignores_unknown_events(capsys):
    cli._progress_callback("something_else", 1)
    assert capsys.readouterr().out == ""


# --- automate (Devin; removed in M3) -----------------------------------------


@pytest.mark.parametrize("final,expected", [
    ({"status_enum": "finished", "pr_url": "https://pr"}, "PR: https://pr"),
    ({"status_enum": "finished"}, "Check the Devin dashboard for the PR link."),
    ({"status_enum": "blocked"}, "Devin session ended with status: blocked"),
])
def test_automate_reports_the_session_outcome_and_terminates_it(runner, final, expected):
    with patch.object(cli.github_client, "get_issue", return_value={"title": "Fix me"}), \
         patch.object(cli.devin_client, "create_automation_session",
                      return_value={"session_id": "s1"}), \
         patch.object(cli.devin_client, "wait_for_session", return_value=final), \
         patch.object(cli.devin_client, "terminate_session") as terminate:
        result = runner.invoke(cli.cli, ["automate", *CREDS, "--ticket", "3"])

    assert result.exit_code == 0
    assert "Creating Devin session to fix: Fix me" in result.output
    assert expected in result.output
    terminate.assert_called_once_with("devin", "s1")


# --- clear-cache -------------------------------------------------------------


def test_clear_cache_removes_the_cache_file(runner):
    cache.save_cache({"k": {"v": 1}})
    result = runner.invoke(cli.cli, ["clear-cache"])
    assert result.exit_code == 0
    assert "Analysis cache cleared." in result.output
    assert cache.load_cache() == {}
