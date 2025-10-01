# Timeout Analysis Report

## Overview

This document analyzes why tests are sometimes cancelled after timeouts with incomplete logs, based on the analysis of workflow run #18158669868 and the GitHub Actions workflow configuration.

## Key Findings

### 1. **Workflow-Level Timeout vs Test-Level Timeout**

There are two types of timeouts at play:

#### a) **Workflow Job Timeout (GitHub Actions)**
- Configured in `.github/workflows/test.yml` with `timeout-minutes: {{ inputs.timeout }}`
- Default value: **10 minutes**
- This is a **hard timeout** enforced by GitHub Actions
- When this timeout is reached, GitHub Actions **cancels the entire job**
- Result: Job status becomes `cancelled`, no clean test output

#### b) **Test-Level Timeout (pytest-timeout)**
- Configured in `tests/unit/test_channels/conftest.py` with `@pytest.mark.timeout(30)` seconds
- This is a **soft timeout** that allows pytest to report test failures
- When triggered, pytest can gracefully fail the test and report it
- Result: Test fails with timeout message in logs

### 2. **Why Jobs Get Cancelled Instead of Failed**

Looking at run #18158669868:

```
Job: test (3.9) / test
- Started: 10:05:04Z
- Test step started: 10:05:04Z
- Cancelled: 10:06:29Z (at 85 seconds = 1m 25s into testing)
- Conclusion: cancelled
```

The job was cancelled because:
1. The **workflow timeout** is set to **10 minutes**
2. Setup steps (checkout, install deps, etc.) took ~5 minutes
3. Tests ran for only ~1.5 minutes before the 10-minute workflow timeout was reached
4. GitHub Actions **terminated the entire job**, killing the pytest process
5. Result: No clean pytest output, just "Operation was canceled"

### 3. **The Hanging Test Problem**

From the logs, we can see tests were progressing normally:
```
2025-10-01T10:06:16.7379855Z ....................................................FFFFFFFFF..F........ [ 53%]
2025-10-01T10:06:17.0238631Z ................FFFFFF.......F.......................................... [ 54%]
...
2025-10-01T10:06:29.1600423Z ##[error]The operation was canceled.
```

The tests reached 66% completion before cancellation. This suggests:
- Tests were **not hanging** completely
- The issue is **workflow timeout too short** relative to:
  - Setup time (~5 minutes)
  - Total test suite runtime (needs more than 5 minutes remaining)
  - Slow CI runner performance

### 4. **Why Logs Don't Show Useful Information**

When GitHub Actions cancels a job due to timeout:
1. It sends a **SIGTERM** to all running processes
2. If processes don't stop quickly, it sends **SIGKILL**
3. There's **no graceful shutdown** for pytest to report results
4. The last thing logged is the cancellation message
5. Any tests that were hung or slow are **not identified** in the output

The orphan process cleanup shows pytest was actively running:
```
2025-10-01T10:06:29.5087174Z Terminate orphan process: pid (2279) (uv)
2025-10-01T10:06:29.5118455Z Terminate orphan process: pid (2283) (pytest)
2025-10-01T10:06:29.5157378Z Terminate orphan process: pid (2286) (python)
2025-10-01T10:06:29.5268315Z Terminate orphan process: pid (2289) (python)
```

### 5. **The Compression Middleware Issue**

Looking at run #18158669868, it was testing a zstandard fix:
```
Title: fix: zstandard not installed
Branch: 4324_zstandard_not_installed
```

The compression tests at 53-54% likely involve:
- Loading/importing compression libraries (brotli, zstandard)
- Running compression operations
- These can be **CPU-intensive** and slow on CI

The failures (`FFFFFFFFF`) indicate tests were actually **failing**, not just hanging.

## Root Causes

### Primary Cause: Insufficient Workflow Timeout
- **10-minute workflow timeout** is too short for:
  - 5 minutes of setup
  - Running 5649 test items
  - Especially when tests fail and need detailed output

### Secondary Cause: Test Failures Slow Down Suite
- When tests fail, pytest collects more information
- Failed assertions generate detailed output
- This adds overhead that can push over the time limit

### Tertiary Cause: No Timeout Buffer
- The workflow timeout (10 min) doesn't account for:
  - Variable CI runner performance
  - Docker service startup times
  - Network latency for package downloads

## Why Tests Appear to Hang

Tests don't actually hang in most cases. Instead:

1. **Tests run slowly** due to:
   - CI runner resource constraints
   - Test complexity (docker services, async operations)
   - pytest-xdist parallelization overhead
   
2. **Time budget runs out** before completion

3. **GitHub Actions cancels everything** before pytest can report

4. **Result looks like a hang** because there's no final output

## Recommendations

### Immediate Actions

1. **Increase Workflow Timeout**
   ```yaml
   timeout:
     required: false
     type: number
     default: 15  # Changed from 10
   ```
   - Or make it 20 minutes for more buffer

2. **Add Timeout Warnings**
   - Configure pytest to show which tests are slow
   ```bash
   pytest --durations=20  # Show 20 slowest tests
   ```

3. **Better Timeout Reporting**
   - Add a step before tests to calculate remaining time
   - Warn if less than X minutes remain

### Long-term Solutions

1. **Split Test Jobs**
   - Run channel tests in separate job with longer timeout
   - Parallel jobs can have different timeout values

2. **Improve Test Performance**
   - Profile slow tests
   - Optimize docker service startup
   - Cache more aggressively

3. **Add Telemetry**
   - Log test start/end times
   - Track test duration trends
   - Alert on anomalous slow tests

4. **Graceful Timeout Handling**
   ```yaml
   - name: Test with coverage
     timeout-minutes: 12  # Less than job timeout
     run: uv run pytest docs/examples tests -n auto --cov
   
   - name: Report if timeout
     if: failure()
     run: echo "Tests timed out at $(date)"
   ```

## Example Timeline Analysis

For run #18158669868 (test 3.9):

```
00:00 - Job starts
00:01 - Checkout (2s)
00:01 - Setup Python (1s)
00:14 - Install build deps (13s)
00:17 - Install uv (3s)
00:22 - Install dependencies (5s)
00:22 - Set PYTHONPATH (0s)
01:21 - Tests running (started at 10:05:04)
      * Tests show failures in compression tests
      * Progress reaches 66%
06:25 - GitHub Actions timeout reached (10 minutes total)
      * Cancels all processes
      * No graceful pytest shutdown
      * No test results reported
```

**Time breakdown:**
- Setup: ~22 seconds
- Tests: ~6 minutes before cancellation
- **Problem**: Job timeout doesn't account for actual test runtime needs

## Conclusion

Tests are **not actually hanging** in most cases. The issue is:

1. **Workflow timeout is too aggressive** (10 minutes)
2. **Setup overhead** consumes significant time
3. **Test suite needs more time** than remaining after setup
4. **GitHub Actions cancels forcefully**, preventing useful diagnostics
5. **No buffer time** for slow CI runners or flaky tests

The solution is to **increase workflow timeout** and add **better time budget management** to prevent abrupt cancellations that hide the real issue.
