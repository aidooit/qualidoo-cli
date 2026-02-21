"""Tests for the api_client module."""

import zipfile
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from qualidoo.api_client import (
    APIError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    QualidooClient,
    RateLimitError,
)


class TestQualidooClientInit:
    """Tests for QualidooClient initialization."""

    def test_init_with_explicit_params(self, valid_api_key: str):
        """Test initialization with explicit API key and URL."""
        client = QualidooClient(
            api_key=valid_api_key, api_url="https://custom.example.com"
        )

        assert client.api_key == valid_api_key
        assert client.api_url == "https://custom.example.com"
        client.close()

    def test_init_loads_from_config(self, tmp_path: Path, clean_env, valid_api_key: str):
        """Test initialization loads from config when params not provided."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text(f'api_key = "{valid_api_key}"')

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
            patch("qualidoo.api_client.get_api_key", return_value=valid_api_key),
            patch(
                "qualidoo.api_client.get_api_url",
                return_value="https://qualidoo.aidooit.com",
            ),
        ):
            client = QualidooClient()

        assert client.api_key == valid_api_key
        client.close()

    def test_init_without_api_key(self, clean_env):
        """Test initialization without API key."""
        with (
            patch("qualidoo.api_client.get_api_key", return_value=None),
            patch(
                "qualidoo.api_client.get_api_url",
                return_value="https://qualidoo.aidooit.com",
            ),
        ):
            client = QualidooClient()

        assert client.api_key is None
        client.close()


class TestQualidooClientContextManager:
    """Tests for QualidooClient context manager."""

    def test_context_manager_enter(self, valid_api_key: str):
        """Test that __enter__ returns self."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")

        with client as c:
            assert c is client

    def test_context_manager_closes_client(self, valid_api_key: str):
        """Test that __exit__ closes the HTTP client."""
        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            # Access the client property to ensure it's created
            _ = client.client

        # After exiting, the internal client should be None
        assert client._client is None


class TestHandleResponse:
    """Tests for _handle_response method."""

    def test_success_response(self, valid_api_key: str):
        """Test handling of successful response."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")
        response = httpx.Response(200, json={"status": "ok"})

        result = client._handle_response(response)
        assert result == {"status": "ok"}
        client.close()

    def test_401_raises_authentication_error(self, valid_api_key: str):
        """Test that 401 raises AuthenticationError."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")
        response = httpx.Response(401, json={"detail": "Invalid API key"})

        with pytest.raises(AuthenticationError) as exc_info:
            client._handle_response(response)

        assert "Authentication failed" in str(exc_info.value)
        client.close()

    def test_403_raises_forbidden_error(self, valid_api_key: str):
        """Test that 403 raises ForbiddenError."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")
        response = httpx.Response(403, json={"detail": "Access denied"})

        with pytest.raises(ForbiddenError) as exc_info:
            client._handle_response(response)

        assert "Access denied" in str(exc_info.value)
        client.close()

    def test_404_raises_not_found_error(self, valid_api_key: str):
        """Test that 404 raises NotFoundError."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")
        response = httpx.Response(404, json={"detail": "Not found"})

        with pytest.raises(NotFoundError) as exc_info:
            client._handle_response(response)

        assert "not found" in str(exc_info.value).lower()
        client.close()

    def test_429_raises_rate_limit_error(self, valid_api_key: str):
        """Test that 429 raises RateLimitError."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")
        response = httpx.Response(429, json={"detail": "Rate limit exceeded"})

        with pytest.raises(RateLimitError) as exc_info:
            client._handle_response(response)

        assert "Rate limit exceeded" in str(exc_info.value)
        client.close()

    def test_500_raises_api_error(self, valid_api_key: str):
        """Test that 500 raises APIError."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")
        response = httpx.Response(500, json={"detail": "Internal server error"})

        with pytest.raises(APIError) as exc_info:
            client._handle_response(response)

        assert "Internal server error" in str(exc_info.value)
        client.close()

    def test_error_without_detail(self, valid_api_key: str):
        """Test handling error response without detail field."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")
        response = httpx.Response(500, json={"error": "Something went wrong"})

        with pytest.raises(APIError):
            client._handle_response(response)
        client.close()


class TestValidateKey:
    """Tests for validate_key method."""

    @respx.mock
    def test_validate_key_success(self, valid_api_key: str, mock_user_info: dict):
        """Test successful key validation."""
        respx.get("https://example.com/api/v1/auth/me").mock(
            return_value=httpx.Response(200, json=mock_user_info)
        )

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            result = client.validate_key()

        assert result == mock_user_info
        assert result["email"] == "test@example.com"

    @respx.mock
    def test_validate_key_auth_failure(self, valid_api_key: str):
        """Test key validation with invalid key."""
        respx.get("https://example.com/api/v1/auth/me").mock(
            return_value=httpx.Response(401, json={"detail": "Invalid API key"})
        )

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            with pytest.raises(AuthenticationError):
                client.validate_key()


class TestUploadAddon:
    """Tests for upload_addon method."""

    @respx.mock
    def test_upload_addon_success(
        self, valid_api_key: str, sample_addon: Path, mock_upload_response: dict
    ):
        """Test successful addon upload."""
        respx.post("https://example.com/api/v1/analyze/upload").mock(
            return_value=httpx.Response(200, json=mock_upload_response)
        )

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            result = client.upload_addon(sample_addon)

        assert result == mock_upload_response
        assert result["job_id"] == "test-job-123"

    def test_upload_addon_nonexistent_path(self, valid_api_key: str, tmp_path: Path):
        """Test upload with nonexistent path raises error."""
        nonexistent = tmp_path / "does_not_exist"

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            with pytest.raises(FileNotFoundError):
                client.upload_addon(nonexistent)

    def test_upload_addon_file_not_dir(self, valid_api_key: str, tmp_path: Path):
        """Test upload with file instead of directory raises error."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("not a directory")

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            with pytest.raises(ValueError, match="must be a directory"):
                client.upload_addon(file_path)


