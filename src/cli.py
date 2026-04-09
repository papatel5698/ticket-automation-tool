import os
import click
from src import config as config_module
from src import github_client, devin_client, analyzer


@click.group()
def cli():
    """Ticket Analyzer - Analyze stale GitHub issues using Devin AI."""
    pass


@cli.command()
@click.option("--token", envvar="DEVIN_API_TOKEN", help="Devin API token.")
@click.option("--github-token", envvar="GITHUB_TOKEN", help="GitHub API token.")
@click.option("--repo", envvar="GITHUB_REPO", help="Target repo (owner/repo).")
@click.option("--stale-days", type=int, default=None,
              help="Override staleness threshold (days). Does not persist.")
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
def analyze(token, github_token, repo, stale_days, top, action, ticket_type,
            priority, ticket):
    """Analyze stale GitHub issues and generate a summary."""
    if not token:
        click.echo("Error: Devin API token required. Set DEVIN_API_TOKEN or use --token.")
        raise SystemExit(1)
    if not github_token:
        click.echo("Error: GitHub token required. Set GITHUB_TOKEN or use --github-token.")
        raise SystemExit(1)
    if not repo:
        click.echo("Error: Repository required. Set GITHUB_REPO or use --repo.")
        raise SystemExit(1)

    cfg = config_module.get_all_config()

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
        cfg, github_token, token, repo,
        stale_days=stale_days,
        top_n=top,
        filters=filters if filters else None,
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

    if status == "finished":
        click.echo("Devin has completed the fix and opened a PR!")
        pr_url = result.get("pr_url", "Check the Devin dashboard for the PR link.")
        click.echo(f"PR: {pr_url}")
    else:
        click.echo(f"Devin session ended with status: {status}")
        click.echo("Check the Devin dashboard for details.")


@cli.group(name="config")
def config_group():
    """Manage persistent configuration."""
    pass


@config_group.command(name="set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a configuration value."""
    try:
        result = config_module.set_config(key, value)
        click.echo(f"{key} = {result}")
    except KeyError as e:
        click.echo(f"Error: {e}")
        raise SystemExit(1)


@config_group.command(name="get")
@click.argument("key")
def config_get(key):
    """Get a configuration value."""
    try:
        value = config_module.get_config(key)
        click.echo(f"{key} = {value}")
    except KeyError as e:
        click.echo(f"Error: {e}")
        raise SystemExit(1)


@config_group.command(name="list")
def config_list():
    """List all configuration values."""
    cfg = config_module.list_config()
    for key, value in cfg.items():
        click.echo(f"{key} = {value}")


if __name__ == "__main__":
    cli()
