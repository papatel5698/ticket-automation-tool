import os
import sys
import warnings
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import click
from src import github_client, devin_client, analyzer


def _progress_callback(event, total, completed=0, issue_num=None, detail=None,
                       cached_count=0):
    """Display progress during parallel analysis."""
    if event == "start":
        if total == 0:
            click.echo("No open issues found.")
        elif cached_count == total:
            click.echo(f"Loading {total} cached result{'s' if total != 1 else ''}...")
        elif cached_count > 0:
            click.echo(f"Analyzing {total - cached_count} issue{'s' if (total - cached_count) != 1 else ''} "
                       f"in parallel ({cached_count} cached)...")
        else:
            click.echo(f"Analyzing {total} issue{'s' if total != 1 else ''} in parallel...")
    elif event == "session_creating":
        click.echo(f"  #{issue_num} Creating Devin session...")
    elif event == "session_waiting":
        click.echo(f"  #{issue_num} Waiting for analysis...")
    elif event == "done":
        click.echo(f"  [{completed}/{total}] #{issue_num} Done - {detail}")
    elif event == "error":
        click.echo(f"  [{completed}/{total}] #{issue_num} FAILED: {detail}")


@click.group()
def cli():
    """Ticket Analyzer - Analyze open GitHub issues using Devin AI."""
    pass


@cli.command()
@click.option("--token", envvar="DEVIN_API_TOKEN", help="Devin API token.")
@click.option("--github-token", envvar="GITHUB_TOKEN", help="GitHub API token.")
@click.option("--repo", envvar="GITHUB_REPO", help="Target repo (owner/repo).")
@click.option("--top", type=int, default=None,
              help="Override top-N ticket count. Does not persist.")
@click.option("--action", type=click.Choice(["automate", "engineer_review", "needs_more_info"]),
              default=None, help="Filter by recommended action.")
@click.option("--type", "ticket_type",
              type=click.Choice(["bug", "feature", "cleanup"]),
              default=None, help="Filter by ticket type.")
@click.option("--priority", type=click.Choice(["high", "medium", "low"]),
              default=None, help="Filter by priority.")
@click.option("--ticket", type=int, default=None,
              help="Analyze a single ticket by issue number.")
@click.option("--no-cache", is_flag=True, default=False,
              help="Skip cache and re-analyze all issues from scratch.")
def analyze(token, github_token, repo, top, action, ticket_type,
            priority, ticket, no_cache):
    """Analyze open GitHub issues and generate a summary."""
    if not token:
        click.echo("Error: Devin API token required. Set DEVIN_API_TOKEN or use --token.")
        raise SystemExit(1)
    if not github_token:
        click.echo("Error: GitHub token required. Set GITHUB_TOKEN or use --github-token.")
        raise SystemExit(1)
    if not repo:
        click.echo("Error: Repository required. Set GITHUB_REPO or use --repo.")
        raise SystemExit(1)

    # Single ticket mode
    if ticket is not None:
        issue = github_client.get_issue(repo, ticket, github_token)
        analysis = analyzer.analyze_single_ticket(issue, github_token, token, repo)
        click.echo(analyzer.format_single_ticket(analysis))
        return

    # Full analysis mode
    filters = {}
    if action:
        filters["action"] = action
    if ticket_type:
        filters["type"] = ticket_type
    if priority:
        filters["priority"] = priority

    cli_output, analyses, summary, top_tickets = analyzer.run_full_analysis(
        github_token, token, repo,
        top_n=top,
        filters=filters if filters else None,
        progress_callback=_progress_callback,
        use_cache=not no_cache,
    )

    click.echo(cli_output)


@cli.command()
@click.option("--token", envvar="DEVIN_API_TOKEN", help="Devin API token.")
@click.option("--github-token", envvar="GITHUB_TOKEN", help="GitHub API token.")
@click.option("--repo", envvar="GITHUB_REPO", help="Target repo (owner/repo).")
@click.option("--ticket", type=int, required=True,
              help="Issue number to automate.")
def automate(token, github_token, repo, ticket):
    """Trigger Devin to resolve a ticket and open a PR."""
    if not token:
        click.echo("Error: Devin API token required. Set DEVIN_API_TOKEN or use --token.")
        raise SystemExit(1)
    if not github_token:
        click.echo("Error: GitHub token required. Set GITHUB_TOKEN or use --github-token.")
        raise SystemExit(1)
    if not repo:
        click.echo("Error: Repository required. Set GITHUB_REPO or use --repo.")
        raise SystemExit(1)

    click.echo(f"Fetching issue #{ticket}...")
    issue = github_client.get_issue(repo, ticket, github_token)
    click.echo(f"Creating Devin session to fix: {issue['title']}")

    session = devin_client.create_automation_session(token, issue, repo)
    session_id = session.get("session_id")
    click.echo(f"Devin session created: {session_id}")
    click.echo("Waiting for Devin to complete...")

    result = devin_client.wait_for_session(token, session_id)
    status = result.get("status_enum", "unknown")

    # Terminate the session to free up Devin resources
    devin_client.terminate_session(token, session_id)

    if status == "finished":
        click.echo("Devin has completed the fix and opened a PR!")
        pr_url = result.get("pr_url", "Check the Devin dashboard for the PR link.")
        click.echo(f"PR: {pr_url}")
    else:
        click.echo(f"Devin session ended with status: {status}")
        click.echo("Check the Devin dashboard for details.")


@cli.command(name="clear-cache")
def clear_cache():
    """Clear the local analysis cache."""
    from src import cache as cache_module
    cache_module.clear_cache()
    click.echo("Analysis cache cleared.")


if __name__ == "__main__":
    cli()
