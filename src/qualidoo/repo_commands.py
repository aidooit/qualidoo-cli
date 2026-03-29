"""Repository scanning commands for Qualidoo CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from qualidoo.api_client import (
    APIError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    QualidooClient,
    RateLimitError,
)
from qualidoo.config import get_api_key, get_context
from qualidoo.github import parse_repo
from qualidoo.org_resolver import OrgProjectResolverError, resolve_org_project
from qualidoo.output import (
    console,
    create_repo_progress_callback,
    print_error,
    print_repo_results,
)

repo_app = typer.Typer(
    name="repo",
    help="GitHub repository operations",
    no_args_is_help=True,
)


@repo_app.command("check")
def check_repo(
    repo: Annotated[
        str,
        typer.Argument(
            help="GitHub repository (owner/repo or URL)",
        ),
    ],
    branch: Annotated[
        Optional[str],
        typer.Option(
            "--branch",
            "-b",
            help="Branch to analyze (defaults to repository default)",
        ),
    ] = None,
    addon: Annotated[
        Optional[str],
        typer.Option(
            "--addon",
            "-a",
            help="Analyze only this specific addon",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show detailed output",
        ),
    ] = False,
    save: Annotated[
        Optional[Path],
        typer.Option(
            "--save",
            "-s",
            help="Save results to JSON file",
        ),
    ] = None,
    timeout: Annotated[
        int,
        typer.Option(
            "--timeout",
            "-t",
            help="Maximum time to wait for analysis (seconds)",
        ),
    ] = 600,
    org: Annotated[
        Optional[str],
        typer.Option(
            "--org",
            "-o",
            help="Organization name/ID to attribute scan to (overrides context)",
        ),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option(
            "--project",
            "-p",
            help="Project name/ID within the organization (overrides context)",
        ),
    ] = None,
) -> None:
    """Analyze Odoo addons in a GitHub repository.

    Use --org and --project to attribute the scans to a specific project.

    Examples:

        qualidoo repo check oca/account-financial-tools

        qualidoo repo check https://github.com/owner/repo --branch 16.0

        qualidoo repo check owner/repo --addon specific_addon --project "Backend Project"
    """
    # Check for API key
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'qualidoo login' first.")
        raise typer.Exit(1)

    # Parse repository
    try:
        parsed = parse_repo(repo)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)

    repo_full_name = parsed.full_name
    # Use URL branch if no explicit --branch option provided
    effective_branch = branch or parsed.branch

    # Resolve project_id from options or context
    project_id: str | None = None
    project_display_name: str | None = None
    context = get_context()

    try:
        with QualidooClient(api_key=api_key) as client:
            # Resolve org/project names to IDs if specified
            if org or project:
                console.print("Resolving organization/project...", end=" ")
                try:
                    resolved = resolve_org_project(client, org, project)
                    project_id = resolved.project_id
                    project_display_name = resolved.project_name
                    console.print("[green]OK[/green]")
                except OrgProjectResolverError as e:
                    console.print("[red]Failed[/red]")
                    print_error(str(e))
                    raise typer.Exit(1)
            elif context.has_project:
                # Use context project silently
                project_id = context.project_id
                project_display_name = context.project_name

            # Check GitHub connection
            console.print("Checking GitHub connection...", end=" ")
            try:
                github_status = client.get_github_status()
            except ForbiddenError as e:
                console.print("[red]Failed[/red]")
                print_error(e.message)
                raise typer.Exit(1)
            except AuthenticationError:
                console.print("[red]Failed[/red]")
                print_error("Authentication failed. Run 'qualidoo login' to reconfigure.")
                raise typer.Exit(1)

            if not github_status.get("connected"):
                console.print("[red]Not connected[/red]")
                print_error(
                    "GitHub not connected. "
                    "Connect at https://qualidoo.com/settings Integrations tab."
                )
                raise typer.Exit(1)

            console.print(f"[green]@{github_status.get('username')}[/green]")

            # Discover addons first to show what we're scanning
            console.print(f"Discovering addons in [cyan]{repo_full_name}[/cyan]...", end=" ")
            try:
                discover_result = client.discover_addons(
                    parsed.owner,
                    parsed.repo,
                    branch=effective_branch,
                )
            except NotFoundError:
                console.print("[red]Not found[/red]")
                print_error(f"Repository not found: {repo_full_name}")
                raise typer.Exit(1)

            addons = discover_result.get("addons", [])
            actual_branch = discover_result.get("branch", effective_branch or "main")

            if not addons:
                console.print("[yellow]None found[/yellow]")
                print_error("No Odoo addons found in repository")
                raise typer.Exit(1)

            console.print(f"[green]Found {len(addons)} addons[/green]")

            # Filter if specific addon requested
            if addon:
                matching = [a for a in addons if a.get("path") == addon or a.get("name") == addon]
                if not matching:
                    print_error(f"Addon '{addon}' not found in repository")
                    console.print("[dim]Available addons:[/dim]")
                    for a in addons:
                        console.print(f"  - {a.get('name')} ({a.get('path')})")
                    raise typer.Exit(1)

            # Start analysis - show spinner while server prepares
            context_msg = ""
            if project_id:
                context_msg = f" (project: {project_display_name or project_id[:12]})"

            console.print()
            with console.status(
                f"[yellow]Preparing analysis{context_msg}...[/yellow]",
                spinner="dots",
            ) as status:
                try:
                    analyze_result = client.start_repo_analysis(
                        repo=repo_full_name,
                        branch=actual_branch,
                        addon_path=addon,
                        use_llm=False,
                        project_id=project_id,
                    )
                except RateLimitError:
                    status.stop()
                    print_error("Rate limit exceeded. Try again later.")
                    raise typer.Exit(1)
                except NotFoundError as e:
                    status.stop()
                    print_error(str(e.message))
                    raise typer.Exit(1)

            scan_id = analyze_result.get("scan_id")
            total_addons = analyze_result.get("total_addons", 0)

            if not scan_id:
                print_error("Failed to start analysis.")
                raise typer.Exit(1)

            console.print(f"Analyzing {total_addons} addon(s)...")
            console.print()

            # Wait for completion with progress
            progress_cb = create_repo_progress_callback(repo_full_name)
            try:
                result = client.wait_for_scan_completion(
                    scan_id,
                    timeout=float(timeout),
                    progress_callback=progress_cb,
                )
            except TimeoutError:
                progress_cb.stop()
                print_error(
                    f"Analysis timed out after {timeout} seconds. "
                    "Try with --addon to analyze a single module."
                )
                raise typer.Exit(1)
            finally:
                progress_cb.stop()

            # Print results
            print_repo_results(result, repo_full_name, verbose=verbose)

            # Save JSON result if requested
            if save:
                save_path = save if save.is_absolute() else Path.cwd() / save
                try:
                    with save_path.open("w") as f:
                        json.dump(result, f, indent=2, default=str)
                    console.print(f"[green]Result saved to:[/green] {save_path}")
                except Exception as e:
                    print_error(f"Failed to save result: {e}")

    except APIError as e:
        print_error(f"API error: {e.message}")
        raise typer.Exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        raise typer.Exit(1)
