"""Formatted terminal output for Qualidoo CLI using rich."""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# Grade colors
GRADE_COLORS = {
    "A+": "bold green",
    "A": "green",
    "B": "cyan",
    "C": "yellow",
    "D": "red",
    "F": "bold red",
}

# Severity colors and icons
SEVERITY_STYLES = {
    "CRITICAL": ("bold red", "!!"),
    "MAJOR": ("red", "!"),
    "MINOR": ("yellow", "-"),
    "INFO": ("dim", "i"),
}


def get_grade_from_score(score: float) -> str:
    """Convert score to letter grade."""
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"


def get_grade_label(score: float) -> str:
    """Get grade label from score."""
    if score >= 90:
        return "Excellent"
    elif score >= 80:
        return "Very Good"
    elif score >= 70:
        return "Good"
    elif score >= 60:
        return "Needs Work"
    else:
        return "Poor"


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]{message}[/bold green]")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]{message}[/yellow]")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[dim]{message}[/dim]")


def print_analysis_result(result: dict[str, Any], addon_name: str, verbose: bool = False) -> None:
    """Print formatted analysis result.

    Args:
        result: Analysis result dict from API.
        addon_name: Name of the analyzed addon.
        verbose: If True, show detailed findings with file paths and suggestions.
    """
    overall_score = result.get("overall_score", 0)
    grade = get_grade_from_score(overall_score)
    grade_label = get_grade_label(overall_score)
    grade_color = GRADE_COLORS.get(grade, "white")

    # Summary panel
    summary = Text()
    summary.append(f"Score: ", style="bold")
    summary.append(f"{overall_score:.1f}/100", style=grade_color)
    summary.append(f" ({grade_label})", style="dim")

    panel = Panel(
        summary,
        title=f"[bold]{addon_name}[/bold]",
        border_style=grade_color,
        padding=(0, 2),
    )
    console.print(panel)
    console.print()

    # Agent scores table
    agent_results_raw = result.get("agent_results", [])

    # Convert list to dict if needed (API returns list of agent results)
    if isinstance(agent_results_raw, list):
        agent_results = {ar.get("agent_name"): ar for ar in agent_results_raw}
    else:
        agent_results = agent_results_raw

    if agent_results:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Agent", style="cyan", min_width=18)
        table.add_column("Score", justify="right", min_width=6)
        table.add_column("Issues", justify="right", min_width=6)

        # Sort agents by weight/importance
        agent_order = [
            "python_quality",
            "security",
            "orm_patterns",
            "performance",
            "structure",
            "documentation",
            "test_coverage",
            "manifest",
            "views_frontend",
        ]

        for agent_name in agent_order:
            if agent_name in agent_results:
                agent_data = agent_results[agent_name]
                score = agent_data.get("score", 0)
                findings = agent_data.get("findings", [])
                issue_count = len(findings)

                # Use display_name from API if available, otherwise format agent_name
                display_name = agent_data.get("display_name") or agent_name.replace("_", " ").title()

                # Color score based on value
                if score >= 80:
                    score_style = "green"
                elif score >= 60:
                    score_style = "yellow"
                else:
                    score_style = "red"

                table.add_row(
                    display_name,
                    Text(str(int(score)), style=score_style),
                    str(issue_count) if issue_count > 0 else "-",
                )

        console.print(table)
        console.print()

    # Top issues
    top_issues = result.get("top_issues", [])
    if top_issues:
        console.print("[bold]Top Issues:[/bold]")
        for issue in top_issues[:10]:  # Limit to 10
            severity = issue.get("severity", "INFO").upper()
            message = issue.get("message", issue.get("description", ""))
            style, icon = SEVERITY_STYLES.get(severity, ("dim", "-"))

            text = Text()
            text.append(f"  {icon} ", style=style)
            text.append(f"{severity}: ", style=f"bold {style.split()[0] if ' ' in style else style}")
            text.append(message)
            console.print(text)

            # Verbose mode: show file path, line number, and suggestion
            if verbose:
                file_path = issue.get("file_path")
                line_number = issue.get("line_number")
                suggestion = issue.get("suggestion")

                if file_path:
                    location = f"    {file_path}"
                    if line_number:
                        location += f":{line_number}"
                    console.print(f"[dim]{location}[/dim]")

                if suggestion:
                    console.print(f"    [italic cyan]Suggestion:[/italic cyan] {suggestion}")

        console.print()

    # Verbose mode: show per-agent recommendations
    if verbose and agent_results:
        has_recommendations = any(
            agent_results.get(name, {}).get("recommendations")
            for name in agent_results
        )
        if has_recommendations:
            console.print("[bold]Recommendations by Agent:[/bold]")
            for agent_name, agent_data in agent_results.items():
                recommendations = agent_data.get("recommendations", [])
                if recommendations:
                    display_name = agent_data.get("display_name") or agent_name.replace("_", " ").title()
                    console.print(f"  [cyan]{display_name}:[/cyan]")
                    for rec in recommendations[:3]:  # Limit to 3 per agent
                        console.print(f"    [dim]-[/dim] {rec}")
            console.print()

    # Dashboard link
    console.print(
        "[dim]View the full report on your dashboard:[/dim] "
        "[link=https://qualidoo.aidooit.com]https://qualidoo.aidooit.com[/link]"
    )
    console.print()


