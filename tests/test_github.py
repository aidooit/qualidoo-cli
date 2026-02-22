"""Tests for GitHub URL parsing utilities."""

from __future__ import annotations

import pytest

from qualidoo.github import format_repo_url, parse_repo, ParsedRepo


class TestParseRepo:
    """Tests for parse_repo function."""

    def test_parse_simple_format(self) -> None:
        """Test parsing simple owner/repo format."""
        result = parse_repo("oca/account-financial-tools")
        assert result.owner == "oca"
        assert result.repo == "account-financial-tools"
        assert result.full_name == "oca/account-financial-tools"

    def test_parse_https_url(self) -> None:
        """Test parsing HTTPS URL format."""
        result = parse_repo("https://github.com/oca/account-financial-tools")
        assert result.owner == "oca"
        assert result.repo == "account-financial-tools"

    def test_parse_https_url_with_git_extension(self) -> None:
        """Test parsing HTTPS URL with .git extension."""
        result = parse_repo("https://github.com/oca/account-financial-tools.git")
        assert result.owner == "oca"
        assert result.repo == "account-financial-tools"

    def test_parse_https_url_without_protocol(self) -> None:
        """Test parsing github.com URL without https://."""
        result = parse_repo("github.com/oca/account-financial-tools")
        assert result.owner == "oca"
        assert result.repo == "account-financial-tools"

    def test_parse_https_url_with_trailing_slash(self) -> None:
        """Test parsing HTTPS URL with trailing slash."""
        result = parse_repo("https://github.com/oca/account-financial-tools/")
        assert result.owner == "oca"
        assert result.repo == "account-financial-tools"

    def test_parse_ssh_url(self) -> None:
        """Test parsing SSH URL format."""
        result = parse_repo("git@github.com:oca/account-financial-tools.git")
        assert result.owner == "oca"
        assert result.repo == "account-financial-tools"

    def test_parse_ssh_url_without_extension(self) -> None:
        """Test parsing SSH URL without .git extension."""
        result = parse_repo("git@github.com:oca/account-financial-tools")
        assert result.owner == "oca"
        assert result.repo == "account-financial-tools"

    def test_parse_with_underscores_and_dots(self) -> None:
        """Test parsing repo names with underscores and dots."""
        result = parse_repo("owner_name/repo.name-123")
        assert result.owner == "owner_name"
        assert result.repo == "repo.name-123"

    def test_parse_strips_whitespace(self) -> None:
        """Test that whitespace is stripped from input."""
        result = parse_repo("  oca/account-financial-tools  ")
        assert result.owner == "oca"
        assert result.repo == "account-financial-tools"

    def test_parse_invalid_format_raises_error(self) -> None:
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid repository format"):
            parse_repo("not-a-valid-repo")

    def test_parse_empty_string_raises_error(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid repository format"):
            parse_repo("")

    def test_parse_too_many_slashes_raises_error(self) -> None:
        """Test that too many slashes raises ValueError."""
        with pytest.raises(ValueError, match="Invalid repository format"):
            parse_repo("owner/repo/extra")

    def test_parse_https_url_with_tree_branch(self) -> None:
        """Test parsing HTTPS URL with /tree/branch path."""
        result = parse_repo("https://github.com/OCA/mail/tree/17.0")
        assert result.owner == "OCA"
        assert result.repo == "mail"
        assert result.branch == "17.0"

    def test_parse_https_url_with_blob_branch(self) -> None:
        """Test parsing HTTPS URL with /blob/branch path."""
        result = parse_repo("https://github.com/OCA/mail/blob/main")
        assert result.owner == "OCA"
        assert result.repo == "mail"
        assert result.branch == "main"

    def test_parse_https_url_branch_with_dots(self) -> None:
        """Test parsing URL with branch name containing dots."""
        result = parse_repo("https://github.com/OCA/mail/tree/16.0-dev")
        assert result.owner == "OCA"
        assert result.repo == "mail"
        assert result.branch == "16.0-dev"

    def test_parse_branch_is_none_when_not_present(self) -> None:
        """Test that branch is None for URLs without branch path."""
        result = parse_repo("https://github.com/OCA/mail")
        assert result.owner == "OCA"
        assert result.repo == "mail"
        assert result.branch is None

    def test_parse_simple_format_has_no_branch(self) -> None:
        """Test that simple owner/repo format has no branch."""
        result = parse_repo("OCA/mail")
        assert result.owner == "OCA"
        assert result.repo == "mail"
        assert result.branch is None


class TestParsedRepo:
    """Tests for ParsedRepo dataclass."""

    def test_full_name_property(self) -> None:
        """Test full_name property."""
        repo = ParsedRepo(owner="test-owner", repo="test-repo")
        assert repo.full_name == "test-owner/test-repo"

    def test_branch_default_is_none(self) -> None:
        """Test that branch defaults to None."""
        repo = ParsedRepo(owner="test-owner", repo="test-repo")
        assert repo.branch is None

    def test_branch_can_be_set(self) -> None:
        """Test that branch can be set."""
        repo = ParsedRepo(owner="test-owner", repo="test-repo", branch="17.0")
        assert repo.branch == "17.0"


class TestFormatRepoUrl:
    """Tests for format_repo_url function."""

    def test_format_repo_url(self) -> None:
        """Test formatting repo URL for display."""
        result = format_repo_url("oca", "account-financial-tools")
        assert result == "github.com/oca/account-financial-tools"
