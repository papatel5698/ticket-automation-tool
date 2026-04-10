import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.models import TicketAnalysis, AnalysisSummary
from src import github_client, devin_client, cache


def generate_summary(analyses):
    """Create an aggregate summary from a list of TicketAnalysis objects."""
    counts_by_type = {}
    counts_by_action = {}
    counts_by_priority = {}

    for a in analyses:
        counts_by_type[a.type] = counts_by_type.get(a.type, 0) + 1
        counts_by_action[a.action] = counts_by_action.get(a.action, 0) + 1
        counts_by_priority[a.priority] = counts_by_priority.get(a.priority, 0) + 1

    return AnalysisSummary(
        total_count=len(analyses),
        counts_by_type=counts_by_type,
        counts_by_action=counts_by_action,
        counts_by_priority=counts_by_priority,
    )


def generate_top_n(analyses, n, filters=None):
    """Sort analyses by priority then confidence, apply filters, return top N."""
    priority_order = {"high": 0, "medium": 1, "low": 2}
    sorted_analyses = sorted(
        analyses,
        key=lambda a: (priority_order.get(a.priority, 3), -a.confidence),
    )

    if filters:
        if filters.get("action"):
            sorted_analyses = [a for a in sorted_analyses if a.action == filters["action"]]
        if filters.get("type"):
            sorted_analyses = [a for a in sorted_analyses if a.type == filters["type"]]
        if filters.get("priority"):
            sorted_analyses = [a for a in sorted_analyses if a.priority == filters["priority"]]

    return sorted_analyses[:n]


def format_cli_output(summary, top_n):
    """Format analysis results for terminal display."""
    lines = []
    lines.append("Tickets Summary")
    lines.append("\u2500" * 15)

    type_parts = ", ".join(f"{v} {k}s" for k, v in summary.counts_by_type.items())
    action_parts = ", ".join(
        f"{v} {k.replace('_', ' ')}" for k, v in summary.counts_by_action.items()
    )
    priority_parts = ", ".join(f"{v} {k}" for k, v in summary.counts_by_priority.items())

    lines.append(f"Total tickets:        {summary.total_count}")
    lines.append(f"By type:              {type_parts}")
    lines.append(f"By action:            {action_parts}")
    lines.append(f"By priority:          {priority_parts}")
    lines.append("")

    if top_n:
        lines.append(f"Top {len(top_n)} Tickets")
        lines.append("\u2500" * 14)
        lines.append(
            f"{'#':<4}| {'Priority':<10}| {'Type':<10}| {'Action':<18}| "
            f"{'Confidence':<12}| {'Complexity':<12}| Title"
        )
        for a in top_n:
            lines.append(
                f"{a.issue_number:<4}| {a.priority:<10}| {a.type:<10}| {a.action:<18}| "
                f"{a.confidence}%{'':<10}| {a.complexity:<12}| {a.title}"
            )

    return "\n".join(lines)


def format_single_ticket(analysis):
    """Format a single ticket analysis for terminal display."""
    lines = []
    header = f"Ticket #{analysis.issue_number}: {analysis.title}"
    lines.append(header)
    lines.append("\u2500" * len(header))
    lines.append(f"Type:                 {analysis.type}")
    lines.append(f"Action:               {analysis.action}")
    lines.append(f"Action Reasoning:     {analysis.action_reasoning}")
    lines.append(f"Confidence:           {analysis.confidence}%")
    lines.append(f"Priority:             {analysis.priority}")
    lines.append(f"Complexity:           {analysis.complexity}")
    lines.append(f"Complexity Reasoning: {analysis.complexity_reasoning}")
    lines.append(f"Description:          {analysis.description}")
    return "\n".join(lines)


def format_github_comment(summary, top_n):
    """Format analysis results as a markdown comment for GitHub."""
    lines = []
    lines.append("## Ticket Analysis Summary")
    lines.append("")
    lines.append(f"**Total tickets:** {summary.total_count}")
    lines.append("")
    lines.append("### By Type")
    for k, v in summary.counts_by_type.items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")
    lines.append("### By Recommended Action")
    for k, v in summary.counts_by_action.items():
        lines.append(f"- **{k.replace('_', ' ')}**: {v}")
    lines.append("")
    lines.append("### By Priority")
    for k, v in summary.counts_by_priority.items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")

    if top_n:
        lines.append(f"### Top {len(top_n)} Tickets")
        lines.append("")
        lines.append(
            "| # | Priority | Type | Action | Confidence | Complexity | Title |"
        )
        lines.append(
            "|---|----------|------|--------|------------|------------|-------|"
        )
        for a in top_n:
            lines.append(
                f"| {a.issue_number} | {a.priority} | {a.type} | "
                f"{a.action} | {a.confidence}% | {a.complexity} | {a.title} |"
            )

    lines.append("")
    lines.append(f"*Generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*")
    return "\n".join(lines)


