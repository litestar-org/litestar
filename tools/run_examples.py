import re
import secrets
import shlex
import shutil
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Generator, List, Tuple

import httpx

if TYPE_CHECKING:
    from mkdocs.config.base import Config as MkDocsConfig
    from mkdocs.structure.files import File, Files

RGX_RUN = re.compile(r"# +?run:(.*)")
RGX_SNIPPET = re.compile(r'--8<-- "(.*)"')
RGX_CODE_BLOCK = re.compile(r"```py[\w\W]+?```")


AVAILABLE_PORTS = list(range(9000, 9999))


@dataclass(frozen=True)
class RunConfig:
    tmp_docs_file: Path
    example_file: Path
    args: List[List[str]]
    code_block: str
    updated_code_block: str


def indent(string: str, level: int = 4) -> str:
    return "\n".join((" " * level) + line for line in string.splitlines())


@contextmanager
def run_app(path: Path) -> Generator[int, None, None]:
    while AVAILABLE_PORTS:
        port = AVAILABLE_PORTS.pop()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                break
    else:
        raise RuntimeError("Could not find an open port")

    proc = subprocess.Popen(
        ["uvicorn", str(path.with_suffix("")).replace("/", ".") + ":app", "--no-access-log", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
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
            raise RuntimeError("Multiple snippet sources found")

        snippet_source = snippet_sources[0]
        if not snippet_source.endswith("py"):
            continue

        example_file = Path(snippet_source)
        if not example_file.exists():
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
    results = []

    with run_app(config.example_file) as port:
        for run_args in config.args:
            url_path, *options = run_args
            args = ["curl", f"http://127.0.0.1:{port}{url_path}", *options]
            clean_args = ["curl", f"http://127.0.0.1:8000{url_path}", *options]

            proc = subprocess.run(args, capture_output=True, text=True)
            stdout = proc.stdout.splitlines()
            if not stdout:
                raise RuntimeError(f"Example: {config.example_file}:{args} yielded no results")

            result = "\n".join(line for line in ("> " + (" ".join(clean_args)), *stdout))
            results.append(result)

    replacement_block = config.updated_code_block
    replacement_block += "\n!!! example\n"
    replacement_block += "\n".join(indent(f"```shell\n{r}\n```") for r in results)
    return config, replacement_block


def on_files(files: "Files", config: "MkDocsConfig") -> None:
    tmp_examples_path = Path(".tmp_examples")
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


def on_post_build(config: "MkDocsConfig") -> None:
    tmp_examples_path = Path(".tmp_examples")
    if tmp_examples_path.exists():
        shutil.rmtree(tmp_examples_path)
