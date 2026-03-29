"""Helper functions for resolving organization/project names to IDs."""

from __future__ import annotations

from dataclasses import dataclass

from qualidoo.api_client import QualidooClient


@dataclass
class ResolvedContext:
    """Resolved organization and project IDs."""

    organization_id: str | None = None
    organization_name: str | None = None
    project_id: str | None = None
    project_name: str | None = None

    @property
    def has_project(self) -> bool:
        """Check if project is resolved."""
        return self.project_id is not None


class OrgProjectResolverError(Exception):
    """Error resolving organization or project."""

    pass


def resolve_org_project(
    client: QualidooClient,
    org_name: str | None,
    project_name: str | None,
) -> ResolvedContext:
    """Resolve organization and project names to IDs.

    Args:
        client: Authenticated QualidooClient.
        org_name: Organization name or ID to look up.
        project_name: Project name or ID within the organization.

    Returns:
        ResolvedContext with organization and project IDs.

    Raises:
        OrgProjectResolverError: If org or project not found.
    """
    if not org_name and not project_name:
        return ResolvedContext()

    # Fetch organizations from API
    result = client.get_organizations()

    if result is None:
        raise OrgProjectResolverError(
            "Could not fetch organizations. Server may need to be updated."
        )

    organizations = result.get("organizations", [])

    if not organizations:
        raise OrgProjectResolverError("You are not a member of any organization.")

    # If only project is specified without org, we need to find which org it belongs to
    if project_name and not org_name:
        # Search all orgs for this project
        for org in organizations:
            projects = org.get("projects", [])
            for p in projects:
                if p.get("name", "").lower() == project_name.lower() or p.get("id") == project_name:
                    return ResolvedContext(
                        organization_id=org.get("id"),
                        organization_name=org.get("name"),
                        project_id=p.get("id"),
                        project_name=p.get("name"),
                    )

        # Project not found in any org
        raise OrgProjectResolverError(
            f"Project '{project_name}' not found in any of your organizations."
        )

    # Find the organization
    selected_org = None
    for org in organizations:
        if org.get("name", "").lower() == org_name.lower() or org.get("id") == org_name:
            selected_org = org
            break

    if not selected_org:
        org_names = [o.get("name") for o in organizations]
        raise OrgProjectResolverError(
            f"Organization '{org_name}' not found. "
            f"Available: {', '.join(org_names)}"
        )

    # If no project specified, return just the org
    if not project_name:
        return ResolvedContext(
            organization_id=selected_org.get("id"),
            organization_name=selected_org.get("name"),
        )

    # Find the project within the organization
    projects = selected_org.get("projects", [])
    selected_project = None
    for p in projects:
        if p.get("name", "").lower() == project_name.lower() or p.get("id") == project_name:
            selected_project = p
            break

    if not selected_project:
        project_names = [p.get("name") for p in projects]
        if project_names:
            raise OrgProjectResolverError(
                f"Project '{project_name}' not found in {selected_org.get('name')}. "
                f"Available: {', '.join(project_names)}"
            )
        else:
            raise OrgProjectResolverError(
                f"No projects found in {selected_org.get('name')}."
            )

    return ResolvedContext(
        organization_id=selected_org.get("id"),
        organization_name=selected_org.get("name"),
        project_id=selected_project.get("id"),
        project_name=selected_project.get("name"),
    )
