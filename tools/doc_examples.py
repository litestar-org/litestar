import re
from argparse import ArgumentParser, Namespace
from pathlib import Path

CODE_BLOCK_RE = re.compile(r".*```py[\w\W]+?```")
CODE_BLOCK_CODE = re.compile(r".*```py(?:thon)([\w\W]+?)```")
FILE_INCLUDE_RE = re.compile(r"--8<-- ?['\"].*['\"]")
DISABLE_EXAMPLE_LINT = re.compile(r"<!-- ?disable-examplelint ?-->")
FILENAME_RE = re.compile(r"[\d-]*(.*)")


EXAMPLE_TEST_TEMPLATE = """
from {module_name} import app
from starlite import TestClient


def test_{name}() -> None:
    with TestClient(app=app) as client:
        pass
"""


def _find_matching_lineno(source_lines: list[str], find: str) -> int:
    match_lines = find.splitlines()

    for i, _ in enumerate(source_lines):
        if match_lines == source_lines[i : i + len(match_lines)]:
            return i + 1

    raise RuntimeError("Could not match linneo")


def _is_allowed_code_block(code_block: str, max_line_length: int) -> bool:
    if DISABLE_EXAMPLE_LINT.search(code_block):
        return True
    if FILE_INCLUDE_RE.search(code_block):
        return True
    return code_block.count("\n") <= max_line_length


def _find_code_blocks(content: str, max_line_length: int) -> list[str]:
    return [
        code_block
        for code_block in CODE_BLOCK_RE.findall(content)
        if not _is_allowed_code_block(code_block, max_line_length=max_line_length)
    ]


def extract_examples(
    file_name: str,
    target_dir_name: str = "examples",
    name: str | None = None,
    max_line_length: int = 15,
) -> None:
    file = Path(file_name)
    content = file.read_text()

    base_examples_dir = Path("examples")
    base_tests_dir = base_examples_dir / "tests"

    examples_dir = base_examples_dir / target_dir_name
    tests_dir = base_tests_dir / examples_dir.relative_to(base_examples_dir)

    examples_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    if not name:
        if not (match := FILENAME_RE.match(file.with_suffix("").name)):
            raise ValueError(f"Could not generate name from filename {file.name!r}")
        name = match.group(1).replace("-", "_")

    code_blocks = _find_code_blocks(content, max_line_length)
    for i, code_block in enumerate(code_blocks):
        target_path = examples_dir / name
        if len(code_blocks) > 1:
            target_path = target_path.with_name(target_path.stem + f"_{i + 1}.py")
        target_path = target_path.with_suffix(".py")
        test_file_path = tests_dir / f"test_{target_path.name}"

        content = content.replace(code_block, f'```python\n--8<-- "{target_path}"\n```\n')
        if not (code_match := CODE_BLOCK_CODE.match(code_block)):
            raise ValueError(f"Unexpectedly missing code block in {file}")
        code = code_match.group(1).strip()
        target_path.write_text(code)

        test_file_path.write_text(
            EXAMPLE_TEST_TEMPLATE.format(
                module_name=str(target_path.with_suffix("")).replace("/", "."), name=target_path.stem
            )
        )

        print(f"Extracted example to: {target_path}")
        print(f"Created test stub in: {test_file_path}")

    file.write_text(content)


def check_docs(max_line_length: int = 15) -> int:
    errors = 0
    for file in Path("docs").rglob("*.md"):
        content = file.read_text()
        content_lines = content.splitlines()
        if DISABLE_EXAMPLE_LINT.search(content_lines[0]):
            continue

        for code_block in _find_code_blocks(content, max_line_length):
            errors += 1
            lineno = _find_matching_lineno(content_lines, code_block)
            print(
                f"{file}:{lineno}: Inline code examples longer than 15 lines are not allowed "
                "and should be put in a separate file"
            )
    return errors


def check_command(args: Namespace) -> None:
    raise SystemExit(1 if check_docs(max_line_length=args.line_length) else 0)


def extract_command(args: Namespace) -> None:
    extract_examples(
        file_name=args.filename,
        target_dir_name=args.directory,
        name=args.name,
        max_line_length=args.line_length,
    )


def cli() -> None:
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    parser_check = subparsers.add_parser("check")
    parser_extract = subparsers.add_parser("extract")

    parser_check.add_argument("--line-length", default=15)

    parser_extract.add_argument("filename")
    parser_extract.add_argument("-n", "--name")
    parser_extract.add_argument("-d", "--directory", default="examples")
    parser_extract.add_argument("-l", "--line-length", default=15)

    parser_check.set_defaults(func=check_command)
    parser_extract.set_defaults(func=extract_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    cli()
