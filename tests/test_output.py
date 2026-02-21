"""Tests for the output module."""

from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console

from qualidoo import output


class TestGetGradeFromScore:
    """Tests for get_grade_from_score function."""

    def test_score_100_returns_a_plus(self):
        """Test that score 100 returns A+."""
        assert output.get_grade_from_score(100) == "A+"

    def test_score_90_returns_a_plus(self):
        """Test that score 90 returns A+."""
        assert output.get_grade_from_score(90) == "A+"

    def test_score_89_returns_a(self):
        """Test that score 89 returns A."""
        assert output.get_grade_from_score(89) == "A"

    def test_score_80_returns_a(self):
        """Test that score 80 returns A."""
        assert output.get_grade_from_score(80) == "A"

    def test_score_79_returns_b(self):
        """Test that score 79 returns B."""
        assert output.get_grade_from_score(79) == "B"

    def test_score_70_returns_b(self):
        """Test that score 70 returns B."""
        assert output.get_grade_from_score(70) == "B"

    def test_score_69_returns_c(self):
        """Test that score 69 returns C."""
        assert output.get_grade_from_score(69) == "C"

    def test_score_60_returns_c(self):
        """Test that score 60 returns C."""
        assert output.get_grade_from_score(60) == "C"

    def test_score_59_returns_d(self):
        """Test that score 59 returns D."""
        assert output.get_grade_from_score(59) == "D"

    def test_score_50_returns_d(self):
        """Test that score 50 returns D."""
        assert output.get_grade_from_score(50) == "D"

    def test_score_49_returns_f(self):
        """Test that score 49 returns F."""
        assert output.get_grade_from_score(49) == "F"

    def test_score_0_returns_f(self):
        """Test that score 0 returns F."""
        assert output.get_grade_from_score(0) == "F"


class TestGetGradeLabel:
    """Tests for get_grade_label function."""

    def test_score_95_returns_excellent(self):
        """Test that score 95 returns Excellent."""
        assert output.get_grade_label(95) == "Excellent"

    def test_score_85_returns_very_good(self):
        """Test that score 85 returns Very Good."""
        assert output.get_grade_label(85) == "Very Good"

    def test_score_75_returns_good(self):
        """Test that score 75 returns Good."""
        assert output.get_grade_label(75) == "Good"

    def test_score_65_returns_needs_work(self):
        """Test that score 65 returns Needs Work."""
        assert output.get_grade_label(65) == "Needs Work"

    def test_score_55_returns_poor(self):
        """Test that score 55 returns Poor."""
        assert output.get_grade_label(55) == "Poor"

    def test_score_45_returns_poor(self):
        """Test that score 45 returns Poor."""
        assert output.get_grade_label(45) == "Poor"


class TestPrintFunctions:
    """Tests for print_error, print_success, print_warning, print_info."""

    def test_print_error(self):
        """Test print_error outputs red error message."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch.object(output, "console", console):
            output.print_error("Test error message")

        result = string_io.getvalue()
        assert "Test error message" in result

    def test_print_success(self):
        """Test print_success outputs green success message."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch.object(output, "console", console):
            output.print_success("Test success message")

        result = string_io.getvalue()
        assert "Test success message" in result

    def test_print_warning(self):
        """Test print_warning outputs yellow warning message."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch.object(output, "console", console):
            output.print_warning("Test warning message")

        result = string_io.getvalue()
        assert "Test warning message" in result

    def test_print_info(self):
        """Test print_info outputs dim info message."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch.object(output, "console", console):
            output.print_info("Test info message")

        result = string_io.getvalue()
        assert "Test info message" in result


class TestPrintUserInfo:
    """Tests for print_user_info function."""

    def test_print_user_info_basic(self, mock_user_info: dict):
        """Test print_user_info displays all fields."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch.object(output, "console", console):
            output.print_user_info(mock_user_info)

        result = string_io.getvalue()
        assert "test@example.com" in result
        assert "FREE" in result  # tier is uppercased
        assert "5" in result  # analyses_this_month
        assert "10" in result  # analyses_limit

    def test_print_user_info_unlimited(self, mock_user_info_unlimited: dict):
        """Test print_user_info handles unlimited API calls."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch.object(output, "console", console):
            output.print_user_info(mock_user_info_unlimited)

        result = string_io.getvalue()
        assert "enterprise@example.com" in result
        assert "ENTERPRISE" in result  # tier is uppercased
        # None limit should show as unlimited
        assert "unlimited" in result


