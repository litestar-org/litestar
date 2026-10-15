from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[2]

EXAMPLES = sorted(
    ".".join(path.relative_to(ROOT).with_suffix("").parts)
    for path in (ROOT / "docs" / "examples").rglob("*.py")
    if path.name != "__init__.py"
)

RAISES_ON_PURPOSE = "docs.examples.dependency_injection.dependency_non_optional_not_provided"

BROKEN = {
    "docs.examples.channels.iter_stream": "creates the ChannelsPlugin without channels",
    "docs.examples.channels.put_history": "creates the ChannelsPlugin without channels",
    "docs.examples.security.using_abstract_authentication_middleware": "registers two handlers for GET /",
}

IMPORT_EXAMPLES = """
import importlib
import json
import sys
import warnings

from litestar.exceptions import ImproperlyConfiguredException

failures = {}
for module in sys.argv[2:]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            importlib.import_module(module)
        except BaseException as exc:
            failures[module] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "improperly_configured": isinstance(exc, ImproperlyConfiguredException),
            }
with open(sys.argv[1], "w") as file:
    json.dump(failures, file)
"""


def _import(modules: list[str], output: Path) -> dict[str, dict[str, Any]]:
    subprocess.run(
        [sys.executable, "-c", IMPORT_EXAMPLES, str(output), *modules],
        cwd=ROOT,
        capture_output=True,
        check=True,
        timeout=300,
    )
    failures: dict[str, dict[str, Any]] = json.loads(output.read_text())
    return failures


@pytest.fixture(scope="session")
def import_failures(tmp_path_factory: pytest.TempPathFactory) -> dict[str, dict[str, Any]]:
    output = tmp_path_factory.mktemp("examples") / "failures.json"
    failures = _import(EXAMPLES, output)
    # an example can fail on what an earlier one left behind, such as a table defined
    # twice on shared SQLAlchemy metadata. those are imported again on their own
    retry = [
        module
        for module, failure in failures.items()
        if not failure["improperly_configured"] and failure["type"] not in ("ImportError", "ModuleNotFoundError")
    ]
    for module in retry:
        del failures[module]
        failures.update(_import([module], output))
    return failures


@pytest.mark.parametrize(
    "module",
    [
        pytest.param(module, marks=pytest.mark.xfail(strict=True, reason=BROKEN[module]))
        if module in BROKEN
        else module
        for module in EXAMPLES
        if module != RAISES_ON_PURPOSE
    ],
)
def test_example_builds(module: str, import_failures: dict[str, dict[str, Any]]) -> None:
    failure = import_failures.get(module)
    if failure is None:
        return
    if not failure["improperly_configured"]:
        pytest.skip(f"{failure['type']}: {failure['message']}")
    pytest.fail(failure["message"], pytrace=False)


def test_example_raising_on_purpose_raises(import_failures: dict[str, dict[str, Any]]) -> None:
    assert import_failures[RAISES_ON_PURPOSE]["improperly_configured"]
