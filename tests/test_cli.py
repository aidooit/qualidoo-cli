"""Tests for the CLI module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from qualidoo.api_client import (
    APIError,
    AuthenticationError,
    ForbiddenError,
    RateLimitError,
)
from qualidoo.cli import app

runner = CliRunner()


class TestMainCallback:
    """Tests for main callback / help display."""

    def test_help_display(self):
        """Test that --help shows usage information."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "qualidoo" in result.output.lower() or "usage" in result.output.lower()

    def test_version_if_available(self):
        """Test --version if supported."""
        result = runner.invoke(app, ["--version"])
        # May or may not be implemented
        assert result.exit_code in [0, 2]  # 2 if not implemented


class TestLoginCommand:
    """Tests for the login command."""

    def test_login_with_key_flag(self, valid_api_key: str, mock_user_info: dict):
        """Test login with --key flag."""
        with (
            patch("qualidoo.cli.validate_api_key_format", return_value=True),
            patch("qualidoo.cli.QualidooClient") as mock_client_class,
            patch("qualidoo.cli.set_api_key") as mock_set_key,
            patch("qualidoo.cli.print_success"),
            patch("qualidoo.cli.print_user_info"),
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.validate_key.return_value = mock_user_info
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["login", "--key", valid_api_key])

            assert result.exit_code == 0
            mock_set_key.assert_called_once_with(valid_api_key)

    def test_login_interactive(self, valid_api_key: str, mock_user_info: dict):
        """Test login with interactive prompt."""
        with (
            patch("qualidoo.cli.validate_api_key_format", return_value=True),
            patch("qualidoo.cli.QualidooClient") as mock_client_class,
            patch("qualidoo.cli.set_api_key"),
            patch("qualidoo.cli.print_success"),
            patch("qualidoo.cli.print_user_info"),
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.validate_key.return_value = mock_user_info
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["login"], input=f"{valid_api_key}\n")

            assert result.exit_code == 0

    def test_login_invalid_key_format(self):
        """Test login with invalid key format."""
        with patch("qualidoo.cli.validate_api_key_format", return_value=False):
            result = runner.invoke(app, ["login", "--key", "invalid_key"])

            assert result.exit_code == 1

    def test_login_auth_failure(self, valid_api_key: str):
        """Test login with authentication failure."""
        with (
            patch("qualidoo.cli.validate_api_key_format", return_value=True),
            patch("qualidoo.cli.QualidooClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.validate_key.side_effect = AuthenticationError("Invalid API key")
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["login", "--key", valid_api_key])

            assert result.exit_code == 1

    def test_login_forbidden(self, valid_api_key: str):
        """Test login with forbidden response."""
        with (
            patch("qualidoo.cli.validate_api_key_format", return_value=True),
            patch("qualidoo.cli.QualidooClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.validate_key.side_effect = ForbiddenError("Access denied")
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["login", "--key", valid_api_key])

            assert result.exit_code == 1


class TestLogoutCommand:
    """Tests for the logout command."""

    def test_logout_when_logged_in(self):
        """Test logout when API key is configured."""
        with (
            patch("qualidoo.cli.remove_api_key", return_value=True),
            patch("qualidoo.cli.print_success"),
        ):
            result = runner.invoke(app, ["logout"])

            assert result.exit_code == 0

    def test_logout_when_not_logged_in(self):
        """Test logout when no API key configured."""
        with patch("qualidoo.cli.remove_api_key", return_value=False):
            result = runner.invoke(app, ["logout"])

            assert result.exit_code == 0
            assert "No API key was configured" in result.output


class TestWhoamiCommand:
    """Tests for the whoami command."""

    def test_whoami_success(self, valid_api_key: str, mock_user_info: dict):
        """Test whoami with valid authentication."""
        with (
            patch("qualidoo.cli.get_api_key", return_value=valid_api_key),
            patch("qualidoo.cli.QualidooClient") as mock_client_class,
            patch("qualidoo.cli.print_user_info"),
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.validate_key.return_value = mock_user_info
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["whoami"])

            assert result.exit_code == 0

    def test_whoami_not_logged_in(self):
        """Test whoami when not logged in."""
        with (
            patch("qualidoo.cli.get_api_key", return_value=None),
            patch("qualidoo.cli.print_error"),
        ):
            result = runner.invoke(app, ["whoami"])

            assert result.exit_code == 1

    def test_whoami_auth_failure(self, valid_api_key: str):
        """Test whoami with authentication failure."""
        with (
            patch("qualidoo.cli.get_api_key", return_value=valid_api_key),
            patch("qualidoo.cli.QualidooClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.validate_key.side_effect = AuthenticationError("Invalid key")
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["whoami"])

            assert result.exit_code == 1


class TestCheckCommand:
    """Tests for the check command."""

    def test_check_full_workflow(
        self,
        valid_api_key: str,
        sample_addon: Path,
        mock_upload_response: dict,
        mock_analysis_result: dict,
    ):
        """Test check command full workflow."""
        with (
            patch("qualidoo.cli.get_api_key", return_value=valid_api_key),
            patch("qualidoo.cli.QualidooClient") as mock_client_class,
            patch("qualidoo.cli.print_analysis_result"),
            patch("qualidoo.cli.create_progress_callback") as mock_progress,
        ):
            mock_callback = MagicMock()
            mock_callback.stop = MagicMock()
            mock_progress.return_value = mock_callback

            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.upload_addon.return_value = mock_upload_response
            mock_client.wait_for_completion.return_value = mock_analysis_result
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["check", str(sample_addon)])

            assert result.exit_code == 0
            mock_client.upload_addon.assert_called_once()
            mock_client.wait_for_completion.assert_called_once()

    def test_check_verbose_mode(
        self,
        valid_api_key: str,
        sample_addon: Path,
        mock_upload_response: dict,
        mock_analysis_result: dict,
    ):
        """Test check command with --verbose flag."""
        with (
            patch("qualidoo.cli.get_api_key", return_value=valid_api_key),
            patch("qualidoo.cli.QualidooClient") as mock_client_class,
            patch("qualidoo.cli.print_analysis_result") as mock_print,
            patch("qualidoo.cli.create_progress_callback") as mock_progress,
        ):
            mock_callback = MagicMock()
            mock_callback.stop = MagicMock()
            mock_progress.return_value = mock_callback

            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.upload_addon.return_value = mock_upload_response
            mock_client.wait_for_completion.return_value = mock_analysis_result
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["check", str(sample_addon), "--verbose"])

            assert result.exit_code == 0
            # Verify verbose=True was passed
            mock_print.assert_called_once()
            call_kwargs = mock_print.call_args
            assert call_kwargs[1].get("verbose") is True or (
                len(call_kwargs[0]) > 2 and call_kwargs[0][2] is True
            )

    def test_check_save_option(
        self,
        valid_api_key: str,
        sample_addon: Path,
        mock_upload_response: dict,
        mock_analysis_result: dict,
        tmp_path: Path,
    ):
        """Test check command with --save flag."""
        output_file = tmp_path / "result.json"

        with (
            patch("qualidoo.cli.get_api_key", return_value=valid_api_key),
            patch("qualidoo.cli.QualidooClient") as mock_client_class,
            patch("qualidoo.cli.print_analysis_result"),
            patch("qualidoo.cli.create_progress_callback") as mock_progress,
        ):
            mock_callback = MagicMock()
            mock_callback.stop = MagicMock()
            mock_progress.return_value = mock_callback

            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.upload_addon.return_value = mock_upload_response
            mock_client.wait_for_completion.return_value = mock_analysis_result
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app, ["check", str(sample_addon), "--save", str(output_file)]
            )

            assert result.exit_code == 0
            assert output_file.exists()
            saved_data = json.loads(output_file.read_text())
            assert saved_data["overall_score"] == 85

    def test_check_missing_manifest(
        self, valid_api_key: str, addon_without_manifest: Path
    ):
        """Test check command with missing __manifest__.py."""
        with patch("qualidoo.cli.get_api_key", return_value=valid_api_key):
            result = runner.invoke(app, ["check", str(addon_without_manifest)])

            assert result.exit_code == 1
            assert "__manifest__.py" in result.output or "manifest" in result.output.lower()

    def test_check_not_logged_in(self, sample_addon: Path):
        """Test check command when not logged in."""
        with patch("qualidoo.cli.get_api_key", return_value=None):
            result = runner.invoke(app, ["check", str(sample_addon)])

            assert result.exit_code == 1

    def test_check_rate_limit(
        self, valid_api_key: str, sample_addon: Path, mock_upload_response: dict
    ):
        """Test check command with rate limit error."""
        with (
            patch("qualidoo.cli.get_api_key", return_value=valid_api_key),
            patch("qualidoo.cli.QualidooClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.upload_addon.side_effect = RateLimitError("Rate limit exceeded")
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["check", str(sample_addon)])

            assert result.exit_code == 1
            assert "rate" in result.output.lower() or "limit" in result.output.lower()

    def test_check_timeout(
        self, valid_api_key: str, sample_addon: Path, mock_upload_response: dict
    ):
        """Test check command with timeout."""
        with (
            patch("qualidoo.cli.get_api_key", return_value=valid_api_key),
            patch("qualidoo.cli.QualidooClient") as mock_client_class,
            patch("qualidoo.cli.create_progress_callback") as mock_progress,
        ):
            mock_callback = MagicMock()
            mock_callback.stop = MagicMock()
            mock_progress.return_value = mock_callback

            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.upload_addon.return_value = mock_upload_response
            mock_client.wait_for_completion.side_effect = TimeoutError("Analysis timed out")
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["check", str(sample_addon)])

            assert result.exit_code == 1
            assert "timeout" in result.output.lower() or "timed out" in result.output.lower()

    def test_check_with_timeout_option(
        self,
        valid_api_key: str,
        sample_addon: Path,
        mock_upload_response: dict,
        mock_analysis_result: dict,
    ):
        """Test check command with --timeout option."""
        with (
            patch("qualidoo.cli.get_api_key", return_value=valid_api_key),
            patch("qualidoo.cli.QualidooClient") as mock_client_class,
            patch("qualidoo.cli.print_analysis_result"),
            patch("qualidoo.cli.create_progress_callback") as mock_progress,
        ):
            mock_callback = MagicMock()
            mock_callback.stop = MagicMock()
            mock_progress.return_value = mock_callback

            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.upload_addon.return_value = mock_upload_response
            mock_client.wait_for_completion.return_value = mock_analysis_result
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app, ["check", str(sample_addon), "--timeout", "600"]
            )

            assert result.exit_code == 0
            # Verify timeout was passed
            call_kwargs = mock_client.wait_for_completion.call_args
            assert call_kwargs[1].get("timeout") == 600 or (
                len(call_kwargs[0]) > 2 and call_kwargs[0][2] == 600
            )

    def test_check_api_error(
        self, valid_api_key: str, sample_addon: Path
    ):
        """Test check command with generic API error."""
        with (
            patch("qualidoo.cli.get_api_key", return_value=valid_api_key),
            patch("qualidoo.cli.QualidooClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.upload_addon.side_effect = APIError("Server error")
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["check", str(sample_addon)])

            assert result.exit_code == 1


class TestConfigCommand:
    """Tests for the config command."""

    def test_config_show(self, tmp_path: Path, valid_api_key: str):
        """Test config command shows configuration."""
        config_file = tmp_path / "config.toml"

        with (
            patch("qualidoo.cli.load_config", return_value={"api_key": valid_api_key}),
            patch("qualidoo.cli.get_config_path", return_value=config_file),
            patch("qualidoo.cli.print_config_info") as mock_print,
        ):
            result = runner.invoke(app, ["config"])

            assert result.exit_code == 0
            mock_print.assert_called_once()

    def test_config_show_flag(self, tmp_path: Path):
        """Test config command with --show flag."""
        config_file = tmp_path / "config.toml"

        with (
            patch("qualidoo.cli.load_config", return_value={}),
            patch("qualidoo.cli.get_config_path", return_value=config_file),
            patch("qualidoo.cli.print_config_info") as mock_print,
        ):
            result = runner.invoke(app, ["config", "--show"])

            assert result.exit_code == 0
            mock_print.assert_called_once()


class TestDefaultDirectory:
    """Tests for default directory behavior."""

    def test_check_uses_current_dir_by_default(
        self,
        valid_api_key: str,
        sample_addon: Path,
        mock_upload_response: dict,
        mock_analysis_result: dict,
        monkeypatch,
    ):
        """Test that check uses current directory when no path provided."""
        # Change to the sample addon directory
        monkeypatch.chdir(sample_addon)

        with (
            patch("qualidoo.cli.get_api_key", return_value=valid_api_key),
            patch("qualidoo.cli.QualidooClient") as mock_client_class,
            patch("qualidoo.cli.print_analysis_result"),
            patch("qualidoo.cli.create_progress_callback") as mock_progress,
        ):
            mock_callback = MagicMock()
            mock_callback.stop = MagicMock()
            mock_progress.return_value = mock_callback

            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.upload_addon.return_value = mock_upload_response
            mock_client.wait_for_completion.return_value = mock_analysis_result
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["check"])

            assert result.exit_code == 0
