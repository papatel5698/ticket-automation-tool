import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from src.analyzer import (
    identify_stale_issues, generate_summary, generate_top_n,
    format_cli_output, format_single_ticket, format_github_comment,
    analyze_single_ticket, run_full_analysis,
)
from src.models import TicketAnalysis, AnalysisSummary


def _make_issue(number, title, days_ago):
    updated = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    return {
        "number": number,
        "title": title,
        "updated_at": updated,
        "labels": [],
    }


def _make_analysis(number, title, type_="bug", action="automate",
                   confidence=90, priority="high", complexity="low"):
    return TicketAnalysis(
        issue_number=number,
        title=title,
        type=type_,
        action=action,
        action_reasoning="Test reasoning",
        confidence=confidence,
        priority=priority,
        complexity=complexity,
        complexity_reasoning="Test complexity reasoning",
        description="Test description",
    )


class TestIdentifyStaleIssues:
    def test_identifies_stale_issues(self):
        issues = [
            _make_issue(1, "Old bug", 40),
            _make_issue(2, "Recent bug", 5),
            _make_issue(3, "Very old", 100),
        ]
        stale = identify_stale_issues(issues, 30)
        assert len(stale) == 2
        assert stale[0]["number"] == 1
        assert stale[1]["number"] == 3

    def test_no_stale_issues(self):
        issues = [
            _make_issue(1, "Fresh", 1),
            _make_issue(2, "Recent", 10),
        ]
        stale = identify_stale_issues(issues, 30)
        assert len(stale) == 0

    def test_zero_stale_days(self):
        issues = [
            _make_issue(1, "Any issue", 0),
        ]
        stale = identify_stale_issues(issues, 0)
        assert len(stale) == 1

    def test_empty_issues_list(self):
        stale = identify_stale_issues([], 30)
        assert len(stale) == 0


class TestGenerateSummary:
    def test_generates_correct_counts(self):
        analyses = [
            _make_analysis(1, "Bug 1", type_="bug", action="automate", priority="high"),
            _make_analysis(2, "Bug 2", type_="bug", action="engineer_review", priority="medium"),
            _make_analysis(3, "Feature", type_="feature", action="automate", priority="low"),
        ]
        summary = generate_summary(analyses)
        assert summary.total_count == 3
        assert summary.counts_by_type == {"bug": 2, "feature": 1}
        assert summary.counts_by_action == {"automate": 2, "engineer_review": 1}
        assert summary.counts_by_priority == {"high": 1, "medium": 1, "low": 1}

    def test_empty_analyses(self):
        summary = generate_summary([])
        assert summary.total_count == 0
        assert summary.counts_by_type == {}


class TestGenerateTopN:
    def test_sorts_by_priority_then_confidence(self):
        analyses = [
            _make_analysis(1, "Low", priority="low", confidence=99),
            _make_analysis(2, "High 1", priority="high", confidence=80),
            _make_analysis(3, "High 2", priority="high", confidence=95),
        ]
        top = generate_top_n(analyses, 10)
        assert top[0].issue_number == 3  # high priority, 95% confidence
        assert top[1].issue_number == 2  # high priority, 80% confidence
        assert top[2].issue_number == 1  # low priority

    def test_limits_to_n(self):
        analyses = [_make_analysis(i, f"Issue {i}") for i in range(20)]
        top = generate_top_n(analyses, 5)
        assert len(top) == 5

    def test_filters_by_action(self):
        analyses = [
            _make_analysis(1, "Auto", action="automate"),
            _make_analysis(2, "Review", action="engineer_review"),
        ]
        top = generate_top_n(analyses, 10, {"action": "automate"})
        assert len(top) == 1
        assert top[0].action == "automate"

    def test_filters_by_type(self):
        analyses = [
            _make_analysis(1, "Bug", type_="bug"),
            _make_analysis(2, "Feature", type_="feature"),
        ]
        top = generate_top_n(analyses, 10, {"type": "bug"})
        assert len(top) == 1
        assert top[0].type == "bug"

    def test_filters_by_priority(self):
        analyses = [
            _make_analysis(1, "High", priority="high"),
            _make_analysis(2, "Low", priority="low"),
        ]
        top = generate_top_n(analyses, 10, {"priority": "high"})
        assert len(top) == 1
        assert top[0].priority == "high"

    def test_combined_filters(self):
        analyses = [
            _make_analysis(1, "A", type_="bug", action="automate", priority="high"),
            _make_analysis(2, "B", type_="bug", action="engineer_review", priority="high"),
            _make_analysis(3, "C", type_="feature", action="automate", priority="high"),
        ]
        top = generate_top_n(analyses, 10, {"type": "bug", "action": "automate"})
        assert len(top) == 1
        assert top[0].issue_number == 1


