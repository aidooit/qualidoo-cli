"""Shared test fixtures for qualidoo-cli tests."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def valid_api_key() -> str:
    """Return a valid API key format."""
    return "qdoo_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"


@pytest.fixture
def invalid_api_keys() -> list[str]:
    """Return a list of invalid API key formats."""
    return [
        "",
        "invalid",
        "qdoo",
        "qdoo_",
        "qdoo_short",  # Too short
        "api_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",  # Wrong prefix
        "QDOO_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",  # Wrong case prefix
    ]


@pytest.fixture
def mock_user_info() -> dict:
    """Return a mock user info response from the API."""
    return {
        "email": "test@example.com",
        "tier": "free",
        "analyses_this_month": 5,
        "analyses_limit": 10,
        "api_requests_today": 3,
        "api_limit": 100,
    }


@pytest.fixture
def mock_user_info_unlimited() -> dict:
    """Return a mock user info response with unlimited calls."""
    return {
        "email": "enterprise@example.com",
        "tier": "enterprise",
        "analyses_this_month": 50,
        "analyses_limit": None,
        "api_requests_today": 200,
        "api_limit": None,
    }


@pytest.fixture
def mock_upload_response() -> dict:
    """Return a mock upload response."""
    return {
        "job_id": "test-job-123",
        "message": "Addon uploaded successfully",
    }


@pytest.fixture
def mock_job_status_pending() -> dict:
    """Return a mock job status for a pending job."""
    return {
        "job_id": "test-job-123",
        "status": "pending",
        "message": "Waiting in queue",
    }


@pytest.fixture
def mock_job_status_running() -> dict:
    """Return a mock job status for a running job."""
    return {
        "job_id": "test-job-123",
        "status": "running",
        "message": "Analysis in progress",
    }


@pytest.fixture
def mock_job_status_completed() -> dict:
    """Return a mock job status for a completed job."""
    return {
        "job_id": "test-job-123",
        "status": "completed",
        "message": "Analysis complete",
    }


@pytest.fixture
def mock_job_status_failed() -> dict:
    """Return a mock job status for a failed job."""
    return {
        "job_id": "test-job-123",
        "status": "failed",
        "error": "Analysis failed: invalid addon structure",
    }


@pytest.fixture
def mock_analysis_result() -> dict:
    """Return a complete mock analysis result."""
    return {
        "job_id": "test-job-123",
        "addon_name": "test_addon",
        "addon_version": "16.0.1.0.0",
        "addon_category": "Uncategorized",
        "addon_author": "Test Author",
        "addon_website": "https://example.com",
        "odoo_version": "16.0",
        "overall_score": 85,
        "grade": "A",
        "agent_results": [
            {
                "agent_name": "python_quality",
                "display_name": "Python Quality",
                "score": 90,
                "findings": [
                    {
                        "message": "Function too long",
                        "severity": "MINOR",
                        "category": "maintainability",
                        "file_path": "models/test.py",
                        "line_number": 42,
                        "suggestion": "Consider breaking into smaller functions",
                        "ignored": False,
                    }
                ],
                "recommendations": ["Add type hints to functions"],
                "critical_count": 0,
                "major_count": 0,
                "minor_count": 1,
                "info_count": 0,
            },
            {
                "agent_name": "security",
                "display_name": "Security",
                "score": 75,
                "findings": [
                    {
                        "message": "SQL query without ORM",
                        "severity": "MAJOR",
                        "category": "security",
                        "file_path": "models/test.py",
                        "line_number": 100,
                        "suggestion": "Use ORM methods instead of raw SQL",
                        "ignored": False,
                    }
                ],
                "recommendations": ["Review all database queries"],
                "critical_count": 0,
                "major_count": 1,
                "minor_count": 0,
                "info_count": 0,
            },
        ],
        "summary": "Good overall quality with some security concerns",
        "top_issues": [
            {
                "message": "SQL query without ORM",
                "severity": "MAJOR",
                "category": "security",
                "file_path": "models/test.py",
                "line_number": 100,
                "suggestion": "Use ORM methods instead of raw SQL",
            },
            {
                "message": "Function too long",
                "severity": "MINOR",
                "category": "maintainability",
                "file_path": "models/test.py",
                "line_number": 42,
                "suggestion": "Consider breaking into smaller functions",
            },
        ],
        "analyzed_at": "2024-01-15T10:30:00Z",
    }


@pytest.fixture
def mock_analysis_result_empty() -> dict:
    """Return a mock analysis result with no issues."""
    return {
        "job_id": "test-job-456",
        "addon_name": "perfect_addon",
        "addon_version": "16.0.1.0.0",
        "addon_category": "Uncategorized",
        "addon_author": "Test Author",
        "addon_website": "",
        "odoo_version": "16.0",
        "overall_score": 100,
        "grade": "A+",
        "agent_results": [],
        "summary": "Perfect score with no issues",
        "top_issues": [],
        "analyzed_at": "2024-01-15T10:30:00Z",
    }


@pytest.fixture
def mock_config_dir(tmp_path: Path):
    """Create a temporary config directory and patch config module paths."""
    config_dir = tmp_path / ".qualidoo"
    config_file = config_dir / "config.toml"

    with (
        patch("qualidoo.config.CONFIG_DIR", config_dir),
        patch("qualidoo.config.CONFIG_FILE", config_file),
    ):
        yield {"dir": config_dir, "file": config_file}


@pytest.fixture
def clean_env():
    """Remove QUALIDOO_* environment variables and restore after test."""
    env_vars = ["QUALIDOO_API_KEY", "QUALIDOO_API_URL"]
    saved = {}

    for var in env_vars:
        if var in os.environ:
            saved[var] = os.environ.pop(var)

    yield

    for var, value in saved.items():
        os.environ[var] = value
    for var in env_vars:
        if var not in saved and var in os.environ:
            del os.environ[var]


@pytest.fixture
def sample_addon(tmp_path: Path) -> Path:
    """Create a valid Odoo addon structure."""
    addon_dir = tmp_path / "test_addon"
    addon_dir.mkdir()

    manifest = addon_dir / "__manifest__.py"
    manifest.write_text(
        """{
    "name": "Test Addon",
    "version": "16.0.1.0.0",
    "depends": ["base"],
    "author": "Test Author",
}
"""
    )

    init = addon_dir / "__init__.py"
    init.write_text("from . import models\n")

    models_dir = addon_dir / "models"
    models_dir.mkdir()

    models_init = models_dir / "__init__.py"
    models_init.write_text("from . import test_model\n")

    models_file = models_dir / "test_model.py"
    models_file.write_text(
        """from odoo import models, fields

