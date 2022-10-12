import subprocess
import sys
from typing import List, Optional, Union


def _run_command(command: List[str], exit_after_run: Optional[bool] = True) -> int:
    """Run a CLI command.

    Args:
        command: the CLI command to run
        exit_after_run: exit after the command finished running

    Returns:
        The command's return code
    """
    completed_process = subprocess.run(command, check=False)
    if exit_after_run:
        sys.exit(completed_process.returncode)

    return completed_process.returncode


def _pre_commit(hook_ids: Optional[Union[str, List[str]]] = None) -> None:
    """Run one or more pre-commit hooks.

    Args:
        hook_ids: one or more hooks to run. It's an optional parameter, `None` means run all hooks

    Returns:
        None
    """
    files = ["--files", *sys.argv[1:]] if len(sys.argv) > 1 else ["--all-files"]

    if not hook_ids:
        _run_command(["pre-commit", "run", "--color=always", *files])
        return

    if isinstance(hook_ids, str):
        hook_ids = [hook_ids]

    overall_return_code = 0
    for hook_id in hook_ids:
        cur_return_code = _run_command(["pre-commit", "run", "--color=always", hook_id, *files], exit_after_run=False)
        overall_return_code = overall_return_code or cur_return_code

    sys.exit(overall_return_code)


def test() -> None:
    """Run tests.

    Args:
        argv: a directory or file to run on

    Returns:
        None
    """

    _run_command(["pytest", *sys.argv[1:]])


def all_checks() -> None:
    """Run all pre-commit checks.

    Args:
        argv: a directory or files to run on

    Returns:
        None
    """

    _pre_commit()


def lint() -> None:
    """Run pylint from pre-commit.

    Args:
        argv: a directory or files to run on

    Returns:
        None
    """

    _pre_commit("pylint")


def fmt() -> None:
    """Run black, isort, prettier, blacken-docs and docformatter from pre-
    commit.

    Args:
        argv: a directory or files to run on

    Returns:
        None
    """

    _pre_commit(["black", "isort", "prettier", "blacken-docs", "docformatter"])


def type_check() -> None:
    """Run mypy from pre-commit.

    Args:
        argv: a directory or files to run on

    Returns:
        None
    """

    _pre_commit("mypy")


def docs() -> None:
    """Build docs."""

    _run_command(["mkdocs", "build"])