class TestFormatCliOutput:
    def test_includes_summary_info(self):
        summary = AnalysisSummary(
            total_count=3,
            counts_by_type={"bug": 2, "feature": 1},
            counts_by_action={"automate": 2, "engineer_review": 1},
            counts_by_priority={"high": 1, "medium": 1, "low": 1},
        )
        top = [_make_analysis(1, "Test Bug")]
        output = format_cli_output(summary, top)
        assert "Stale Tickets Summary" in output
        assert "Total stale tickets:  3" in output
        assert "2 bugs" in output

    def test_includes_top_n_table(self):
        summary = AnalysisSummary(total_count=1, counts_by_type={}, counts_by_action={}, counts_by_priority={})
        top = [_make_analysis(1, "Bug 1")]
        output = format_cli_output(summary, top)
        assert "Bug 1" in output
        assert "Priority" in output


class TestFormatSingleTicket:
    def test_formats_single_ticket(self):
        analysis = _make_analysis(1, "Division by zero", action="automate")
        output = format_single_ticket(analysis)
        assert "Ticket #1: Division by zero" in output
        assert "Type:" in output
        assert "Action:" in output
        assert "Confidence:" in output


class TestFormatGithubComment:
    def test_generates_markdown(self):
        summary = AnalysisSummary(
            total_count=2,
            counts_by_type={"bug": 2},
            counts_by_action={"automate": 2},
            counts_by_priority={"high": 2},
        )
        top = [_make_analysis(1, "Bug 1")]
        output = format_github_comment(summary, top)
        assert "## Stale Tickets Analysis Summary" in output
        assert "| # | Priority |" in output
        assert "Bug 1" in output


class TestAnalyzeSingleTicket:
    @patch("src.analyzer.devin_client")
    def test_returns_ticket_analysis(self, mock_devin):
        mock_devin.create_analysis_session.return_value = {"session_id": "abc"}
        mock_devin.wait_for_session.return_value = {"status_enum": "finished"}
        mock_devin.parse_analysis_result.return_value = {
            "type": "bug",
            "action": "automate",
            "action_reasoning": "Simple fix",
            "confidence": 95,
            "priority": "high",
            "complexity": "low",
            "complexity_reasoning": "One function change",
            "description": "Division by zero fix",
        }

        issue = {"number": 1, "title": "Div by zero", "body": "Crash"}
        result = analyze_single_ticket(issue, "gh_token", "devin_token", "owner/repo")

        assert isinstance(result, TicketAnalysis)
        assert result.type == "bug"
        assert result.action == "automate"
        assert result.confidence == 95


class TestRunFullAnalysis:
    @patch("src.analyzer.github_client")
    @patch("src.analyzer.devin_client")
    def test_full_analysis_flow(self, mock_devin, mock_github):
        # Setup mock issues
        old_date = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        mock_github.get_open_issues.return_value = [
            {"number": 1, "title": "Bug", "updated_at": old_date, "labels": []},
        ]
        mock_github.find_or_create_summary_discussion.return_value = "D_abc123"
        mock_github.post_discussion_comment.return_value = {"id": "DC_1"}
        mock_github.add_label.return_value = []

        # Setup mock Devin
        mock_devin.create_analysis_session.return_value = {"session_id": "abc"}
        mock_devin.wait_for_session.return_value = {"status_enum": "finished"}
        mock_devin.parse_analysis_result.return_value = {
            "type": "bug",
            "action": "automate",
            "action_reasoning": "Simple fix",
            "confidence": 90,
            "priority": "high",
            "complexity": "low",
            "complexity_reasoning": "Easy",
            "description": "Fix the bug",
        }

        config = {"stale_days": 30, "top_n": 10}
        cli_output, analyses, summary, top = run_full_analysis(
            config, "gh_token", "devin_token", "owner/repo"
        )

        assert len(analyses) == 1
        assert summary.total_count == 1
        assert "Stale Tickets Summary" in cli_output
        mock_github.add_label.assert_called_once()