class TestModel(models.Model):
    _name = "test.model"
    _description = "Test Model"

    name = fields.Char(string="Name", required=True)
"""
    )

    return addon_dir


@pytest.fixture
def addon_without_manifest(tmp_path: Path) -> Path:
    """Create an addon directory without __manifest__.py."""
    addon_dir = tmp_path / "invalid_addon"
    addon_dir.mkdir()

    init = addon_dir / "__init__.py"
    init.write_text("# No manifest\n")

    return addon_dir


@pytest.fixture
def addon_with_skip_files(tmp_path: Path) -> Path:
    """Create an addon with files that should be skipped during upload."""
    addon_dir = tmp_path / "addon_with_skips"
    addon_dir.mkdir()

    manifest = addon_dir / "__manifest__.py"
    manifest.write_text('{"name": "Test", "version": "16.0.1.0.0", "depends": ["base"]}')

    # Files that should be skipped
    pycache = addon_dir / "__pycache__"
    pycache.mkdir()
    (pycache / "test.cpython-311.pyc").write_bytes(b"fake bytecode")

    git_dir = addon_dir / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("fake git config")

    venv_dir = addon_dir / "venv"
    venv_dir.mkdir()
    (venv_dir / "bin").mkdir()

    node_modules = addon_dir / "node_modules"
    node_modules.mkdir()
    (node_modules / "package").mkdir()

    # Files that should be included
    (addon_dir / "__init__.py").write_text("# init\n")
    (addon_dir / "models.py").write_text("# models\n")

    return addon_dir
