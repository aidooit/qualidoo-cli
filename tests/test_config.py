"""Tests for the config module."""

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from qualidoo import config


class TestValidateApiKeyFormat:
    """Tests for validate_api_key_format function."""

    def test_valid_key(self, valid_api_key: str):
        """Test that a valid API key passes validation."""
        assert config.validate_api_key_format(valid_api_key) is True

    def test_valid_key_longer(self):
        """Test that a longer valid key passes validation."""
        key = "qdoo_" + "a" * 64
        assert config.validate_api_key_format(key) is True

    def test_invalid_empty(self):
        """Test that an empty string fails validation."""
        assert config.validate_api_key_format("") is False

    def test_invalid_no_prefix(self):
        """Test that a key without qdoo_ prefix fails."""
        assert config.validate_api_key_format("a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6") is False

    def test_invalid_wrong_prefix(self):
        """Test that a key with wrong prefix fails."""
        assert config.validate_api_key_format("api_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6") is False

    def test_invalid_uppercase_prefix(self):
        """Test that uppercase prefix fails."""
        assert config.validate_api_key_format("QDOO_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6") is False

    def test_invalid_too_short(self):
        """Test that a key that's too short fails."""
        assert config.validate_api_key_format("qdoo_short") is False

    def test_invalid_special_chars(self):
        """Test that a key with special characters fails."""
        assert config.validate_api_key_format("qdoo_a1b2c3d4e5f6g7h8i9j0k1l2m3n4!@#$") is False

    def test_invalid_just_prefix(self):
        """Test that just the prefix fails."""
        assert config.validate_api_key_format("qdoo_") is False


