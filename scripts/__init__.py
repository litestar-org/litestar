import subprocess
import sys
from typing import List, Optional, Union


def _run_command(command: List[str], exit_after_run: Optional[bool] = True) -> int:
    completed_process = subprocess.run(command)
    if exit_after_run:
        exit(completed_process.returncode)

    return completed_process.returncode


def _pre_commit(hook_ids: Optional[Union[str, List[str]]] = None) -> None:
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

    exit(overall_return_code)


def test() -> None:
    _run_command(["pytest", *sys.argv[1:]])


def all_checks() -> None:
    _pre_commit()


def lint() -> None:
    _pre_commit("pylint")


def fmt() -> None:
    _pre_commit(["black", "isort", "prettier", "blacken-docs"])


def type_check() -> None:
    _pre_commit("mypy")


def docs() -> None:
    _run_command(["mkdocs", "build"])