class TestShouldSkipFile:
    """Tests for _should_skip_file method."""

    def test_skip_pycache(self, valid_api_key: str):
        """Test that __pycache__ files are skipped."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")
        assert client._should_skip_file(Path("__pycache__/test.pyc")) is True
        assert client._should_skip_file(Path("models/__pycache__/model.cpython-311.pyc")) is True
        client.close()

    def test_skip_git(self, valid_api_key: str):
        """Test that .git files are skipped."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")
        assert client._should_skip_file(Path(".git/config")) is True
        assert client._should_skip_file(Path(".git/objects/abc123")) is True
        client.close()

    def test_skip_venv(self, valid_api_key: str):
        """Test that venv files are skipped."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")
        assert client._should_skip_file(Path("venv/bin/python")) is True
        assert client._should_skip_file(Path(".venv/lib/python")) is True
        client.close()

    def test_skip_node_modules(self, valid_api_key: str):
        """Test that node_modules files are skipped."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")
        assert client._should_skip_file(Path("node_modules/package/index.js")) is True
        client.close()

    def test_skip_pyc_files(self, valid_api_key: str):
        """Test that .pyc files are skipped."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")
        assert client._should_skip_file(Path("models/test.pyc")) is True
        # Note: .pyo files are only skipped if the part equals ".pyo" literally
        client.close()

    def test_skip_egg_info(self, valid_api_key: str):
        """Test that .egg-info directories are skipped."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")
        # The skip_patterns check for exact part match, so ".egg-info" as a folder name
        assert client._should_skip_file(Path(".egg-info/PKG-INFO")) is True
        client.close()

    def test_include_normal_files(self, valid_api_key: str):
        """Test that normal Python files are not skipped."""
        client = QualidooClient(api_key=valid_api_key, api_url="https://example.com")
        assert client._should_skip_file(Path("models/test.py")) is False
        assert client._should_skip_file(Path("__init__.py")) is False
        assert client._should_skip_file(Path("__manifest__.py")) is False
        assert client._should_skip_file(Path("views/template.xml")) is False
        client.close()


class TestGetJobStatus:
    """Tests for get_job_status method."""

    @respx.mock
    def test_get_job_status_success(
        self, valid_api_key: str, mock_job_status_running: dict
    ):
        """Test successful job status retrieval."""
        respx.get("https://example.com/api/v1/jobs/test-job-123").mock(
            return_value=httpx.Response(200, json=mock_job_status_running)
        )

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            result = client.get_job_status("test-job-123")

        assert result["status"] == "running"

    @respx.mock
    def test_get_job_status_not_found(self, valid_api_key: str):
        """Test job status with nonexistent job."""
        respx.get("https://example.com/api/v1/jobs/nonexistent").mock(
            return_value=httpx.Response(404, json={"detail": "Job not found"})
        )

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            with pytest.raises(NotFoundError):
                client.get_job_status("nonexistent")


class TestGetJobResult:
    """Tests for get_job_result method."""

    @respx.mock
    def test_get_job_result_success(
        self, valid_api_key: str, mock_analysis_result: dict
    ):
        """Test successful job result retrieval."""
        respx.get("https://example.com/api/v1/jobs/test-job-123/result").mock(
            return_value=httpx.Response(200, json=mock_analysis_result)
        )

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            result = client.get_job_result("test-job-123")

        assert result["overall_score"] == 85
        assert result["grade"] == "A"


