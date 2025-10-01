# Tools Directory

This directory contains utility scripts for the Litestar project.

## find_timeout_workflows.py

A script to identify GitHub Actions workflow runs that failed due to timeouts.

### Purpose

This tool helps identify workflow runs where tests or jobs failed because they exceeded their timeout limits. This is particularly useful for diagnosing intermittent test failures related to timeouts, such as those mentioned in `tests/unit/test_channels/conftest.py`.

### Requirements

The script supports two modes:

1. **GitHub CLI mode** (default):
   - Requires `gh` CLI installed and authenticated
   - Install from: https://cli.github.com/
   - Authenticate with: `gh auth login`

2. **API mode** (`--use-api` flag):
   - Requires `requests` library: `pip install requests`
   - Requires GitHub personal access token with `repo` scope
   - Set token via `--token` flag or `GITHUB_TOKEN` environment variable

### Usage

```bash
# Using GitHub CLI (default)
python tools/find_timeout_workflows.py

# Analyze specific workflow with custom limit
python tools/find_timeout_workflows.py --workflow ci.yml --limit 100

# Using GitHub API directly
python tools/find_timeout_workflows.py --use-api --token YOUR_GITHUB_TOKEN

# Using GitHub API with environment variable
export GITHUB_TOKEN=YOUR_GITHUB_TOKEN
python tools/find_timeout_workflows.py --use-api
```

### Options

- `--workflow WORKFLOW`: Workflow file name to analyze (default: `ci.yml`)
- `--limit LIMIT`: Number of workflow runs to analyze (default: 50)
- `--use-api`: Use GitHub API directly instead of gh CLI
- `--token TOKEN`: GitHub personal access token (can also use `GITHUB_TOKEN` env var)

### Output

The script produces a detailed report showing:
- Run ID and URL
- Run title and date
- Branch name
- Job name and ID that timed out
- Specific timeout indicators found in the logs

### Example Output

```
Analyzing workflow runs for 'ci.yml'...
Fetching up to 50 workflow runs...

Checking run 12345678: Tests And Linting (failure)...
  - Checking job 'test (3.9)' (ID: 98765432)...
    ✗ TIMEOUT DETECTED in job 'test (3.9)'
      Indicators: timeout, exceeded the timeout

================================================================================
TIMEOUT FAILURES REPORT
================================================================================

Found 1 job(s) with timeout failures:

1. Run ID: 12345678
   Title: Tests And Linting
   URL: https://github.com/litestar-org/litestar/actions/runs/12345678
   Branch: main
   Date: 2024-01-15T10:30:00Z
   Conclusion: failure
   Job: test (3.9) (ID: 98765432)
   Job Conclusion: failure
   Timeout Indicators: timeout, exceeded the timeout

================================================================================
```

### Known Timeout Examples

The script was created to help identify timeout issues like those documented in:
- https://github.com/litestar-org/litestar/actions/runs/5629765460/job/15255093668
- https://github.com/litestar-org/litestar/actions/runs/5647890525/job/15298927200

These examples were added as interim measures in `tests/unit/test_channels/conftest.py` with a 30-second timeout marker.
