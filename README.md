<p align="center">
  <img src="qualidoo.png" alt="Qualidoo Logo" width="400">
</p>

<p align="center">
  <strong>AI-powered quality analysis tool for Odoo addons.</strong>
</p>

## Overview

Qualidoo CLI is a command-line tool for analyzing Odoo addon quality. It uploads your addon to qualidoo.aidooit.com for analysis and displays results directly in your terminal.

Features:
- Analyze addons from any directory
- View results with detailed findings and recommendations
- Save analysis results as JSON for CI/CD integration
- Progress feedback during analysis

## Installation

```bash
pip install qualidoo
```

## Quick Start

```bash
# 1. Configure your API key (get it from https://qualidoo.aidooit.com/settings)
qualidoo login

# 2. Analyze an addon
cd /path/to/my_addon
qualidoo check

# Or specify a path
qualidoo check /path/to/my_addon
```

## Authentication

The CLI requires an API key from your Qualidoo account. API access is available on PRO, TEAM, and BETA tiers.

### Getting an API Key

1. Visit https://qualidoo.aidooit.com/settings
2. Generate a new API key (format: `qdoo_xxxxxxxxxxxx`)
3. Run `qualidoo login` and enter your key

### Configuring the API Key

**Option 1: Interactive login (recommended)**

```bash
qualidoo login
```

You'll be prompted to enter your API key securely.

**Option 2: Command-line flag**

```bash
qualidoo login --key qdoo_your_api_key_here
```

**Option 3: Environment variable**

```bash
export QUALIDOO_API_KEY=qdoo_your_api_key_here
qualidoo check
```

The environment variable takes precedence over the stored configuration.

## Commands

### `qualidoo login`

Configure API key for authentication.

```bash
qualidoo login                    # Interactive prompt
qualidoo login --key qdoo_xxx     # Provide key directly
qualidoo login -k qdoo_xxx        # Short form
```

The API key is validated against the server before saving.

### `qualidoo logout`

Remove stored API key.

```bash
qualidoo logout
```

### `qualidoo whoami`

Show current authentication status and user information.

```bash
qualidoo whoami
```

Displays your email, current tier, and API usage information.

### `qualidoo check`

Analyze an Odoo addon for quality issues.

```bash
qualidoo check [PATH] [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `PATH` | Path to the Odoo addon directory (defaults to current directory) |

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--verbose` | `-v` | Show detailed findings with file paths and suggestions |
| `--save FILE` | `-s` | Save full JSON result to file |
| `--timeout SECONDS` | `-t` | Maximum time to wait for analysis (default: 300) |

**Examples:**

```bash
# Analyze current directory
qualidoo check

# Analyze specific addon
qualidoo check /path/to/sale_extension

# Show detailed output
qualidoo check --verbose

# Save results for CI/CD
qualidoo check --save result.json

# Combine options
qualidoo check /path/to/addon -v -s analysis.json -t 600
```

**Output:**

The check command displays:
- Overall score (0-100) and grade
- Summary of findings by severity (CRITICAL, MAJOR, MINOR, INFO)
- Per-agent scores
- Top recommendations

With `--verbose`, it also shows:
- Each finding with file path and line number
- Detailed descriptions
- Improvement suggestions

### `qualidoo config`

View current configuration.

```bash
qualidoo config
qualidoo config --show    # Explicit show flag
qualidoo config -s        # Short form
```

Displays the configuration file path and current settings (API key is masked).

## Configuration

### Config File Location

Configuration is stored in:

```
~/.qualidoo/config.toml
```

The file is created with secure permissions (readable only by owner).

### Configuration Format

```toml
api_key = "qdoo_your_api_key_here"
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `QUALIDOO_API_KEY` | API key (overrides config file) |
| `QUALIDOO_API_URL` | API URL (default: https://qualidoo.aidooit.com) |

## CI/CD Integration

Use the CLI in your CI/CD pipeline to enforce quality standards:

```yaml
# GitHub Actions example
- name: Install Qualidoo CLI
  run: pip install qualidoo

- name: Analyze addon
  env:
    QUALIDOO_API_KEY: ${{ secrets.QUALIDOO_API_KEY }}
  run: |
    qualidoo check ./my_addon --save result.json
    # Parse result.json and fail if score < threshold
```

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Not logged in" | No API key configured | Run `qualidoo login` |
| "Invalid API key" | Key is incorrect or expired | Get a new key from settings page |
| "Authentication failed" | API key no longer valid | Run `qualidoo login` to reconfigure |
| "Rate limit exceeded" | Too many API requests | Wait and try again later |
| "Not a valid Odoo addon" | Missing `__manifest__.py` | Ensure path points to valid addon |
| "Analysis timed out" | Server processing took too long | Increase `--timeout` or try again |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (authentication, API, or validation failure) |

## Requirements

- Python 3.10+
- PRO, TEAM, or BETA tier for API access (FREE tier has no API access)

## Development

### Setting Up the Development Environment

Clone the repository and install with development dependencies:

```bash
git clone https://github.com/aidooit/qualidoo.git
cd qualidoo-cli
pip install -e ".[dev]"
```

### Running Tests

The test suite uses pytest with respx for HTTP mocking. To run all tests:

```bash
# Run all tests with verbose output
pytest -v

# Run tests for a specific module
pytest tests/test_config.py -v
pytest tests/test_api_client.py -v
pytest tests/test_output.py -v
pytest tests/test_cli.py -v

# Run a specific test class
pytest tests/test_cli.py::TestCheckCommand -v

# Run a specific test
pytest tests/test_config.py::TestValidateApiKeyFormat::test_valid_key -v

# Run tests with coverage (requires pytest-cov)
pytest --cov=qualidoo --cov-report=term-missing
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures (mock data, temp directories)
├── test_config.py       # Configuration module tests (~22 tests)
├── test_api_client.py   # API client tests (~34 tests)
├── test_output.py       # Output formatting tests (~25 tests)
└── test_cli.py          # CLI command tests (~21 tests)
```

### Test Coverage

The test suite covers:

- **Configuration** (`test_config.py`): API key validation, config file operations, environment variable handling
- **API Client** (`test_api_client.py`): HTTP requests, error handling, file uploads, job polling
- **Output** (`test_output.py`): Grade calculations, terminal formatting, progress callbacks
- **CLI** (`test_cli.py`): All commands (login, logout, whoami, check, config) with various scenarios

### Dev Dependencies

| Package | Purpose |
|---------|---------|
| `pytest>=8.0.0` | Test framework |
| `respx>=0.21.0` | HTTP mocking for httpx |

## License

MIT License
