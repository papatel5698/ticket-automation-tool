"""The eval answer key: the expected triage for each calculator-demo issue.

Entries are keyed by issue title, because the demo reset recreates issues and
their numbers change every time (docs/decisions/002-demo-reset.md).
"""

import json
from dataclasses import dataclass
from pathlib import Path

TYPES = ("bug", "feature", "cleanup")
ACTIONS = ("automate", "engineer_review", "needs_more_info")
PRIORITIES = ("high", "medium", "low")
FIELDS = ("title", "type", "action", "priority", "reason")


class AnswerKeyError(ValueError):
    """The answer key is missing, unreadable or malformed."""


@dataclass(frozen=True)
class ExpectedTriage:
    title: str
    type: str
    action: str
    priority: str
    reason: str
    duplicate_of: str | None = None  # title of the original issue, if this is a duplicate


def load_answer_key(path: Path) -> dict[str, ExpectedTriage]:
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AnswerKeyError(f"Can't read answer key {path}: {error}") from None

    if not isinstance(data, dict):
        raise AnswerKeyError(f"{path}: expected a JSON object with an \"issues\" list")
    issues = data.get("issues", [])
    if not isinstance(issues, list):
        raise AnswerKeyError(f"{path}: \"issues\" must be a list")
    if not issues:
        raise AnswerKeyError(f"{path}: the answer key has no entries")

    key: dict[str, ExpectedTriage] = {}
    for i, raw in enumerate(issues, 1):
        if not isinstance(raw, dict):
            raise AnswerKeyError(f"Entry {i} must be an object")
        missing = [f for f in FIELDS if f not in raw]
        if missing:
            raise AnswerKeyError(f"Entry {i} is missing {', '.join(missing)}")
        not_text = [f for f in FIELDS if not isinstance(raw[f], str)]
        if not_text:
            raise AnswerKeyError(f"Entry {i}: {', '.join(not_text)} must be text")
        for field, allowed in (("type", TYPES), ("action", ACTIONS), ("priority", PRIORITIES)):
            if raw[field] not in allowed:
                raise AnswerKeyError(
                    f"Entry {raw['title']!r}: {field} {raw[field]!r} isn't one of {', '.join(allowed)}"
                )
        if not raw["reason"].strip():
            raise AnswerKeyError(f"Entry {raw['title']!r} needs a reason")
        if raw["title"] in key:
            raise AnswerKeyError(f"Duplicate title: {raw['title']!r}")
        duplicate_of = raw.get("duplicate_of")
        if duplicate_of is not None and not isinstance(duplicate_of, str):
            raise AnswerKeyError(f"Entry {raw['title']!r}: duplicate_of must be a title")
        key[raw["title"]] = ExpectedTriage(
            **{f: raw[f] for f in FIELDS}, duplicate_of=duplicate_of
        )

    for item in key.values():
        if item.duplicate_of is None:
            continue
        if item.duplicate_of == item.title or item.duplicate_of not in key:
            raise AnswerKeyError(
                f"Entry {item.title!r}: duplicate_of {item.duplicate_of!r} isn't another entry"
            )
        if key[item.duplicate_of].duplicate_of is not None:
            raise AnswerKeyError(
                f"Entry {item.title!r}: duplicate_of must name the original issue, "
                f"not another duplicate"
            )
    return key


def compare_titles(key: dict, issue_titles: list[str]) -> tuple[list[str], list[str]]:
    """Return (issues with no answer, answers with no issue)."""
    missing = [t for t in issue_titles if t not in key]
    extra = [t for t in key if t not in issue_titles]
    return missing, extra
