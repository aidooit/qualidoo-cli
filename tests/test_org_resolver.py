"""Tests for org_resolver module."""

from unittest.mock import MagicMock

import pytest

from qualidoo.org_resolver import (
    OrgProjectResolverError,
    ResolvedContext,
    resolve_org_project,
)


class TestResolvedContext:
    """Tests for ResolvedContext dataclass."""

    def test_has_project_true_when_project_id_set(self):
        ctx = ResolvedContext(project_id="project_123", project_name="My Project")
        assert ctx.has_project is True

    def test_has_project_false_when_project_id_none(self):
        ctx = ResolvedContext(organization_id="org_123")
        assert ctx.has_project is False

    def test_empty_context(self):
        ctx = ResolvedContext()
        assert ctx.has_project is False
        assert ctx.organization_id is None


class TestResolveOrgProject:
    """Tests for resolve_org_project function."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock QualidooClient."""
        client = MagicMock()
        client.get_organizations.return_value = {
            "organizations": [
                {
                    "id": "org_abc123",
                    "name": "AidooIT",
                    "projects": [
                        {"id": "project_def456", "name": "Backend Project"},
                        {"id": "project_ghi789", "name": "Frontend Project"},
                    ],
                },
                {
                    "id": "org_xyz789",
                    "name": "ClientCorp",
                    "projects": [
                        {"id": "project_jkl012", "name": "DevOps"},
                    ],
                },
            ]
        }
        return client

    def test_no_org_no_project_returns_empty(self, mock_client):
        """When no org or project specified, return empty context."""
        result = resolve_org_project(mock_client, None, None)
        assert result.organization_id is None
        assert result.project_id is None
        # Should not call API
        mock_client.get_organizations.assert_not_called()

    def test_resolve_org_by_name(self, mock_client):
        """Resolve organization by name."""
        result = resolve_org_project(mock_client, "AidooIT", None)
        assert result.organization_id == "org_abc123"
        assert result.organization_name == "AidooIT"
        assert result.project_id is None

    def test_resolve_org_by_name_case_insensitive(self, mock_client):
        """Resolve organization by name (case insensitive)."""
        result = resolve_org_project(mock_client, "aidooit", None)
        assert result.organization_id == "org_abc123"
        assert result.organization_name == "AidooIT"

    def test_resolve_org_by_id(self, mock_client):
        """Resolve organization by ID."""
        result = resolve_org_project(mock_client, "org_abc123", None)
        assert result.organization_id == "org_abc123"
        assert result.organization_name == "AidooIT"

    def test_resolve_org_and_project(self, mock_client):
        """Resolve both organization and project."""
        result = resolve_org_project(mock_client, "AidooIT", "Backend Project")
        assert result.organization_id == "org_abc123"
        assert result.organization_name == "AidooIT"
        assert result.project_id == "project_def456"
        assert result.project_name == "Backend Project"

    def test_resolve_project_case_insensitive(self, mock_client):
        """Resolve project by name (case insensitive)."""
        result = resolve_org_project(mock_client, "AidooIT", "backend project")
        assert result.project_id == "project_def456"
        assert result.project_name == "Backend Project"

    def test_resolve_project_by_id(self, mock_client):
        """Resolve project by ID."""
        result = resolve_org_project(mock_client, "AidooIT", "project_def456")
        assert result.project_id == "project_def456"
        assert result.project_name == "Backend Project"

    def test_resolve_project_only_finds_org(self, mock_client):
        """When only project specified, find which org it belongs to."""
        result = resolve_org_project(mock_client, None, "DevOps")
        assert result.organization_id == "org_xyz789"
        assert result.organization_name == "ClientCorp"
        assert result.project_id == "project_jkl012"
        assert result.project_name == "DevOps"

    def test_org_not_found_raises_error(self, mock_client):
        """Raise error when organization not found."""
        with pytest.raises(OrgProjectResolverError) as exc_info:
            resolve_org_project(mock_client, "NonExistent", None)
        assert "NonExistent" in str(exc_info.value)
        assert "Available:" in str(exc_info.value)

    def test_project_not_found_raises_error(self, mock_client):
        """Raise error when project not found in organization."""
        with pytest.raises(OrgProjectResolverError) as exc_info:
            resolve_org_project(mock_client, "AidooIT", "NonExistent")
        assert "NonExistent" in str(exc_info.value)
        assert "AidooIT" in str(exc_info.value)

    def test_project_not_found_any_org_raises_error(self, mock_client):
        """Raise error when project not found in any organization."""
        with pytest.raises(OrgProjectResolverError) as exc_info:
            resolve_org_project(mock_client, None, "NonExistentProject")
        assert "NonExistentProject" in str(exc_info.value)

    def test_no_organizations_raises_error(self, mock_client):
        """Raise error when user has no organizations."""
        mock_client.get_organizations.return_value = {"organizations": []}
        with pytest.raises(OrgProjectResolverError) as exc_info:
            resolve_org_project(mock_client, "AidooIT", None)
        assert "not a member" in str(exc_info.value)

    def test_null_response_raises_error(self, mock_client):
        """Raise error when API returns null."""
        mock_client.get_organizations.return_value = None
        with pytest.raises(OrgProjectResolverError) as exc_info:
            resolve_org_project(mock_client, "AidooIT", None)
        assert "Could not fetch" in str(exc_info.value)

    def test_org_with_no_projects_raises_error(self, mock_client):
        """Raise error when org has no projects but project was requested."""
        mock_client.get_organizations.return_value = {
            "organizations": [
                {
                    "id": "org_empty",
                    "name": "EmptyOrg",
                    "projects": [],
                },
            ]
        }
        with pytest.raises(OrgProjectResolverError) as exc_info:
            resolve_org_project(mock_client, "EmptyOrg", "SomeProject")
        assert "No projects found" in str(exc_info.value)
