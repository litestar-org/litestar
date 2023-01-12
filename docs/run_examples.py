import importlib
import logging
import multiprocessing
import os
import re
import secrets
import shlex
import socket
import subprocess
import sys
import time
from contextlib import contextmanager, redirect_stderr
from pathlib import Path
from typing import Generator, List, TYPE_CHECKING

import httpx
import uvicorn
from docutils.nodes import Node, admonition, literal_block
from sphinx.addnodes import highlightlang
from sphinx.application import Sphinx
from sphinx.directives.code import LiteralInclude

from starlite import Starlite

if TYPE_CHECKING:
    pass

RGX_RUN = re.compile(r"# +?run:(.*)")
RGX_SNIPPET = re.compile(r'--8<-- "(.*)"')

AVAILABLE_PORTS = list(range(9000, 9999))


logger = logging.getLogger("sphinx")


def _load_app_from_path(path: Path) -> Starlite:
    module = importlib.import_module(str(path.with_suffix("")).replace("/", "."))
    for obj in module.__dict__.values():
        if isinstance(obj, Starlite):
            return obj
    raise RuntimeError(f"No Starlite app found in {path}")


@contextmanager
def run_app(path: Path) -> Generator[int, None, None]:
    """Run an example app from a python file.

    The first ``Starlite`` instance found in the file will be used as target to run.
    """
    while AVAILABLE_PORTS:
        port = AVAILABLE_PORTS.pop()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                break
    else:
        raise RuntimeError("Could not find an open port")

    app = _load_app_from_path(path)

    def run() -> None:
        with redirect_stderr(Path(os.devnull).open()):
            uvicorn.run(app, port=port, access_log=False)

    proc = multiprocessing.Process(target=run)
    proc.start()
    for _ in range(50):
        try:
            httpx.get(f"http://127.0.0.1:{port}", timeout=0.1)
        except httpx.TransportError:
            time.sleep(0.1)
        else:
            break
    try:
        yield port
    finally:
        proc.kill()
    AVAILABLE_PORTS.append(port)


def extract_run_args(content: str) -> tuple[str, list[List[str]]]:
    """Extract run args from a python file.

    Return the file content stripped of the run comments and a list of argument lists
    """
    new_lines = []
    run_configs = []
    for line in content.splitlines():
        if run_stmt_match := RGX_RUN.match(line):
            run_stmt = run_stmt_match.group(1).lstrip()
            run_configs.append(shlex.split(run_stmt))
        else:
            new_lines.append(line)
    return "\n".join(new_lines), run_configs


def exec_examples(app_file: Path, run_configs: List[List[str]]) -> str:
    """Start a server with the example application, run the specified requests against it
    and return their results
    """

    results = []

    with run_app(app_file) as port:
        for run_args in run_configs:
            url_path, *options = run_args
            args = ["curl", "-s", f"http://127.0.0.1:{port}{url_path}", *options]
            clean_args = ["curl", f"http://127.0.0.1:8000{url_path}", *options]

            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
            )
            stdout = proc.stdout.splitlines()
            if not stdout:
                logger.error(f"Example: {app_file}:{args} yielded no results")
                continue

            result = "\n".join(line for line in ("> " + (" ".join(clean_args)), *stdout))
            results.append(result)

    return "\n".join(results)


TMP_EXAMPLES_PATH = Path("_tmp_docs_examples")


class AutoRunInclude(LiteralInclude):
    def run(self) -> list[Node]:
        language = self.options.get("language")
        if language != "python" or self.options.get("no-run"):
            return super().run()

        rel_filename, filename = self.env.relfn2path(self.arguments[0])
        file = Path(filename)
        content = file.read_text()
        clean_content, run_args = extract_run_args(content)

        if not run_args:
            return super().run()

        tmp_file = TMP_EXAMPLES_PATH / secrets.token_hex()
        self.arguments[0] = str(Path("..") / tmp_file)
        tmp_file.write_text(clean_content)

        nodes = super().run()

        result = exec_examples(file.relative_to(Path.cwd()), run_args)

        nodes.append(
            highlightlang("", literal_block("", result), lang="shell", force=False, linenothreshold=sys.maxsize)
        )
        nodes.append(admonition("", literal_block("", result)))

        return nodes


def setup(app: Sphinx) -> dict[str, bool]:
    app.add_directive("literalinclude", AutoRunInclude, override=True)
    TMP_EXAMPLES_PATH.mkdir(exist_ok=True)

    return {"parallel_read_safe": True, "parallel_write_safe": True}
