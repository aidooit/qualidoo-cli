"""HTTP client for Qualidoo API with authentication."""

import time
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx

from qualidoo.config import get_api_key, get_api_url


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthenticationError(APIError):
    """Raised when authentication fails (401)."""

    pass


class ForbiddenError(APIError):
    """Raised when access is forbidden (403) - e.g., free tier."""

    pass


class RateLimitError(APIError):
    """Raised when rate limited (429)."""

    pass


class NotFoundError(APIError):
    """Raised when resource not found (404)."""

    pass


class QualidooClient:
    """HTTP client for Qualidoo API."""

    def __init__(self, api_key: str | None = None, api_url: str | None = None):
        """Initialize client with API key and URL.

        Args:
            api_key: API key to use. If None, will be loaded from config/env.
            api_url: API URL to use. If None, will be loaded from config/env.
        """
        self.api_key = api_key or get_api_key()
        self.api_url = (api_url or get_api_url()).rstrip("/")
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {"User-Agent": "qualidoo-cli/0.2.0"}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            self._client = httpx.Client(
                base_url=self.api_url,
                headers=headers,
                timeout=60.0,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "QualidooClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate exceptions."""
        if response.status_code == 401:
            raise AuthenticationError(
                "Authentication failed. Run 'qualidoo login' to reconfigure.",
                status_code=401,
            )
        elif response.status_code == 403:
            try:
                detail = response.json().get("detail", "")
            except Exception:
                detail = ""
            if "tier" in detail.lower() or "subscription" in detail.lower():
                raise ForbiddenError(
                    "API access requires Pro subscription. Upgrade at https://qualidoo.com",
                    status_code=403,
                )
            raise ForbiddenError(f"Access forbidden: {detail}", status_code=403)
        elif response.status_code == 404:
            raise NotFoundError("Resource not found.", status_code=404)
        elif response.status_code == 429:
            raise RateLimitError(
                "Rate limit exceeded. Try again later.",
                status_code=429,
            )
        elif response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise APIError(f"API error: {detail}", status_code=response.status_code)

        # Parse JSON response
        try:
            result = response.json()
        except Exception as e:
            raise APIError(f"Invalid response from server: {e}", status_code=response.status_code)

        if result is None:
            raise APIError(
                "Empty response from server. The server may need to be updated.",
                status_code=response.status_code,
            )

        return result

    def validate_key(self) -> dict[str, Any]:
        """Validate the API key by calling /api/v1/auth/me.

        Returns:
            User information dict if valid.

        Raises:
            AuthenticationError: If key is invalid.
            APIError: For other API errors.
        """
        response = self.client.get("/api/v1/auth/me")
        return self._handle_response(response)

    def upload_addon(self, addon_path: Path) -> dict[str, Any]:
        """Upload an addon for analysis.

        Args:
            addon_path: Path to the addon directory.

        Returns:
            Dict containing job_id and other info.

        Raises:
            APIError: For API errors.
            FileNotFoundError: If addon path doesn't exist.
        """
        if not addon_path.exists():
            raise FileNotFoundError(f"Addon path not found: {addon_path}")

        if not addon_path.is_dir():
            raise ValueError(f"Addon path must be a directory: {addon_path}")

        # Create ZIP file in memory
        zip_buffer = BytesIO()
        addon_name = addon_path.name

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in addon_path.rglob("*"):
                if file_path.is_file():
                    # Skip common non-essential files
                    if self._should_skip_file(file_path):
                        continue
                    arcname = f"{addon_name}/{file_path.relative_to(addon_path)}"
                    zf.write(file_path, arcname)

        zip_buffer.seek(0)

        # Upload (with client=cli to identify CLI uploads)
        files = {"file": (f"{addon_name}.zip", zip_buffer, "application/zip")}
        response = self.client.post("/api/v1/analyze/upload", files=files, params={"client": "cli"})
        return self._handle_response(response)

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped when zipping."""
        skip_patterns = {
            "__pycache__",
            ".git",
            ".svn",
            ".hg",
            ".pyc",
            ".pyo",
            ".egg-info",
            ".eggs",
            "node_modules",
            ".venv",
            "venv",
        }
        parts = file_path.parts
        for part in parts:
            if part in skip_patterns or part.endswith(".pyc"):
                return True
        return False

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get the status of an analysis job.

        Args:
            job_id: The job ID returned from upload_addon.

        Returns:
            Dict containing job status.
        """
        response = self.client.get(f"/api/v1/jobs/{job_id}")
        return self._handle_response(response)

    def get_job_result(self, job_id: str) -> dict[str, Any]:
        """Get the result of a completed analysis job.

        Args:
            job_id: The job ID returned from upload_addon.

        Returns:
            Dict containing analysis results.
        """
        response = self.client.get(f"/api/v1/jobs/{job_id}/result")
        return self._handle_response(response)

    def wait_for_completion(
        self,
        job_id: str,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
        progress_callback: Any = None,
    ) -> dict[str, Any]:
        """Poll until job completes and return the result.

        Args:
            job_id: The job ID to wait for.
            poll_interval: Seconds between status checks.
            timeout: Maximum seconds to wait.
            progress_callback: Optional callback(status_dict) called on each poll.

        Returns:
            Analysis result dict.

        Raises:
            TimeoutError: If job doesn't complete within timeout.
            APIError: If job fails or other API error.
        """
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")

            status = self.get_job_status(job_id)

            if progress_callback:
                progress_callback(status)

            job_status = status.get("status", "").lower()

            if job_status == "completed":
                return self.get_job_result(job_id)
            elif job_status == "failed":
                error = status.get("error", "Unknown error")
                raise APIError(f"Analysis failed: {error}")
            elif job_status in ("pending", "running", "processing"):
                time.sleep(poll_interval)
            else:
                # Unknown status, keep polling
                time.sleep(poll_interval)

    # =========================================================================
    # GitHub Repository Methods
    # =========================================================================

    def get_github_status(self) -> dict[str, Any]:
        """Check if the user has GitHub connected.

        Returns:
            Dict with 'connected', 'username', and 'message' fields.

        Raises:
            APIError: For API errors.
        """
        response = self.client.get("/api/v1/cli/github/status")
        return self._handle_response(response)

    def discover_addons(
        self,
        owner: str,
        repo: str,
        branch: str | None = None,
    ) -> dict[str, Any]:
        """Discover Odoo addons in a GitHub repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            branch: Branch to scan (defaults to repo default branch).

        Returns:
            Dict with 'repo', 'branch', 'addons', and 'total' fields.

        Raises:
            APIError: For API errors.
            NotFoundError: If repository not found.
        """
        url = f"/api/v1/cli/github/repos/{owner}/{repo}/addons"
        params = {}
        if branch:
            params["branch"] = branch
        response = self.client.get(url, params=params)
        return self._handle_response(response)

    def start_repo_analysis(
        self,
        repo: str,
        branch: str | None = None,
        addon_path: str | None = None,
        use_llm: bool = False,
    ) -> dict[str, Any]:
        """Start analysis of addons in a GitHub repository.

        Args:
            repo: Repository in 'owner/repo' format.
            branch: Branch to analyze (defaults to repo default branch).
            addon_path: Specific addon path to analyze, or all if None.
            use_llm: Enable LLM-enhanced analysis.

        Returns:
            Dict with 'scan_id' and 'total_addons' fields.

        Raises:
            APIError: For API errors.
            NotFoundError: If repository or addon not found.
        """
        payload: dict[str, Any] = {"repo": repo}
        if branch:
            payload["branch"] = branch
        if addon_path:
            payload["addon_path"] = addon_path
        payload["use_llm"] = use_llm

        response = self.client.post("/api/v1/cli/github/analyze", json=payload)
        return self._handle_response(response)

    def get_scan_status(self, scan_id: str) -> dict[str, Any]:
        """Get the status of a repository scan with per-addon results.

        Args:
            scan_id: The scan ID returned from start_repo_analysis.

        Returns:
            Dict with scan status and per-addon results.

        Raises:
            APIError: For API errors.
            NotFoundError: If scan not found.
        """
        response = self.client.get(f"/api/v1/cli/github/scans/{scan_id}")
        return self._handle_response(response)

    def wait_for_scan_completion(
        self,
        scan_id: str,
        poll_interval: float = 2.0,
        timeout: float = 600.0,
        progress_callback: Any = None,
    ) -> dict[str, Any]:
        """Poll until scan completes and return the final status.

        Args:
            scan_id: The scan ID to wait for.
            poll_interval: Seconds between status checks.
            timeout: Maximum seconds to wait.
            progress_callback: Optional callback(status_dict) called on each poll.

        Returns:
            Final scan status dict with all results.

        Raises:
            TimeoutError: If scan doesn't complete within timeout.
            APIError: If scan fails or other API error.
        """
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(
                    f"Scan {scan_id} did not complete within {timeout} seconds. "
                    "Try with --addon to analyze a single module."
                )

            status = self.get_scan_status(scan_id)

            if progress_callback:
                progress_callback(status)

            scan_status = status.get("status", "").lower()

            if scan_status == "completed":
                return status
            elif scan_status == "failed":
                error = status.get("error_message", "Unknown error")
                raise APIError(f"Scan failed: {error}")
            elif scan_status in ("pending", "discovering", "analyzing"):
                time.sleep(poll_interval)
            else:
                # Unknown status, keep polling
                time.sleep(poll_interval)

    def get_integrations(self) -> list[dict[str, Any]]:
        """Get all integrations for the current user.

        Returns:
            List of integration dicts.

        Raises:
            APIError: For API errors.
        """
        response = self.client.get("/api/v1/integrations")
        return self._handle_response(response)
