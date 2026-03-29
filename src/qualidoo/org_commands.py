"""Organization and project context commands for Qualidoo CLI."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

from qualidoo.api_client import (
    APIError,
    AuthenticationError,
    ForbiddenError,
    QualidooClient,
)
from qualidoo.config import clear_context, get_api_key, get_context, set_context
from qualidoo.output import (
    console,
    print_context,
    print_error,
    print_organizations,
    print_success,
)

org_app = typer.Typer(
    name="org",
    help="Manage organization and project context",
    no_args_is_help=True,
)


@org_app.command("list")
def list_orgs() -> None:
    """List all organizations and their projects.

    Shows all organizations you're a member of, along with their projects.
    The current context is marked with an arrow.
    """
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'qualidoo login' first.")
        raise typer.Exit(1)

    console.print("Fetching organizations...", end=" ")
    try:
        with QualidooClient(api_key=api_key) as client:
            result = client.get_organizations()
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

    if result is None:
        print_error("No response from server. Make sure the server is running the latest version.")
        raise typer.Exit(1)

    context = get_context()
    print_organizations(result.get("organizations", []), context)


@org_app.command("use")
def use_org(
    org: Annotated[
        str,
        typer.Argument(
            help="Organization name or ID to use",
        ),
    ],
    project: Annotated[
        Optional[str],
        typer.Option(
            "--project",
            "-p",
            help="Project name or ID within the organization",
        ),
    ] = None,
) -> None:
    """Set the default organization and project for scans.

    Scans will be attributed to this project until you change or clear the context.

    Examples:

        qualidoo org use AidooIT

        qualidoo org use AidooIT --project "Backend Project"
    """
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'qualidoo login' first.")
        raise typer.Exit(1)

    # Fetch organizations to validate the choice
    console.print("Validating context...", end=" ")
    try:
        with QualidooClient(api_key=api_key) as client:
            result = client.get_organizations()
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

    if result is None:
        print_error("No response from server. Make sure the server is running the latest version.")
        raise typer.Exit(1)

    organizations = result.get("organizations", [])

    # Find the organization
    selected_org = None
    for o in organizations:
        if o.get("name", "").lower() == org.lower() or o.get("id") == org:
            selected_org = o
            break

    if not selected_org:
        print_error(f"Organization '{org}' not found.")
        console.print("[dim]Available organizations:[/dim]")
        for o in organizations:
            console.print(f"  - {o.get('name')}")
        raise typer.Exit(1)

    # Find the project if specified
    selected_project = None
    if project:
        projects = selected_org.get("projects", [])
        for p in projects:
            if p.get("name", "").lower() == project.lower() or p.get("id") == project:
                selected_project = p
                break

        if not selected_project:
            print_error(f"Project '{project}' not found in {selected_org.get('name')}.")
            console.print("[dim]Available projects:[/dim]")
            for p in projects:
                console.print(f"  - {p.get('name')}")
            raise typer.Exit(1)

    # Save context
    set_context(
        organization_id=selected_org.get("id"),
        organization_name=selected_org.get("name"),
        project_id=selected_project.get("id") if selected_project else None,
        project_name=selected_project.get("name") if selected_project else None,
    )

    if selected_project:
        print_success(f"Default set to: {selected_org.get('name')} / {selected_project.get('name')}")
    else:
        print_success(f"Default set to: {selected_org.get('name')}")

    console.print("[dim]Scans will be attributed to this context.[/dim]")
    console.print("[dim]Run 'qualidoo org clear' to clear organization/project.[/dim]")


@org_app.command("current")
def show_current() -> None:
    """Show the current organization/project context."""
    context = get_context()
    print_context(context)


@org_app.command("clear")
def clear_org() -> None:
    """Clear the organization/project context.

    After clearing, scans will go to your personal history.
    """
    clear_context()
    print_success("Context cleared. Scans will now go to your personal history.")
