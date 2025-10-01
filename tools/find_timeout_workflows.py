#!/usr/bin/env python3
"""
Script to identify all workflow runs that failed due to timeouts.

This script can use either:
1. GitHub CLI (gh) - requires authentication
2. GitHub API directly via requests library

Usage:
    python tools/find_timeout_workflows.py [--workflow WORKFLOW] [--limit LIMIT] [--use-api]

Arguments:
    --workflow    Workflow file name (default: ci.yml)
    --limit       Number of workflow runs to analyze (default: 50)
    --use-api     Use GitHub API directly instead of gh CLI
    --token       GitHub personal access token (can also use GITHUB_TOKEN env var)

Requirements:
    - For gh CLI: GitHub CLI must be installed and authenticated
    - For API: requests library and GitHub token
    - Repository must be litestar-org/litestar

Known timeout examples from comments in tests/unit/test_channels/conftest.py:
    - https://github.com/litestar-org/litestar/actions/runs/5629765460/job/15255093668
    - https://github.com/litestar-org/litestar/actions/runs/5647890525/job/15298927200
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


TIMEOUT_INDICATORS = [
    "timeout",
    "timed out",
    "Operation cancelled",
    "The runner has received a shutdown signal",
    "exceeded the timeout",
    "SIGTERM",
    "The job running on runner",
    "has exceeded the maximum execution time",
    "ERROR: Job failed: execution took longer than",
    "pytest-timeout",
    "Timeout:",
]

GITHUB_API_BASE = "https://api.github.com"
REPO_OWNER = "litestar-org"
REPO_NAME = "litestar"


class GitHubAPIClient:
    """Client for interacting with GitHub API."""
    
    def __init__(self, token: Optional[str] = None):
        if not HAS_REQUESTS:
            raise ImportError("requests library is required for API mode. Install it with: pip install requests")
        
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token is required. Provide via --token or GITHUB_TOKEN env var")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    
    def get_workflows(self) -> list[dict]:
        """Get all workflows in the repository."""
        url = f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get("workflows", [])
    
    def get_workflow_runs(self, workflow_id: str, per_page: int = 100) -> list[dict]:
        """Get workflow runs for a specific workflow."""
        url = f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{workflow_id}/runs"
        params = {"per_page": per_page}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json().get("workflow_runs", [])
    
    def get_workflow_run_jobs(self, run_id: int) -> list[dict]:
        """Get all jobs for a specific workflow run."""
        url = f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{run_id}/jobs"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get("jobs", [])
    
    def get_job_logs(self, job_id: int) -> str:
        """Get logs for a specific job."""
        url = f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/jobs/{job_id}/logs"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.text
        return ""


def run_gh_command(cmd: list[str]) -> Any:
    """Run a GitHub CLI command and return parsed JSON output."""
    try:
        result = subprocess.run(
            ["gh"] + cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout) if result.stdout.strip() else None
    except subprocess.CalledProcessError as e:
        print(f"Error running gh command: {e}", file=sys.stderr)
        print(f"stderr: {e.stderr}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return None


def get_workflow_runs(workflow_name: str, limit: int = 100) -> list[dict]:
    """Get workflow runs for a specific workflow using gh CLI."""
    cmd = [
        "run",
        "list",
        "--workflow", workflow_name,
        "--json", "databaseId,displayTitle,conclusion,status,createdAt,updatedAt,url,headBranch",
        "--limit", str(limit),
    ]
    runs = run_gh_command(cmd)
    return runs if runs else []


def get_workflow_run_jobs(run_id: int) -> list[dict]:
    """Get all jobs for a specific workflow run using gh CLI."""
    cmd = [
        "run",
        "view",
        str(run_id),
        "--json", "jobs",
    ]
    result = run_gh_command(cmd)
    return result.get("jobs", []) if result else []


def get_job_logs(run_id: int, job_id: int) -> str:
    """Get logs for a specific job using gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "run", "view", "--job", str(job_id), "--log"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def check_for_timeout_in_logs(logs: str) -> tuple[bool, list[str]]:
    """Check if logs contain timeout indicators.
    
    Returns:
        Tuple of (has_timeout, list of matched indicators)
    """
    logs_lower = logs.lower()
    matched_indicators = []
    for indicator in TIMEOUT_INDICATORS:
        if indicator.lower() in logs_lower:
            matched_indicators.append(indicator)
    return len(matched_indicators) > 0, matched_indicators