class TestEnsureConfigDir:
    """Tests for ensure_config_dir function."""

    def test_creates_directory(self, tmp_path: Path):
        """Test that the config directory is created."""
        config_dir = tmp_path / ".qualidoo"

        with patch("qualidoo.config.CONFIG_DIR", config_dir):
            config.ensure_config_dir()

        assert config_dir.exists()
        assert config_dir.is_dir()

    def test_sets_permissions(self, tmp_path: Path):
        """Test that directory has correct permissions (0o700)."""
        config_dir = tmp_path / ".qualidoo"

        with patch("qualidoo.config.CONFIG_DIR", config_dir):
            config.ensure_config_dir()

        # Check owner-only permissions
        mode = config_dir.stat().st_mode
        assert stat.S_IMODE(mode) == 0o700

    def test_existing_directory(self, tmp_path: Path):
        """Test that existing directory is not affected."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        test_file = config_dir / "existing.txt"
        test_file.write_text("existing content")

        with patch("qualidoo.config.CONFIG_DIR", config_dir):
            config.ensure_config_dir()

        assert test_file.exists()
        assert test_file.read_text() == "existing content"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_existing_config(self, tmp_path: Path):
        """Test loading an existing config file."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text('api_key = "qdoo_test123456789012345678901234"')

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            result = config.load_config()

        assert result == {"api_key": "qdoo_test123456789012345678901234"}

    def test_load_missing_file(self, tmp_path: Path):
        """Test loading when config file doesn't exist."""
        config_dir = tmp_path / ".qualidoo"
        config_file = config_dir / "config.toml"

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            result = config.load_config()

        assert result == {}

    def test_load_empty_file(self, tmp_path: Path):
        """Test loading an empty config file."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text("")

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            result = config.load_config()

        assert result == {}

    def test_load_multiple_values(self, tmp_path: Path):
        """Test loading config with multiple values."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text(
            'api_key = "qdoo_test"\napi_url = "https://custom.example.com"'
        )

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            result = config.load_config()

        assert result["api_key"] == "qdoo_test"
        assert result["api_url"] == "https://custom.example.com"


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_creates_file(self, tmp_path: Path):
        """Test that save_config creates the config file."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            config.save_config({"api_key": "qdoo_test123456789012345678901234"})

        assert config_file.exists()
        content = config_file.read_text()
        assert "api_key" in content
        assert "qdoo_test123456789012345678901234" in content

    def test_save_sets_permissions(self, tmp_path: Path):
        """Test that saved file has correct permissions (0o600)."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            config.save_config({"api_key": "qdoo_test"})

        mode = config_file.stat().st_mode
        assert stat.S_IMODE(mode) == 0o600

    def test_save_creates_directory(self, tmp_path: Path):
        """Test that save_config creates the config directory if needed."""
        config_dir = tmp_path / ".qualidoo"
        config_file = config_dir / "config.toml"

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            config.save_config({"api_key": "qdoo_test"})

        assert config_dir.exists()
        assert config_file.exists()

    def test_save_overwrites_existing(self, tmp_path: Path):
        """Test that save_config overwrites existing config."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text('api_key = "old_key"')

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            config.save_config({"api_key": "new_key"})

        content = config_file.read_text()
        assert "new_key" in content
        assert "old_key" not in content


class TestGetApiKey:
    """Tests for get_api_key function."""

    def test_env_var_takes_precedence(self, tmp_path: Path, clean_env, valid_api_key: str):
        """Test that environment variable takes precedence over config file."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text('api_key = "qdoo_from_config_file_1234567890"')

        os.environ["QUALIDOO_API_KEY"] = valid_api_key

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            result = config.get_api_key()

        assert result == valid_api_key

    def test_falls_back_to_config_file(self, tmp_path: Path, clean_env):
        """Test that config file is used when env var is not set."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text('api_key = "qdoo_from_config_file_1234567890"')

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            result = config.get_api_key()

        assert result == "qdoo_from_config_file_1234567890"

    def test_returns_none_when_missing(self, tmp_path: Path, clean_env):
        """Test that None is returned when no API key is configured."""
        config_dir = tmp_path / ".qualidoo"
        config_file = config_dir / "config.toml"

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            result = config.get_api_key()

        assert result is None


class TestSetApiKey:
    """Tests for set_api_key function."""

    def test_saves_api_key(self, tmp_path: Path):
        """Test that set_api_key saves the key to config."""
        config_dir = tmp_path / ".qualidoo"
        config_file = config_dir / "config.toml"

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            config.set_api_key("qdoo_new_key_12345678901234567890")

            # Verify by loading
            result = config.load_config()

        assert result["api_key"] == "qdoo_new_key_12345678901234567890"

    def test_updates_existing_key(self, tmp_path: Path):
        """Test that set_api_key updates an existing key."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text('api_key = "qdoo_old_key_12345678901234567890"')

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            config.set_api_key("qdoo_new_key_12345678901234567890")
            result = config.load_config()

        assert result["api_key"] == "qdoo_new_key_12345678901234567890"

    def test_preserves_other_config(self, tmp_path: Path):
        """Test that set_api_key preserves other config values."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text('api_url = "https://custom.example.com"')

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            config.set_api_key("qdoo_test_key_123456789012345678")
            result = config.load_config()

        assert result["api_key"] == "qdoo_test_key_123456789012345678"
        assert result["api_url"] == "https://custom.example.com"


class TestRemoveApiKey:
    """Tests for remove_api_key function."""

    def test_removes_existing_key(self, tmp_path: Path):
        """Test that remove_api_key removes an existing key."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text('api_key = "qdoo_test_key_123456789012345678"')

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            result = config.remove_api_key()
            loaded = config.load_config()

        assert result is True
        assert "api_key" not in loaded

    def test_returns_false_when_not_present(self, tmp_path: Path):
        """Test that remove_api_key returns False when key doesn't exist."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text("")

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            result = config.remove_api_key()

        assert result is False

    def test_preserves_other_config(self, tmp_path: Path):
        """Test that remove_api_key preserves other config values."""
        config_dir = tmp_path / ".qualidoo"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text(
            'api_key = "qdoo_test_key_123456789012345678"\napi_url = "https://custom.com"'
        )

        with (
            patch("qualidoo.config.CONFIG_DIR", config_dir),
            patch("qualidoo.config.CONFIG_FILE", config_file),
        ):
            config.remove_api_key()
            loaded = config.load_config()

        assert "api_key" not in loaded
        assert loaded["api_url"] == "https://custom.com"


class TestGetApiUrl:
    """Tests for get_api_url function."""

    def test_returns_default_url(self, clean_env):
        """Test that default URL is returned when env var is not set."""
        result = config.get_api_url()
        assert result == config.DEFAULT_API_URL

    def test_env_var_override(self, clean_env):
        """Test that environment variable overrides default."""
        os.environ["QUALIDOO_API_URL"] = "https://custom.example.com"
        result = config.get_api_url()
        assert result == "https://custom.example.com"


class TestGetConfigPath:
    """Tests for get_config_path function."""

    def test_returns_config_file_path(self):
        """Test that get_config_path returns the config file path."""
        result = config.get_config_path()
        assert result == config.CONFIG_FILE
        assert isinstance(result, Path)