def analyze_single_ticket(issue, github_token, devin_token, repo,
                          progress_callback=None):
    """Deep-dive analysis of one ticket using Devin."""
    issue_num = issue["number"]

    if progress_callback:
        progress_callback("session_creating", 0, 0, issue_num)

    session = devin_client.create_analysis_session(devin_token, issue, repo)
    session_id = session.get("session_id")

    if progress_callback:
        progress_callback("session_waiting", 0, 0, issue_num, session_id)

    result = devin_client.wait_for_session(devin_token, session_id)
    parsed = devin_client.parse_analysis_result(result)

    # Terminate the session to free up Devin resources
    devin_client.terminate_session(devin_token, session_id)

    return TicketAnalysis(
        issue_number=issue_num,
        title=issue["title"],
        type=parsed.get("type", "unknown"),
        action=parsed.get("action", "needs_more_info"),
        action_reasoning=parsed.get("action_reasoning", ""),
        confidence=int(parsed.get("confidence", 0)),
        priority=parsed.get("priority", "low"),
        complexity=parsed.get("complexity", "unknown"),
        complexity_reasoning=parsed.get("complexity_reasoning", ""),
        description=parsed.get("description", ""),
    )


def _staggered_analyze(issue, github_token, devin_token, repo, delay,
                       progress_callback=None):
    """Analyze a single ticket with a staggered start delay to avoid 429s."""
    if delay > 0:
        time.sleep(delay)
    return analyze_single_ticket(issue, github_token, devin_token, repo,
                                 progress_callback=progress_callback)


def run_full_analysis(config, github_token, devin_token, repo,
                      top_n=None, filters=None, progress_callback=None,
                      use_cache=True):
    """Main entry point: fetch issues, analyze them, post summary."""
    top_n_count = top_n if top_n is not None else config.get("top_n", 10)

    # Fetch all open issues
    issues = github_client.get_open_issues(repo, github_token)

    # Split issues into cached and uncached
    analyses = []
    uncached_issues = []
    total = len(issues)

    if use_cache:
        for issue in issues:
            cached = cache.get_cached_analysis(issue)
            if cached is not None:
                analyses.append(cached)
            else:
                uncached_issues.append(issue)
    else:
        uncached_issues = issues

    cached_count = total - len(uncached_issues)

    if progress_callback:
        progress_callback("start", total, cached_count=cached_count)

    # Analyze uncached issues with Devin (in parallel with staggered starts)
    if uncached_issues:
        max_workers = min(5, len(uncached_issues))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_issue = {}
            for idx, issue in enumerate(uncached_issues):
                delay = idx * 2  # 2-second stagger between submissions
                future = executor.submit(
                    _staggered_analyze, issue, github_token, devin_token, repo,
                    delay, progress_callback=progress_callback
                )
                future_to_issue[future] = issue

            completed = cached_count
            for future in as_completed(future_to_issue):
                issue = future_to_issue[future]
                completed += 1
                try:
                    analysis = future.result()
                    analyses.append(analysis)
                    if use_cache:
                        cache.cache_analysis(issue, analysis)
                    if progress_callback:
                        progress_callback("done", total, completed, issue["number"], issue["title"])
                except Exception as e:
                    if progress_callback:
                        progress_callback("error", total, completed, issue["number"], str(e))
                    else:
                        print(f"Warning: Failed to analyze issue #{issue['number']}: {e}")

    # Generate summary and top-N
    summary = generate_summary(analyses)
    top_tickets = generate_top_n(analyses, top_n_count, filters)

    # Post summary to GitHub Discussions (new discussion each run)
    try:
        comment_body = format_github_comment(summary, top_tickets)
        github_client.create_summary_discussion(repo, comment_body, github_token)
    except Exception as e:
        print(f"Warning: Failed to post summary to GitHub Discussion: {e}")

    # Format CLI output
    cli_output = format_cli_output(summary, top_tickets)

    return cli_output, analyses, summary, top_tickets