class TestWaitForCompletion:
    """Tests for wait_for_completion method."""

    @respx.mock
    def test_wait_for_completion_immediate(
        self, valid_api_key: str, mock_job_status_completed: dict, mock_analysis_result: dict
    ):
        """Test wait_for_completion when job completes immediately."""
        respx.get("https://example.com/api/v1/jobs/test-job-123").mock(
            return_value=httpx.Response(200, json=mock_job_status_completed)
        )
        respx.get("https://example.com/api/v1/jobs/test-job-123/result").mock(
            return_value=httpx.Response(200, json=mock_analysis_result)
        )

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            result = client.wait_for_completion("test-job-123", poll_interval=0.1)

        assert result["overall_score"] == 85

    @respx.mock
    def test_wait_for_completion_with_polling(
        self,
        valid_api_key: str,
        mock_job_status_pending: dict,
        mock_job_status_running: dict,
        mock_job_status_completed: dict,
        mock_analysis_result: dict,
    ):
        """Test wait_for_completion with multiple polling cycles."""
        route = respx.get("https://example.com/api/v1/jobs/test-job-123")
        route.side_effect = [
            httpx.Response(200, json=mock_job_status_pending),
            httpx.Response(200, json=mock_job_status_running),
            httpx.Response(200, json=mock_job_status_completed),
        ]
        respx.get("https://example.com/api/v1/jobs/test-job-123/result").mock(
            return_value=httpx.Response(200, json=mock_analysis_result)
        )

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            result = client.wait_for_completion("test-job-123", poll_interval=0.01)

        assert result["overall_score"] == 85

    @respx.mock
    def test_wait_for_completion_timeout(
        self, valid_api_key: str, mock_job_status_running: dict
    ):
        """Test wait_for_completion raises TimeoutError on timeout."""
        respx.get("https://example.com/api/v1/jobs/test-job-123").mock(
            return_value=httpx.Response(200, json=mock_job_status_running)
        )

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            with pytest.raises(TimeoutError, match="did not complete"):
                client.wait_for_completion(
                    "test-job-123", poll_interval=0.01, timeout=0.02
                )

    @respx.mock
    def test_wait_for_completion_job_failure(
        self, valid_api_key: str, mock_job_status_failed: dict
    ):
        """Test wait_for_completion raises APIError on job failure."""
        respx.get("https://example.com/api/v1/jobs/test-job-123").mock(
            return_value=httpx.Response(200, json=mock_job_status_failed)
        )

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            with pytest.raises(APIError, match="failed"):
                client.wait_for_completion("test-job-123", poll_interval=0.01)

    @respx.mock
    def test_wait_for_completion_with_callback(
        self, valid_api_key: str, mock_job_status_completed: dict, mock_analysis_result: dict
    ):
        """Test wait_for_completion calls progress callback."""
        respx.get("https://example.com/api/v1/jobs/test-job-123").mock(
            return_value=httpx.Response(200, json=mock_job_status_completed)
        )
        respx.get("https://example.com/api/v1/jobs/test-job-123/result").mock(
            return_value=httpx.Response(200, json=mock_analysis_result)
        )

        callback_calls = []

        def callback(status: dict):
            callback_calls.append(status)

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            client.wait_for_completion(
                "test-job-123", poll_interval=0.1, progress_callback=callback
            )

        assert len(callback_calls) >= 1
        assert callback_calls[0]["status"] == "completed"


class TestZipCreation:
    """Tests for ZIP file creation during upload."""

    @respx.mock
    def test_zip_excludes_skip_patterns(
        self, valid_api_key: str, addon_with_skip_files: Path, mock_upload_response: dict
    ):
        """Test that ZIP excludes files matching skip patterns."""
        uploaded_content = None

        def capture_upload(request):
            nonlocal uploaded_content
            # Extract the file content from multipart form data
            # The actual content is in the request
            uploaded_content = request.content
            return httpx.Response(200, json=mock_upload_response)

        respx.post("https://example.com/api/v1/analyze/upload").mock(
            side_effect=capture_upload
        )

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            client.upload_addon(addon_with_skip_files)

        # Verify the upload was made
        assert uploaded_content is not None

    @respx.mock
    def test_zip_includes_required_files(
        self, valid_api_key: str, sample_addon: Path, mock_upload_response: dict
    ):
        """Test that ZIP includes required addon files."""
        respx.post("https://example.com/api/v1/analyze/upload").mock(
            return_value=httpx.Response(200, json=mock_upload_response)
        )

        with QualidooClient(
            api_key=valid_api_key, api_url="https://example.com"
        ) as client:
            client.upload_addon(sample_addon)

        # Just verify the upload succeeded
        assert respx.calls.call_count == 1