def analyze_workflow_runs_with_api(
    workflow_name: str, 
    limit: int, 
    token: Optional[str] = None
) -> list[dict]:
    """Analyze workflow runs using GitHub API directly."""
    print(f"Using GitHub API to analyze workflow runs for '{workflow_name}'...")
    print(f"Fetching up to {limit} workflow runs...\n")
    
    try:
        client = GitHubAPIClient(token)
    except (ImportError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return []
    
    # Find the workflow by name
    workflows = client.get_workflows()
    workflow = None
    for wf in workflows:
        if wf.get("path", "").endswith(workflow_name):
            workflow = wf
            break
    
    if not workflow:
        print(f"Error: Workflow '{workflow_name}' not found", file=sys.stderr)
        return []
    
    workflow_id = workflow["id"]
    print(f"Found workflow: {workflow['name']} (ID: {workflow_id})\n")
    
    runs = client.get_workflow_runs(workflow_id, per_page=limit)
    
    if not runs:
        print("No workflow runs found.")
        return []
    
    timeout_failures = []
    
    for run in runs:
        run_id = run.get("id")
        conclusion = run.get("conclusion")
        status = run.get("status")
        
        # Only check completed runs that failed or were cancelled
        if status == "completed" and conclusion in ["failure", "cancelled"]:
            print(f"Checking run {run_id}: {run.get('display_title')} ({conclusion})...")
            
            jobs = client.get_workflow_run_jobs(run_id)
            
            for job in jobs:
                job_id = job.get("id")
                job_name = job.get("name")
                job_conclusion = job.get("conclusion")
                
                if job_conclusion in ["failure", "cancelled"]:
                    print(f"  - Checking job '{job_name}' (ID: {job_id})...")
                    logs = client.get_job_logs(job_id)
                    
                    has_timeout, matched_indicators = check_for_timeout_in_logs(logs)
                    
                    if has_timeout:
                        timeout_failures.append({
                            "run_id": run_id,
                            "run_url": run.get("html_url"),
                            "run_title": run.get("display_title"),
                            "run_conclusion": conclusion,
                            "run_date": run.get("created_at"),
                            "branch": run.get("head_branch"),
                            "job_id": job_id,
                            "job_name": job_name,
                            "job_conclusion": job_conclusion,
                            "timeout_indicators": matched_indicators,
                        })
                        print(f"    ✗ TIMEOUT DETECTED in job '{job_name}'")
                        print(f"      Indicators: {', '.join(matched_indicators)}")
    
    return timeout_failures


def analyze_workflow_runs(workflow_name: str = "ci.yml", limit: int = 50):
    """Analyze workflow runs for timeout failures using gh CLI."""
    print(f"Using gh CLI to analyze workflow runs for '{workflow_name}'...")
    print(f"Fetching up to {limit} workflow runs...\n")
    
    runs = get_workflow_runs(workflow_name, limit)
    
    if not runs:
        print("No workflow runs found.")
        return []
    
    timeout_failures = []
    
    for run in runs:
        run_id = run.get("databaseId")
        conclusion = run.get("conclusion")
        status = run.get("status")
        
        # Only check completed runs that failed or were cancelled
        if status == "completed" and conclusion in ["failure", "cancelled"]:
            print(f"Checking run {run_id}: {run.get('displayTitle')} ({conclusion})...")
            
            jobs = get_workflow_run_jobs(run_id)
            
            for job in jobs:
                job_id = job.get("databaseId")
                job_name = job.get("name")
                job_conclusion = job.get("conclusion")
                
                if job_conclusion in ["failure", "cancelled"]:
                    print(f"  - Checking job '{job_name}' (ID: {job_id})...")
                    logs = get_job_logs(run_id, job_id)
                    
                    has_timeout, matched_indicators = check_for_timeout_in_logs(logs)
                    
                    if has_timeout:
                        timeout_failures.append({
                            "run_id": run_id,
                            "run_url": run.get("url"),
                            "run_title": run.get("displayTitle"),
                            "run_conclusion": conclusion,
                            "run_date": run.get("createdAt"),
                            "branch": run.get("headBranch"),
                            "job_id": job_id,
                            "job_name": job_name,
                            "job_conclusion": job_conclusion,
                            "timeout_indicators": matched_indicators,
                        })
                        print(f"    ✗ TIMEOUT DETECTED in job '{job_name}'")
                        print(f"      Indicators: {', '.join(matched_indicators)}")
    
    return timeout_failures


def print_report(timeout_failures: list[dict]):
    """Print the timeout failures report."""
    print("\n" + "=" * 80)
    print("TIMEOUT FAILURES REPORT")
    print("=" * 80 + "\n")
    
    if timeout_failures:
        print(f"Found {len(timeout_failures)} job(s) with timeout failures:\n")
        
        for i, failure in enumerate(timeout_failures, 1):
            print(f"{i}. Run ID: {failure['run_id']}")
            print(f"   Title: {failure['run_title']}")
            print(f"   URL: {failure['run_url']}")
            print(f"   Branch: {failure['branch']}")
            print(f"   Date: {failure['run_date']}")
            print(f"   Conclusion: {failure['run_conclusion']}")
            print(f"   Job: {failure['job_name']} (ID: {failure['job_id']})")
            print(f"   Job Conclusion: {failure['job_conclusion']}")
            print(f"   Timeout Indicators: {', '.join(failure['timeout_indicators'])}")
            print()
    else:
        print("No timeout failures detected in the analyzed workflow runs.")
    
    print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Identify GitHub Actions workflow runs that failed due to timeouts"
    )
    parser.add_argument(
        "--workflow",
        default="ci.yml",
        help="Workflow file name to analyze (default: ci.yml)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Number of workflow runs to analyze (default: 50)",
    )
    parser.add_argument(
        "--use-api",
        action="store_true",
        help="Use GitHub API directly instead of gh CLI",
    )
    parser.add_argument(
        "--token",
        help="GitHub personal access token (can also use GITHUB_TOKEN env var)",
    )
    
    args = parser.parse_args()
    
    timeout_failures = []
    
    if args.use_api:
        timeout_failures = analyze_workflow_runs_with_api(
            workflow_name=args.workflow,
            limit=args.limit,
            token=args.token,
        )
    else:
        # Check if gh is installed
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: GitHub CLI (gh) is not installed or not in PATH.", file=sys.stderr)
            print("Please install it from: https://cli.github.com/", file=sys.stderr)
            print("Or use --use-api flag to use GitHub API directly.", file=sys.stderr)
            sys.exit(1)
        
        # Run the analysis
        timeout_failures = analyze_workflow_runs(workflow_name=args.workflow, limit=args.limit)
    
    # Print report
    print_report(timeout_failures)


if __name__ == "__main__":
    main()
