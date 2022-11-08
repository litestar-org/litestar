import re
from pathlib import Path


CODE_BLOCK_RE = re.compile(r".*```py[\w\W]+?```")
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
    raise SystemExit(check_examples_dir())
