"""Tests for the organization commands."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from qualidoo.api_client import APIError, AuthenticationError, ForbiddenError
from qualidoo.cli import app
from qualidoo.config import OrgProjectContext

runner = CliRunner()


@pytest.fixture
def mock_organizations_response() -> dict:
    """Return a mock organizations response from the API."""
    return {
        "organizations": [
            {
                "id": "org_abc123",
                "name": "AidooIT",
                "slug": "aidooit",
                "role": "owner",
                "projects": [
                    {"id": "project_def456", "name": "Backend Project"},
                    {"id": "project_ghi789", "name": "Frontend Project"},
                ],
            },
            {
                "id": "org_xyz789",
                "name": "ClientCorp",
                "slug": "clientcorp",
                "role": "member",
                "projects": [
                    {"id": "project_jkl012", "name": "Odoo Modules"},
                ],
            },
        ]
    }


class TestOrgList:
    """Tests for 'org list' command."""

    def test_org_list_success(
        self, valid_api_key: str, mock_organizations_response: dict
    ):
        """Test org list shows organizations and projects."""
        with (
            patch("qualidoo.org_commands.get_api_key", return_value=valid_api_key),
            patch("qualidoo.org_commands.QualidooClient") as mock_client_class,
            patch("qualidoo.org_commands.get_context", return_value=OrgProjectContext()),
            patch("qualidoo.org_commands.print_organizations") as mock_print,
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_organizations.return_value = mock_organizations_response
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["org", "list"])

            assert result.exit_code == 0
            mock_print.assert_called_once()

    def test_org_list_not_logged_in(self):
        """Test org list when not logged in."""
        with patch("qualidoo.org_commands.get_api_key", return_value=None):
            result = runner.invoke(app, ["org", "list"])

            assert result.exit_code == 1

    def test_org_list_auth_failure(self, valid_api_key: str):
        """Test org list with authentication failure."""
        with (
            patch("qualidoo.org_commands.get_api_key", return_value=valid_api_key),
            patch("qualidoo.org_commands.QualidooClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_organizations.side_effect = AuthenticationError("Invalid key")
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["org", "list"])

            assert result.exit_code == 1


class TestOrgUse:
    """Tests for 'org use' command."""

    def test_org_use_set_org_only(
        self, valid_api_key: str, mock_organizations_response: dict
    ):
        """Test setting org context without project."""
        with (
            patch("qualidoo.org_commands.get_api_key", return_value=valid_api_key),
            patch("qualidoo.org_commands.QualidooClient") as mock_client_class,
            patch("qualidoo.org_commands.set_context") as mock_set_context,
            patch("qualidoo.org_commands.print_success"),
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_organizations.return_value = mock_organizations_response
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["org", "use", "AidooIT"])

            assert result.exit_code == 0
            mock_set_context.assert_called_once_with(
                organization_id="org_abc123",
                organization_name="AidooIT",
                project_id=None,
                project_name=None,
            )

    def test_org_use_set_org_and_project(
        self, valid_api_key: str, mock_organizations_response: dict
    ):
        """Test setting org and project context."""
        with (
            patch("qualidoo.org_commands.get_api_key", return_value=valid_api_key),
            patch("qualidoo.org_commands.QualidooClient") as mock_client_class,
            patch("qualidoo.org_commands.set_context") as mock_set_context,
            patch("qualidoo.org_commands.print_success"),
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_organizations.return_value = mock_organizations_response
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app, ["org", "use", "AidooIT", "--project", "Backend Project"]
            )

            assert result.exit_code == 0
            mock_set_context.assert_called_once_with(
                organization_id="org_abc123",
                organization_name="AidooIT",
                project_id="project_def456",
                project_name="Backend Project",
            )

    def test_org_use_org_not_found(
        self, valid_api_key: str, mock_organizations_response: dict
    ):
        """Test error when org not found."""
        with (
            patch("qualidoo.org_commands.get_api_key", return_value=valid_api_key),
            patch("qualidoo.org_commands.QualidooClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_organizations.return_value = mock_organizations_response
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["org", "use", "NonExistent"])

            assert result.exit_code == 1
            assert "not found" in result.output.lower()

    def test_org_use_project_not_found(
        self, valid_api_key: str, mock_organizations_response: dict
    ):
        """Test error when project not found in org."""
        with (
            patch("qualidoo.org_commands.get_api_key", return_value=valid_api_key),
            patch("qualidoo.org_commands.QualidooClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_organizations.return_value = mock_organizations_response
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app, ["org", "use", "AidooIT", "--project", "NonExistent Project"]
            )

            assert result.exit_code == 1
            assert "not found" in result.output.lower()


class TestOrgCurrent:
    """Tests for 'org current' command."""

    def test_org_current_with_context(self):
        """Test showing current context."""
        context = OrgProjectContext(
            organization_id="org_abc123",
            organization_name="AidooIT",
            project_id="project_def456",
            project_name="Backend Project",
        )
        with (
            patch("qualidoo.org_commands.get_context", return_value=context),
            patch("qualidoo.org_commands.print_context") as mock_print,
        ):
            result = runner.invoke(app, ["org", "current"])

            assert result.exit_code == 0
            mock_print.assert_called_once_with(context)

    def test_org_current_no_context(self):
        """Test showing no context."""
        with (
            patch("qualidoo.org_commands.get_context", return_value=OrgProjectContext()),
            patch("qualidoo.org_commands.print_context") as mock_print,
        ):
            result = runner.invoke(app, ["org", "current"])

            assert result.exit_code == 0
            mock_print.assert_called_once()


class TestOrgClear:
    """Tests for 'org clear' command."""

    def test_org_clear(self):
        """Test clearing context."""
        with (
            patch("qualidoo.org_commands.clear_context") as mock_clear,
            patch("qualidoo.org_commands.print_success"),
        ):
            result = runner.invoke(app, ["org", "clear"])

            assert result.exit_code == 0
            mock_clear.assert_called_once()