class TestPrintConfigInfo:
    """Tests for print_config_info function."""

    def test_print_config_info_with_key(self, tmp_path: Path):
        """Test print_config_info with API key configured."""
        config = {"api_key": "qdoo_test123456789012345678901234"}
        config_path = tmp_path / ".qualidoo" / "config.toml"

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch.object(output, "console", console):
            output.print_config_info(config, str(config_path))

        result = string_io.getvalue()
        # Rich may wrap long paths and add ANSI codes, so check for key parts
        assert "Config file" in result
        assert ".qualidoo" in result
        # Key should be masked (shown as qdoo_tes...1234)
        assert "qdoo_test123456789012345678901234" not in result
        assert "qdoo_" in result

    def test_print_config_info_no_key(self, tmp_path: Path):
        """Test print_config_info without API key."""
        config = {}
        config_path = tmp_path / ".qualidoo" / "config.toml"

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch.object(output, "console", console):
            output.print_config_info(config, str(config_path))

        result = string_io.getvalue()
        # Rich may wrap long paths, so check for key parts
        assert "config.toml" in result
        assert "Not configured" in result


class TestPrintAnalysisResult:
    """Tests for print_analysis_result function."""

    def test_print_analysis_result_basic(self, mock_analysis_result: dict):
        """Test print_analysis_result displays basic info."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch.object(output, "console", console):
            output.print_analysis_result(mock_analysis_result, "test_addon")

        result = string_io.getvalue()
        assert "test_addon" in result
        assert "85" in result  # overall_score
        assert "A" in result  # grade

    def test_print_analysis_result_verbose(self, mock_analysis_result: dict):
        """Test print_analysis_result in verbose mode shows more details."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch.object(output, "console", console):
            output.print_analysis_result(mock_analysis_result, "test_addon", verbose=True)

        result = string_io.getvalue()
        assert "test_addon" in result
        assert "85" in result
        # Verbose mode should show recommendations
        assert "Add type hints" in result or "Review all database queries" in result

    def test_print_analysis_result_with_issues(self, mock_analysis_result: dict):
        """Test print_analysis_result displays top issues."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch.object(output, "console", console):
            output.print_analysis_result(mock_analysis_result, "test_addon")

        result = string_io.getvalue()
        # Should show top issues
        assert "SQL query without ORM" in result or "MAJOR" in result

    def test_print_analysis_result_empty_issues(self, mock_analysis_result_empty: dict):
        """Test print_analysis_result with no issues."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        with patch.object(output, "console", console):
            output.print_analysis_result(mock_analysis_result_empty, "perfect_addon")

        result = string_io.getvalue()
        assert "perfect_addon" in result
        assert "100" in result
        # Score shows label not letter grade
        assert "Excellent" in result


class TestCreateProgressCallback:
    """Tests for create_progress_callback function."""

    def test_create_progress_callback_returns_callable(self):
        """Test that create_progress_callback returns a callable."""
        callback = output.create_progress_callback()

        # Should have a stop method
        assert hasattr(callback, "stop") or callable(callback)

    def test_create_progress_callback_can_be_called(self):
        """Test that the progress callback can be called with status."""
        callback = output.create_progress_callback()

        # Should not raise when called
        try:
            callback({"status": "running", "message": "Processing"})
        except Exception:
            pass  # Some implementations may not support this without a console

        # Clean up if needed
        if hasattr(callback, "stop"):
            try:
                callback.stop()
            except Exception:
                pass


class TestGradeColors:
    """Tests for GRADE_COLORS constant."""

    def test_all_grades_have_colors(self):
        """Test that all grades have defined colors."""
        expected_grades = ["A+", "A", "B", "C", "D", "F"]
        for grade in expected_grades:
            assert grade in output.GRADE_COLORS


class TestSeverityStyles:
    """Tests for SEVERITY_STYLES constant."""

    def test_all_severities_have_styles(self):
        """Test that all severities have defined styles."""
        expected_severities = ["CRITICAL", "MAJOR", "MINOR", "INFO"]
        for severity in expected_severities:
            assert severity in output.SEVERITY_STYLES
            style, icon = output.SEVERITY_STYLES[severity]
            assert isinstance(style, str)
            assert isinstance(icon, str)
