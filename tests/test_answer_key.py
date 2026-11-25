"""Tests for the eval answer key (evals/answer_key.json) and its loader."""

import json
import os
from pathlib import Path

import pytest

from src.answer_key import (
    AnswerKeyError,
    ExpectedTriage,
    compare_titles,
    load_answer_key,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ANSWER_KEY = REPO_ROOT / "evals" / "answer_key.json"


def entry(**overrides):
    base = {
        "title": "Division by zero crashes the program",
        "type": "bug",
        "action": "automate",
        "priority": "medium",
        "reason": "One-function fix with a clear expected message.",
    }
    base.update(overrides)
    return base


def write_key(tmp_path, entries):
    path = tmp_path / "answer_key.json"
    path.write_text(json.dumps({"issues": entries}))
    return path


def test_load_answer_key_returns_entries_by_title(tmp_path):
    key = load_answer_key(write_key(tmp_path, [entry()]))
    assert key == {
        "Division by zero crashes the program": ExpectedTriage(
            title="Division by zero crashes the program",
            type="bug",
            action="automate",
            priority="medium",
            reason="One-function fix with a clear expected message.",
        )
    }


@pytest.mark.parametrize("field,value", [
    ("type", "question"),
    ("action", "fix_it"),
    ("priority", "urgent"),
])
def test_load_answer_key_rejects_values_outside_the_triage_schema(tmp_path, field, value):
    with pytest.raises(AnswerKeyError, match=value):
        load_answer_key(write_key(tmp_path, [entry(**{field: value})]))


def test_load_answer_key_rejects_missing_fields(tmp_path):
    bad = entry()
    del bad["priority"]
    with pytest.raises(AnswerKeyError, match="priority"):
        load_answer_key(write_key(tmp_path, [bad]))


def test_load_answer_key_requires_a_reason(tmp_path):
    with pytest.raises(AnswerKeyError, match="reason"):
        load_answer_key(write_key(tmp_path, [entry(reason="  ")]))


def test_load_answer_key_rejects_duplicate_titles(tmp_path):
    with pytest.raises(AnswerKeyError, match="Duplicate"):
        load_answer_key(write_key(tmp_path, [entry(), entry()]))


def test_load_answer_key_wraps_unreadable_files(tmp_path):
    path = tmp_path / "answer_key.json"
    path.write_text("{oops")
    with pytest.raises(AnswerKeyError, match="answer_key.json"):
        load_answer_key(path)


def test_compare_titles_reports_both_directions():
    key = {"A": None, "B": None}
    missing, extra = compare_titles(key, ["B", "C"])
    assert missing == ["C"]  # demo issue with no expected answer
    assert extra == ["A"]  # answer for an issue that isn't in the demo


def test_repo_answer_key_is_valid():
    key = load_answer_key(ANSWER_KEY)
    assert len(key) >= 7


def demo_issue_set_path():
    demo_dir = os.environ.get("CALCULATOR_DEMO_DIR", str(REPO_ROOT.parent / "calculator-demo"))
    return Path(demo_dir) / "demo" / "issues.json"


@pytest.mark.skipif(
    not demo_issue_set_path().exists() and not os.environ.get("CI"),
    reason="calculator-demo isn't checked out next to this repo (CI always checks it out)",
)
def test_answer_key_covers_exactly_the_demo_issue_set():
    titles = [i["title"] for i in json.loads(demo_issue_set_path().read_text())["issues"]]
    missing, extra = compare_titles(load_answer_key(ANSWER_KEY), titles)
    assert missing == [], f"Demo issues with no expected triage: {missing}"
    assert extra == [], f"Answer-key entries with no demo issue: {extra}"
