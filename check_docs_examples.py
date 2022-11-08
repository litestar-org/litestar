import re
import sys
from pathlib import Path
from argparse import ArgumentParser


CODE_BLOCK_RE = re.compile(r".*```py[\w\W]+?```")
CODE_BLOCK_CODE = re.compile(r".*```py(?:thon)([\w\W]+?)```")
FILE_INCLUDE_RE = re.compile(r"--8<-- ?['\"].*['\"]")
DISABLE_EXAMPLE_LINT = re.compile(r"<!-- ?disable-examplelint ?-->")


def _find_matching_lineno(source_lines: list[str], find: str) -> int:
    match_lines = find.splitlines()

    for i, source_line in enumerate(source_lines):
        if match_lines == source_lines[i : i + len(match_lines)]:
            return i + 1

    raise RuntimeError


def _allowed_code_block_length(code_block: str) -> bool:
    if DISABLE_EXAMPLE_LINT.search(code_block):
        return True
    if FILE_INCLUDE_RE.search(code_block):
        return True
    return code_block.count("\n") <= 15


def extract_examples(file_name: str, target_dir_name: str, name: str) -> None:
    file = Path(file_name)
    content = file.read_text()
    examples_dir = Path(target_dir_name)
    examples_dir.mkdir(parents=True, exist_ok=True)

    code_blocks: list[str] = CODE_BLOCK_RE.findall(content)
    for i, code_block in enumerate(code_blocks):
        if FILE_INCLUDE_RE.search(code_block):
            continue
        if DISABLE_EXAMPLE_LINT.search(code_block):
            continue
        target_path = examples_dir / name
        if len(code_blocks) > 1:
            target_path = target_path.with_name(target_path.stem + f"_{i + 1}.py")
        target_path = target_path.with_suffix(".py")
        content = content.replace(code_block, f'```python\n--8<-- "{target_path}"\n```\n')
        code = CODE_BLOCK_CODE.match(code_block).group(1).strip()
        target_path.write_text(code)
        print(f"Extracted example to: {target_path}")
    file.write_text(content)


def check_examples_dir() -> int:
    errors = 0
    for file in Path("docs").rglob("*.md"):
        content = file.read_text()
        content_lines = content.splitlines()
        if DISABLE_EXAMPLE_LINT.search(content_lines[0]):
            continue

        code_blocks: list[str] = CODE_BLOCK_RE.findall(content)
        for code_block in code_blocks:
            if not _allowed_code_block_length(code_block):
                errors += 1
                lineno = _find_matching_lineno(content_lines, code_block)
                print(
                    f"{file}:{lineno}: Inline code examples longer than 15 lines are not allowed "
                    "and should be put in a separate file"
                )
    return errors


if __name__ == "__main__":
    if sys.argv[1] == "check":
        raise SystemExit(check_examples_dir())
    elif sys.argv[1] == "extract":
        extract_examples(sys.argv[2], sys.argv[3], sys.argv[4])
