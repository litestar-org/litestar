import importlib
import logging
import multiprocessing
import os
import re
import secrets
import shlex
import shutil
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, redirect_stderr
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Generator, List, Tuple

import httpx
import uvicorn

from starlite import Starlite

if TYPE_CHECKING:
    from mkdocs.config.base import Config as MkDocsConfig
    from mkdocs.structure.files import File, Files

RGX_RUN = re.compile(r"# +?run:(.*)")
RGX_SNIPPET = re.compile(r'--8<-- "(.*)"')
RGX_CODE_BLOCK = re.compile(r" *```py[\w\W]+?```")


AVAILABLE_PORTS = list(range(9000, 9999))


logger = logging.getLogger("mkdocs")


@dataclass(frozen=True)
class RunConfig:
    tmp_docs_file: Path
    example_file: Path
    args: List[List[str]]
    code_block: str
    updated_code_block: str


def indent(string: str, indent_char: str = " ", level: int = 4) -> str:
    return "\n".join((indent_char * level) + line for line in string.splitlines())


def get_indentation(text: str) -> Tuple[str, int]:
    if match := re.match("^[ \t]+", text):
        indentation = match.group()
        indent_char = indentation[0]
        return indent_char, len(indentation)
    return " ", 0


def _load_app_from_path(path: Path) -> Starlite:
    module = importlib.import_module(str(path.with_suffix("")).replace("/", "."))
    for obj in module.__dict__.values():
        if isinstance(obj, Starlite):
            return obj
    raise RuntimeError(f"No Starlite app found in {path}")


@contextmanager
def run_app(path: Path) -> Generator[int, None, None]:
    """Run an example app from a python file.

    The first `Starlite` instance found in the file will be used as target to run.
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


def extract_run_args(content: str) -> Tuple[str, List[List[str]]]:
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


def extract_from_docs_file(file: "File", tmp_path: Path) -> List[RunConfig]:
    """Extract `RunConfig`s from a documentation file.

    If configurations are found, set up a temporary documentation file and replace the `File`s source with it.
    """
    tmp_docs_file = tmp_path / secrets.token_hex()
    content = Path(file.abs_src_path).read_text()

    code_blocks = RGX_CODE_BLOCK.findall(content)
    configs = []

    if not code_blocks:
        return []

    for code_block in code_blocks:
        snippet_sources = RGX_SNIPPET.findall(code_block)
        if not snippet_sources:
            continue
        if len(snippet_sources) > 1:
            logger.warning(f"In {file.src_path}: Multiple snippets found in code block. Skipping")
            continue

        snippet_source = snippet_sources[0]
        if not snippet_source.endswith("py"):
            continue

        example_file = Path(snippet_source)
        if not example_file.exists():
            logger.warning(f"In {file.src_path}: Example file not found: {example_file}")
            continue
        example_content = example_file.read_text()
        updated_example_content, run_args = extract_run_args(example_content)
        if not run_args:
            continue

        tmp_example_file = tmp_path / secrets.token_hex()
        tmp_example_file.write_text(updated_example_content)
        updated_code_block = code_block.replace(snippet_source, str(tmp_example_file.absolute()))

        configs.append(
            RunConfig(
                args=run_args,
                tmp_docs_file=tmp_docs_file,
                example_file=example_file,
                code_block=code_block,
                updated_code_block=updated_code_block,
            )
        )

    if configs:
        file.abs_src_path = str(tmp_docs_file.absolute())
        tmp_docs_file.write_text(content)

    return configs


def exec_from_config(config: RunConfig) -> Tuple[RunConfig, str]:
    """Execute a `RunConfig`.

    Start a server with the example application, run the specified requests against it and write and output back into
    the temporary documentation file
    """

    results = []

    with run_app(config.example_file) as port:
        for run_args in config.args:
            url_path, *options = run_args
            args = ["curl", f"http://127.0.0.1:{port}{url_path}", *options]
            clean_args = ["curl", f"http://127.0.0.1:8000{url_path}", *options]

            proc = subprocess.run(args, capture_output=True, text=True)
            stdout = proc.stdout.splitlines()
            if not stdout:
                logger.error(f"Example: {config.example_file}:{args} yielded no results")
                continue

            result = "\n".join(line for line in ("> " + (" ".join(clean_args)), *stdout))
            results.append(result)

    indent_char, indent_level = get_indentation(config.updated_code_block)
    replacement_block = '\n!!! example "Run it"\n'
    replacement_block += indent("\n".join(f"```shell\n{r}\n```" for r in results), indent_char, 4)
    if indent_level:
        replacement_block = indent(replacement_block, indent_char, indent_level)

    return config, config.updated_code_block + "\n" + replacement_block


def on_files(files: "Files", config: "MkDocsConfig") -> None:
    """Extract runnable examples from code snippets, run them concurrently, store the results in temporary files and
    modify the corresponding `File`.
    """
    tmp_examples_path = Path(".tmp_docs_examples")
    if tmp_examples_path.exists():
        shutil.rmtree(tmp_examples_path)
    tmp_examples_path.mkdir(exist_ok=True)

    configs = []
    for file in files:
        if not file.is_documentation_page():
            continue
        configs.extend(extract_from_docs_file(file, tmp_examples_path))

    transformations: Dict[Path, Dict[str, str]] = {}

    with ThreadPoolExecutor() as executor:
        for config, result_block in executor.map(exec_from_config, configs):
            transformations.setdefault(config.tmp_docs_file, {})
            transformations[config.tmp_docs_file][config.code_block] = result_block

    for tmp_docs_file, replacements in transformations.items():
        content = tmp_docs_file.read_text()
        for code_block, updated_code_block in replacements.items():
            content = content.replace(code_block, updated_code_block)
        tmp_docs_file.write_text(content)


def _cleanup_temp_files() -> None:
    """Cleanup temporary files."""
    tmp_examples_path = Path(".tmp_docs_examples")
    if tmp_examples_path.exists():
        shutil.rmtree(tmp_examples_path)


def on_post_build(config: "MkDocsConfig") -> None:
    _cleanup_temp_files()


def on_build_error(error: Exception) -> None:
    _cleanup_temp_files()


on_shutdown = _cleanup_temp_files
