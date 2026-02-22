"""GitHub URL parsing utilities for CLI."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ParsedRepo:
    """Parsed GitHub repository information."""

    owner: str
    repo: str
    branch: str | None = None

    @property
    def full_name(self) -> str:
        """Return the full repository name (owner/repo)."""
        return f"{self.owner}/{self.repo}"


def parse_repo(repo_input: str) -> ParsedRepo:
    """Parse a GitHub repository from various input formats.

    Accepts:
        - owner/repo
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - https://github.com/owner/repo/tree/branch
        - https://github.com/owner/repo/blob/branch
        - github.com/owner/repo
        - git@github.com:owner/repo.git

    Args:
        repo_input: Repository string in any supported format.

    Returns:
        ParsedRepo with owner, repo, and optional branch.

    Raises:
        ValueError: If the input cannot be parsed.
    """
    repo_input = repo_input.strip()

    # Try simple owner/repo format first
    simple_match = re.match(r"^([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)$", repo_input)
    if simple_match:
        return ParsedRepo(owner=simple_match.group(1), repo=simple_match.group(2))

    # Try HTTPS URL format (with optional /tree/branch or /blob/branch)
    https_match = re.match(
        r"^(?:https?://)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?(?:/(?:tree|blob)/([^/]+))?/?$",
        repo_input,
    )
    if https_match:
        return ParsedRepo(
            owner=https_match.group(1),
            repo=https_match.group(2),
            branch=https_match.group(3),
        )

    # Try SSH URL format
    ssh_match = re.match(
        r"^git@github\.com:([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?$",
        repo_input,
    )
    if ssh_match:
        return ParsedRepo(owner=ssh_match.group(1), repo=ssh_match.group(2))

    raise ValueError(
        f"Invalid repository format: {repo_input}\n"
        "Expected: owner/repo, https://github.com/owner/repo, or git@github.com:owner/repo.git"
    )


def format_repo_url(owner: str, repo: str) -> str:
    """Format a GitHub repository URL for display.

    Args:
        owner: Repository owner.
        repo: Repository name.

    Returns:
        Formatted URL string.
    """
    return f"github.com/{owner}/{repo}"
