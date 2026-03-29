"""Qualidoo CLI - AI-powered Odoo addon quality analyzer."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from qualidoo.api_client import (
    APIError,
    AuthenticationError,
    ForbiddenError,
    QualidooClient,
    RateLimitError,
)
from qualidoo.config import (
    get_api_key,
    get_config_path,
    get_context,
    load_config,
    remove_api_key,
    set_api_key,
    validate_api_key_format,
)
from qualidoo.output import (
    console,
    create_progress_callback,
    print_analysis_result,
    print_config_info,
    print_error,
    print_integrations,
    print_success,
    print_user_info,
)
from qualidoo.org_resolver import OrgProjectResolverError, resolve_org_project
from qualidoo.repo_commands import repo_app
from qualidoo.org_commands import org_app

app = typer.Typer(
    name="qualidoo",
    help="AI-powered Odoo addon quality analyzer",
    no_args_is_help=True,
)

# Register subcommands
app.add_typer(repo_app, name="repo")
app.add_typer(org_app, name="org")


@app.callback()
def main() -> None:
    """AI-powered Odoo addon quality analyzer."""
    pass


@app.command()
def login(
    api_key: Annotated[
        Optional[str],
        typer.Option(
            "--key",
            "-k",
            help="API key (or enter interactively)",
        ),
    ] = None,
) -> None:
    """Configure API key for authentication.

    Get your API key from https://qualidoo.com/settings
    """
    # Prompt for key if not provided
    if not api_key:
        console.print("Get your API key from: [link=https://qualidoo.com/settings]https://qualidoo.com/settings[/link] API Keys tab.")
        console.print()
        api_key = typer.prompt("Enter your API key", hide_input=True)

    if not api_key:
        print_error("API key is required.")
        raise typer.Exit(1)

    # Validate format
    if not validate_api_key_format(api_key):
        print_error("Invalid API key format. Keys should start with 'qdoo_'")
        raise typer.Exit(1)

    # Validate with API
    console.print("Validating API key...", end=" ")
    try:
        with QualidooClient(api_key=api_key) as client:
            user_info = client.validate_key()
    except AuthenticationError:
        console.print("[red]Failed[/red]")
        print_error("Invalid API key. Please check and try again.")
        raise typer.Exit(1)
    except ForbiddenError as e:
        console.print("[red]Failed[/red]")
        print_error(e.message)
        raise typer.Exit(1)
    except APIError as e:
        console.print("[red]Failed[/red]")
        print_error(f"API error: {e.message}")
        raise typer.Exit(1)
    except Exception as e:
        console.print("[red]Failed[/red]")
        print_error(f"Connection error: {e}")
        raise typer.Exit(1)

    console.print("[green]Success![/green]")

    # Save the key
    set_api_key(api_key)
    print_success(f"API key saved to {get_config_path()}")
    console.print()
    print_user_info(user_info)


@app.command()
def logout() -> None:
    """Remove stored API key."""
    if remove_api_key():
        print_success("API key removed.")
    else:
        console.print("No API key was configured.")


@app.command()
def whoami() -> None:
    """Show current authentication status."""
    api_key = get_api_key()

    if not api_key:
        print_error("Not logged in. Run 'qualidoo login' first.")
        raise typer.Exit(1)

    console.print("Checking authentication...", end=" ")
    try:
        with QualidooClient(api_key=api_key) as client:
            user_info = client.validate_key()
    except AuthenticationError:
        console.print("[red]Failed[/red]")
        print_error("Authentication failed. Run 'qualidoo login' to reconfigure.")
        raise typer.Exit(1)
    except APIError as e:
        console.print("[red]Failed[/red]")
        print_error(f"API error: {e.message}")
        raise typer.Exit(1)
    except Exception as e:
        console.print("[red]Failed[/red]")
        print_error(f"Connection error: {e}")
        raise typer.Exit(1)

    console.print("[green]OK[/green]")
    console.print()
    print_user_info(user_info)


@app.command()
def check(
    path: Annotated[
        Optional[Path],
        typer.Argument(
            help="Path to the Odoo addon directory (defaults to current directory)",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
    timeout: Annotated[
        int,
        typer.Option(
            "--timeout",
            "-t",
            help="Maximum time to wait for analysis (seconds)",
        ),
    ] = 300,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show detailed findings with file paths and suggestions",
        ),
    ] = False,
    save: Annotated[
        Optional[Path],
        typer.Option(
            "--save",
            "-s",
            help="Save full JSON result to file (e.g., result.json or /path/to/result.json)",
        ),
    ] = None,
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
    """Analyze an Odoo addon for quality issues.

    Uploads the addon to https://qualidoo.com for analysis and displays results.
    Use --org and --project to attribute the scan to a specific project.
    """
    # Check for API key
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'qualidoo login' first.")
        raise typer.Exit(1)

    # Use current directory if no path provided
    if path is None:
        path = Path.cwd()

    addon_name = path.name

    # Verify it looks like an addon
    manifest_path = path / "__manifest__.py"
    if not manifest_path.exists():
        print_error(f"Not a valid Odoo addon: missing __manifest__.py in {path}")
        raise typer.Exit(1)

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
                # Use context project
                project_id = context.project_id
                project_display_name = context.project_name

            # Upload addon
            context_msg = ""
            if project_id:
                context_msg = f" (project: {project_display_name or project_id[:12]})"
            console.print(f"Uploading [cyan]{addon_name}[/cyan]{context_msg}...", end=" ")
            try:
                upload_result = client.upload_addon(path, project_id=project_id)
            except AuthenticationError:
                console.print("[red]Failed[/red]")
                print_error("Authentication failed. Run 'qualidoo login' to reconfigure.")
                raise typer.Exit(1)
            except ForbiddenError as e:
                console.print("[red]Failed[/red]")
                print_error(e.message)
                raise typer.Exit(1)
            except RateLimitError:
                console.print("[red]Failed[/red]")
                print_error("Rate limit exceeded. Try again later.")
                raise typer.Exit(1)

            console.print("[green]Done[/green]")

            job_id = upload_result.get("job_id")
            if not job_id:
                print_error("No job ID returned from upload.")
                raise typer.Exit(1)

            # Wait for completion with progress
            progress_cb = create_progress_callback()
            try:
                result = client.wait_for_completion(
                    job_id,
                    timeout=float(timeout),
                    progress_callback=progress_cb,
                )
            finally:
                progress_cb.stop()

            console.print()
            print_analysis_result(result, addon_name, verbose=verbose)

            # Save JSON result if requested
            if save:
                import json

                # If only filename provided, save in current directory
                save_path = save if save.is_absolute() else Path.cwd() / save
                try:
                    with save_path.open("w") as f:
                        json.dump(result, f, indent=2, default=str)
                    console.print(f"[green]Result saved to:[/green] {save_path}")
                except Exception as e:
                    print_error(f"Failed to save result: {e}")

    except TimeoutError:
        print_error(f"Analysis timed out after {timeout} seconds.")
        raise typer.Exit(1)
    except APIError as e:
        print_error(f"API error: {e.message}")
        raise typer.Exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        raise typer.Exit(1)


@app.command()
def config(
    show: Annotated[
        bool,
        typer.Option(
            "--show",
            "-s",
            help="Show current configuration",
        ),
    ] = False,
) -> None:
    """View or manage configuration."""
    if show:
        cfg = load_config()
        print_config_info(cfg, str(get_config_path()))
    else:
        # Default behavior: show config
        cfg = load_config()
        print_config_info(cfg, str(get_config_path()))


@app.command()
def integrations() -> None:
    """Show connected integrations (GitHub, etc.)."""
    api_key = get_api_key()

    if not api_key:
        print_error("Not logged in. Run 'qualidoo login' first.")
        raise typer.Exit(1)

    console.print("Checking integrations...", end=" ")
    try:
        with QualidooClient(api_key=api_key) as client:
            integrations_list = client.get_integrations()
    except AuthenticationError:
        console.print("[red]Failed[/red]")
        print_error("Authentication failed. Run 'qualidoo login' to reconfigure.")
        raise typer.Exit(1)
    except ForbiddenError as e:
        console.print("[red]Failed[/red]")
        print_error(e.message)
        raise typer.Exit(1)
    except APIError as e:
        console.print("[red]Failed[/red]")
        print_error(f"API error: {e.message}")
        raise typer.Exit(1)
    except Exception as e:
        console.print("[red]Failed[/red]")
        print_error(f"Connection error: {e}")
        raise typer.Exit(1)

    console.print("[green]OK[/green]")
    console.print()
    print_integrations(integrations_list)


if __name__ == "__main__":
    app()
