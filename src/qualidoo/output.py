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

    # Check for baseline violations
    baseline_violation = result.get("baseline_violation", False)
    baseline_violations = result.get("baseline_violations", [])

    # Summary panel
    summary = Text()
    summary.append(f"Score: ", style="bold")
    summary.append(f"{overall_score:.1f}/100", style=grade_color)
    summary.append(f" ({grade_label})", style="dim")

    # Override border color if baseline violation
    border_style = "bold red" if baseline_violation else grade_color

    panel = Panel(
        summary,
        title=f"[bold]{addon_name}[/bold]",
        border_style=border_style,
        padding=(0, 2),
    )
    console.print(panel)

    # Show baseline violation warning
    if baseline_violation:
        console.print()
        console.print("[bold red]!! BASELINE VIOLATION !![/bold red]")
        for violation in baseline_violations:
            console.print(f"  [red]- {violation}[/red]")

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
        "[link=https://qualidoo.com]https://qualidoo.com/dashboard[/link]"
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


# =============================================================================
# Repository Scan Output
# =============================================================================


def print_integrations(integrations: list[dict[str, Any]]) -> None:
    """Print integration status."""
    if not integrations:
        console.print("[dim]No integrations connected.[/dim]")
        console.print()
        console.print(
            "Connect GitHub at: "
            "[link=https://qualidoo.com/settings]"
            "https://qualidoo.com/settings[/link] Integrations tab."
        )
        return

    for integration in integrations:
        provider = integration.get("provider", "unknown")
        username = integration.get("provider_username", "")
        is_active = integration.get("is_active", False)

        if provider == "github":
            if is_active:
                console.print(f"[green]GitHub:[/green] Connected (@{username})")
            else:
                console.print("[red]GitHub:[/red] Disconnected")
        else:
            status_color = "green" if is_active else "red"
            status_text = "Connected" if is_active else "Disconnected"
            console.print(f"[{status_color}]{provider.title()}:[/{status_color}] {status_text}")


def create_repo_progress_callback(repo: str) -> Any:
    """Create a progress callback for repo scan polling with live display.

    Args:
        repo: Repository name for display.

    Returns:
        Callback function with progress tracking.
    """
    from rich.live import Live
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    )

    live = Live(progress, console=console, refresh_per_second=4)

    task_id: TaskID | None = None
    started = False
    completed_addons: set[str] = set()

    def callback(status: dict[str, Any]) -> None:
        nonlocal task_id, started, completed_addons

        scan_status = status.get("status", "unknown")
        total = status.get("total_addons", 0)
        analyzed = status.get("analyzed_addons", 0)
        failed = status.get("failed_addons", 0)

        if not started:
            live.start()
            task_id = progress.add_task(f"Scanning {repo}...", total=total or 1)
            started = True

        # Update progress
        if task_id is not None:
            completed = analyzed + failed
            if total > 0:
                progress.update(task_id, completed=completed, total=total)

            # Update description based on status
            if scan_status == "discovering":
                progress.update(task_id, description="Discovering addons...")
            elif scan_status == "analyzing":
                # Find currently analyzing addon
                results = status.get("results", [])
                analyzing = [r for r in results if r.get("status") == "analyzing"]
                if analyzing:
                    current = analyzing[0].get("name", "")
                    progress.update(task_id, description=f"Analyzing {current}...")
                else:
                    progress.update(task_id, description="Analyzing addons...")
            elif scan_status == "completed":
                progress.update(task_id, description="Scan completed")

    callback.live = live  # type: ignore[attr-defined]
    callback.progress = progress  # type: ignore[attr-defined]
    callback.stop = lambda: live.stop() if started else None  # type: ignore[attr-defined]

    return callback


def print_repo_results(
    scan_result: dict[str, Any],
    repo: str,
    verbose: bool = False,
) -> None:
    """Print repository scan results.

    Args:
        scan_result: Scan status dict from API.
        repo: Repository name for display.
        verbose: If True, show detailed per-addon findings.
    """
    status = scan_result.get("status", "unknown")
    results = scan_result.get("results", [])
    total = scan_result.get("total_addons", 0)
    analyzed = scan_result.get("analyzed_addons", 0)
    failed = scan_result.get("failed_addons", 0)

    # Header
    console.print()
    console.print(f"[bold]Repository:[/bold] {repo}")
    console.print(f"[bold]Status:[/bold] {status}")
    console.print(f"[bold]Addons:[/bold] {analyzed} analyzed, {failed} failed, {total} total")
    console.print()

    if not results:
        console.print("[dim]No addons analyzed.[/dim]")
        return

    # Build results table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Addon", style="cyan", min_width=30)
    table.add_column("Score", justify="right", min_width=6)
    table.add_column("Grade", justify="center", min_width=6)
    table.add_column("Critical", justify="right", min_width=8)
    table.add_column("Major", justify="right", min_width=6)
    table.add_column("Status", min_width=10)

    # Sort by score (descending), then by name
    sorted_results = sorted(
        results,
        key=lambda r: (-(r.get("score") or 0), r.get("name", "")),
    )

    for result in sorted_results:
        name = result.get("name", "unknown")
        addon_status = result.get("status", "unknown")
        score = result.get("score")
        grade = result.get("grade", "")
        critical = result.get("critical_count", 0)
        major = result.get("major_count", 0)
        error = result.get("error_message")

        # Format score
        if score is not None:
            score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
            score_text = Text(str(score), style=score_color)
        else:
            score_text = Text("-", style="dim")

        # Format grade
        grade_color = GRADE_COLORS.get(grade, "white")
        grade_text = Text(grade, style=grade_color) if grade else Text("-", style="dim")

        # Format status
        if addon_status == "completed":
            status_text = Text("Done", style="green")
        elif addon_status == "failed":
            status_text = Text("Failed", style="red")
        elif addon_status == "analyzing":
            status_text = Text("Running", style="yellow")
        else:
            status_text = Text(addon_status, style="dim")

        # Format counts
        critical_text = Text(str(critical), style="red") if critical > 0 else Text("-", style="dim")
        major_text = Text(str(major), style="yellow") if major > 0 else Text("-", style="dim")

        table.add_row(name, score_text, grade_text, critical_text, major_text, status_text)

        # Show error if failed
        if error and addon_status == "failed":
            console.print(f"  [dim]{name}:[/dim] [red]{error}[/red]")

    console.print(table)
    console.print()

    # Summary stats
    completed_results = [r for r in results if r.get("status") == "completed" and r.get("score") is not None]
    if completed_results:
        scores = [r["score"] for r in completed_results]
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)

        console.print(f"[bold]Average score:[/bold] {avg_score:.1f}")
        console.print(f"[bold]Score range:[/bold] {min_score} - {max_score}")
        console.print()

    # Check for baseline violations
    violated_addons = [
        r.get("name", "unknown")
        for r in results
        if r.get("baseline_violation", False)
    ]
    if violated_addons:
        console.print("[bold red]!! BASELINE VIOLATIONS !![/bold red]")
        console.print("[red]The following addons violate project baseline rules:[/red]")
        for addon_name in violated_addons:
            console.print(f"  [red]- {addon_name}[/red]")
        console.print()

    # Verbose mode: show per-addon details
    if verbose:
        console.print("[dim]Use 'qualidoo history' to view detailed results for each addon.[/dim]")
        console.print()

    # Dashboard link
    console.print(
        "[dim]View full reports on your dashboard:[/dim] "
        "[link=https://qualidoo.com/dashboard]https://qualidoo.com/dashboard[/link]"
    )
