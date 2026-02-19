"""Configuration management for Qualidoo CLI.

Stores API key in ~/.qualidoo/config.toml with secure permissions.
Supports QUALIDOO_API_KEY environment variable override.
"""

import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

import tomli_w

CONFIG_DIR = Path.home() / ".qualidoo"
CONFIG_FILE = CONFIG_DIR / "config.toml"
API_KEY_PREFIX = "qdoo_"
API_KEY_PATTERN = re.compile(r"^qdoo_[a-zA-Z0-9]{32,}$")

DEFAULT_API_URL = "https://qualidoo.aidooit.com"


def ensure_config_dir() -> None:
    """Create config directory with secure permissions if it doesn't exist."""
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(mode=0o700, parents=True)


def load_config() -> dict[str, Any]:
    """Load configuration from config file."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        with CONFIG_FILE.open("rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to config file with secure permissions."""
    ensure_config_dir()
    with CONFIG_FILE.open("wb") as f:
        tomli_w.dump(config, f)
    # Set file permissions to owner-only (0600)
    CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)


def get_api_key() -> str | None:
    """Get API key from environment variable or config file.

    Environment variable QUALIDOO_API_KEY takes precedence.
    """
    # Check environment variable first
    env_key = os.environ.get("QUALIDOO_API_KEY")
    if env_key:
        return env_key

    # Fall back to config file
    config = load_config()
    return config.get("api_key")


def set_api_key(api_key: str) -> None:
    """Save API key to config file."""
    config = load_config()
    config["api_key"] = api_key
    save_config(config)


def remove_api_key() -> bool:
    """Remove API key from config file. Returns True if key was removed."""
    config = load_config()
    if "api_key" in config:
        del config["api_key"]
        save_config(config)
        return True
    return False


def validate_api_key_format(api_key: str) -> bool:
    """Validate API key format (should start with 'qdoo_' and have valid characters)."""
    return bool(API_KEY_PATTERN.match(api_key))


def get_api_url() -> str:
    """Get API URL from environment variable or default."""
    return os.environ.get("QUALIDOO_API_URL", DEFAULT_API_URL)


def get_config_path() -> Path:
    """Get the path to the config file."""
    return CONFIG_FILE
