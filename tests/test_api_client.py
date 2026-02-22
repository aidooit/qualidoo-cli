"""Tests for the Qualidoo API client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from qualidoo.api_client import (
    APIError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    QualidooClient,
    RateLimitError,
)


class TestQualidooClientGitHubMethods:
    """Tests for GitHub-related API client methods."""

    @pytest.fixture
    def client(self) -> QualidooClient:
        """Create a test client."""
        return QualidooClient(api_key="qdoo_test_key", api_url="https://test.api.com")

    @pytest.fixture
    def mock_response(self) -> MagicMock:
        """Create a mock HTTP response."""
        response = MagicMock()
        response.status_code = 200
        return response

    def test_get_github_status_connected(
        self, client: QualidooClient, mock_response: MagicMock
    ) -> None:
        """Test getting GitHub status when connected."""
        mock_response.json.return_value = {
            "connected": True,
            "username": "testuser",
            "message": "Connected as @testuser",
        }

        with patch.object(client.client, "get", return_value=mock_response):
            result = client.get_github_status()

        assert result["connected"] is True
        assert result["username"] == "testuser"

    def test_get_github_status_not_connected(
        self, client: QualidooClient, mock_response: MagicMock
    ) -> None:
        """Test getting GitHub status when not connected."""
        mock_response.json.return_value = {
            "connected": False,
            "username": None,
            "message": "GitHub not connected",
        }

        with patch.object(client.client, "get", return_value=mock_response):
            result = client.get_github_status()

        assert result["connected"] is False
        assert result["username"] is None

    def test_discover_addons_success(
        self, client: QualidooClient, mock_response: MagicMock
    ) -> None:
        """Test discovering addons in a repo."""
        mock_response.json.return_value = {
            "repo": "oca/account-financial-tools",
            "branch": "16.0",
            "addons": [
                {"path": "account_invoice_validation", "name": "account_invoice_validation"},
                {"path": "account_payment_partner", "name": "account_payment_partner"},
            ],
            "total": 2,
        }

        with patch.object(client.client, "get", return_value=mock_response):
            result = client.discover_addons("oca", "account-financial-tools", branch="16.0")

        assert result["repo"] == "oca/account-financial-tools"
        assert result["total"] == 2
        assert len(result["addons"]) == 2

    def test_discover_addons_not_found(
        self, client: QualidooClient, mock_response: MagicMock
    ) -> None:
        """Test discovering addons when repo not found."""
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Repository not found"}
        mock_response.text = "Repository not found"

        with patch.object(client.client, "get", return_value=mock_response):
            with pytest.raises(NotFoundError):
                client.discover_addons("nonexistent", "repo")

    def test_start_repo_analysis_success(
        self, client: QualidooClient, mock_response: MagicMock
    ) -> None:
        """Test starting repo analysis."""
        mock_response.json.return_value = {
            "scan_id": "scan_123",
            "total_addons": 5,
        }

        with patch.object(client.client, "post", return_value=mock_response):
            result = client.start_repo_analysis(
                repo="oca/account-financial-tools",
                branch="16.0",
                addon_path=None,
                use_llm=False,
            )

        assert result["scan_id"] == "scan_123"
        assert result["total_addons"] == 5

    def test_start_repo_analysis_specific_addon(
        self, client: QualidooClient, mock_response: MagicMock
    ) -> None:
        """Test starting repo analysis for specific addon."""
        mock_response.json.return_value = {
            "scan_id": "scan_456",
            "total_addons": 1,
        }

        with patch.object(client.client, "post", return_value=mock_response) as mock_post:
            result = client.start_repo_analysis(
                repo="oca/account-financial-tools",
                branch="16.0",
                addon_path="account_invoice_validation",
                use_llm=False,
            )

        assert result["scan_id"] == "scan_456"
        assert result["total_addons"] == 1

        # Verify the payload included addon_path
        call_args = mock_post.call_args
        assert call_args.kwargs["json"]["addon_path"] == "account_invoice_validation"

    def test_get_scan_status_success(
        self, client: QualidooClient, mock_response: MagicMock
    ) -> None:
        """Test getting scan status."""
        mock_response.json.return_value = {
            "status": "analyzing",
            "total_addons": 5,
            "analyzed_addons": 2,
            "failed_addons": 0,
            "results": [
                {
                    "path": "addon1",
                    "name": "addon1",
                    "status": "completed",
                    "score": 85,
                    "grade": "A",
                },
                {
                    "path": "addon2",
                    "name": "addon2",
                    "status": "completed",
                    "score": 72,
                    "grade": "B",
                },
            ],
            "error_message": None,
        }

        with patch.object(client.client, "get", return_value=mock_response):
            result = client.get_scan_status("scan_123")

        assert result["status"] == "analyzing"
        assert result["analyzed_addons"] == 2
        assert len(result["results"]) == 2

    def test_get_scan_status_not_found(
        self, client: QualidooClient, mock_response: MagicMock
    ) -> None:
        """Test getting scan status when not found."""
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Scan not found"}
        mock_response.text = "Scan not found"

        with patch.object(client.client, "get", return_value=mock_response):
            with pytest.raises(NotFoundError):
                client.get_scan_status("nonexistent_scan")

    def test_get_integrations_success(
        self, client: QualidooClient, mock_response: MagicMock
    ) -> None:
        """Test getting integrations list."""
        mock_response.json.return_value = [
            {
                "id": "int_123",
                "provider": "github",
                "provider_username": "testuser",
                "is_active": True,
                "scopes": ["repo", "read:user"],
                "connected_at": "2024-01-01T00:00:00Z",
            }
        ]

        with patch.object(client.client, "get", return_value=mock_response):
            result = client.get_integrations()

        assert len(result) == 1
        assert result[0]["provider"] == "github"
        assert result[0]["is_active"] is True

    def test_authentication_error(
        self, client: QualidooClient, mock_response: MagicMock
    ) -> None:
        """Test handling of 401 authentication error."""
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid token"}

        with patch.object(client.client, "get", return_value=mock_response):
            with pytest.raises(AuthenticationError):
                client.get_github_status()

    def test_forbidden_error(
        self, client: QualidooClient, mock_response: MagicMock
    ) -> None:
        """Test handling of 403 forbidden error."""
        mock_response.status_code = 403
        mock_response.json.return_value = {"detail": "Requires Pro tier subscription"}

        with patch.object(client.client, "get", return_value=mock_response):
            with pytest.raises(ForbiddenError):
                client.get_github_status()

    def test_rate_limit_error(
        self, client: QualidooClient, mock_response: MagicMock
    ) -> None:
        """Test handling of 429 rate limit error."""
        mock_response.status_code = 429
        mock_response.json.return_value = {"detail": "Rate limit exceeded"}

        with patch.object(client.client, "get", return_value=mock_response):
            with pytest.raises(RateLimitError):
                client.get_github_status()


class TestWaitForScanCompletion:
    """Tests for wait_for_scan_completion method."""

    @pytest.fixture
    def client(self) -> QualidooClient:
        """Create a test client."""
        return QualidooClient(api_key="qdoo_test_key", api_url="https://test.api.com")

    def test_wait_for_completion_immediate_success(self, client: QualidooClient) -> None:
        """Test waiting when scan completes immediately."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "completed",
            "total_addons": 2,
            "analyzed_addons": 2,
            "failed_addons": 0,
            "results": [],
            "error_message": None,
        }

        with patch.object(client.client, "get", return_value=mock_response):
            result = client.wait_for_scan_completion("scan_123", timeout=10)

        assert result["status"] == "completed"

    def test_wait_for_completion_with_polling(self, client: QualidooClient) -> None:
        """Test waiting with multiple polling iterations."""
        responses = [
            {"status": "analyzing", "total_addons": 2, "analyzed_addons": 0, "failed_addons": 0, "results": [], "error_message": None},
            {"status": "analyzing", "total_addons": 2, "analyzed_addons": 1, "failed_addons": 0, "results": [], "error_message": None},
            {"status": "completed", "total_addons": 2, "analyzed_addons": 2, "failed_addons": 0, "results": [], "error_message": None},
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = responses

        with patch.object(client.client, "get", return_value=mock_response):
            with patch("time.sleep"):  # Skip actual sleeping
                result = client.wait_for_scan_completion(
                    "scan_123", poll_interval=0.1, timeout=10
                )

        assert result["status"] == "completed"

    def test_wait_for_completion_timeout(self, client: QualidooClient) -> None:
        """Test timeout when scan doesn't complete."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "analyzing",
            "total_addons": 5,
            "analyzed_addons": 1,
            "failed_addons": 0,
            "results": [],
            "error_message": None,
        }

        with patch.object(client.client, "get", return_value=mock_response):
            with patch("time.sleep"):
                with pytest.raises(TimeoutError, match="did not complete"):
                    client.wait_for_scan_completion(
                        "scan_123", poll_interval=0.001, timeout=0.001
                    )

    def test_wait_for_completion_with_failure(self, client: QualidooClient) -> None:
        """Test handling scan failure."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "failed",
            "total_addons": 2,
            "analyzed_addons": 0,
            "failed_addons": 2,
            "results": [],
            "error_message": "GitHub API error",
        }

        with patch.object(client.client, "get", return_value=mock_response):
            with pytest.raises(APIError, match="Scan failed"):
                client.wait_for_scan_completion("scan_123", timeout=10)

    def test_wait_for_completion_with_callback(self, client: QualidooClient) -> None:
        """Test progress callback is called during polling."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "completed",
            "total_addons": 2,
            "analyzed_addons": 2,
            "failed_addons": 0,
            "results": [],
            "error_message": None,
        }

        callback = MagicMock()

        with patch.object(client.client, "get", return_value=mock_response):
            client.wait_for_scan_completion(
                "scan_123", timeout=10, progress_callback=callback
            )

        callback.assert_called()