def print_user_info(user_info: dict[str, Any]) -> None:
    """Print user authentication info in a styled panel."""
    email = user_info.get("email", "Unknown")
    tier = user_info.get("tier", "Unknown")
    analyses_this_month = user_info.get("analyses_this_month", 0)
    analyses_limit = user_info.get("analyses_limit")
    api_requests_today = user_info.get("api_requests_today", 0)
    api_limit = user_info.get("api_limit")

    tier_colors = {
        "free": "dim",
        "beta": "cyan",
        "pro": "green",
        "team": "bold green",
    }
    tier_style = tier_colors.get(tier.lower(), "white")

    # Format analyses limit
    analyses_limit_str = "unlimited" if analyses_limit is None else str(analyses_limit)

    # Format API limit
    api_limit_str = "unlimited" if api_limit is None else str(api_limit)

    content = Text()
    content.append("Email: ", style="bold")
    content.append(f"{email}\n")
    content.append("Tier: ", style="bold")
    content.append(f"{tier.upper()}\n", style=tier_style)
    content.append("Analyses this month: ", style="bold")
    content.append(f"{analyses_this_month} / {analyses_limit_str}\n")
    content.append("API calls today: ", style="bold")
    content.append(f"{api_requests_today} / {api_limit_str}")

    panel = Panel(
        content,
        border_style="yellow",
        padding=(0, 2),
    )
    console.print(panel)


def print_config_info(config: dict[str, Any], config_path: str) -> None:
    """Print current configuration."""
    console.print(f"[bold]Config file:[/bold] {config_path}")

    if "api_key" in config:
        # Mask the API key
        key = config["api_key"]
        if len(key) > 12:
            masked = key[:8] + "..." + key[-4:]
        else:
            masked = "***"
        console.print(f"[bold]API key:[/bold] {masked}")
    else:
        console.print("[bold]API key:[/bold] [dim]Not configured[/dim]")


def create_progress_callback() -> Any:
    """Create a progress callback for job polling."""
    from rich.progress import Progress, SpinnerColumn, TextColumn

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )

    task_id = None
    started = False

    def callback(status: dict[str, Any]) -> None:
        nonlocal task_id, started
        job_status = status.get("status", "unknown")

        if not started:
            progress.start()
            task_id = progress.add_task(f"Analyzing... ({job_status})", total=None)
            started = True
        else:
            progress.update(task_id, description=f"Analyzing... ({job_status})")

    callback.progress = progress  # type: ignore[attr-defined]
    callback.stop = lambda: progress.stop() if started else None  # type: ignore[attr-defined]

    return callback
