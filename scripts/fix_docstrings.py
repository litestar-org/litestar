import re
import sys
from pathlib import Path

INLINE_CODE_RGX = re.compile(r"(?<![`:])`([\w -]+?)`")
REFERENCE_RGX = re.compile(r"\[(.+?)]\[(.+?)]")
DOCSTRING_RGX = re.compile(r'"""[\w\W]+?"""')
CODE_BLOCK_RGX = re.compile(r" *```python([\w\W]+?)```")


def fix_inline_code(content: str) -> str:
    return INLINE_CODE_RGX.sub("``\g<1>``", content)


def fix_references_in_docstring(content: str) -> str:
    replacements = {}
    for match in REFERENCE_RGX.finditer(content):
        source = match.group(0)
        label = match.group(1)
        target = match.group(2)

        target_kind = "ref"
        target_parts = target.split(".")
        if target_parts[-1][0].islower():
            if not (len(target_parts) > 1 and target_parts[-2][0].isupper()):
                target_kind = "func"
        elif target_parts[-1][1].islower():
            target_kind = "class"
        replacements[source] = f":{target_kind}:`{label} <{target}>`"

    for source, replacement in replacements.items():
        content = content.replace(source, replacement)

    return content


def get_indentation(text: str) -> tuple[str, int]:
    if match := re.match("^[ \t]+", text):
        indentation = match.group()
        indent_char = indentation[0]
        return indent_char, len(indentation)
    return " ", 0


def indent(string: str, indent_char: str = " ", level: int = 4) -> str:
    return "\n".join((indent_char * level) + line for line in string.splitlines())


def fix_code_blocks(content: str) -> str:
    for match in CODE_BLOCK_RGX.finditer(content):
        block = match.group(0)
        code = match.group(1)
        indent_char, indent_level = get_indentation(block)
        code = indent(code, " ", 4)
        replacement_block = f"{indent_char * indent_level}.. code-block: python\n{code}"
        content = content.replace(block, replacement_block)
    return content


def fix_docstrings(content: str) -> str:
    for docstring in DOCSTRING_RGX.findall(content):
        fixed_docstring = fix_references_in_docstring(docstring)
        fixed_docstring = fix_code_blocks(fixed_docstring)
        content = content.replace(docstring, fixed_docstring)

    return content


def fix_file(path: Path) -> None:
    fixed = fix_inline_code(path.read_text())
    fixed = fix_docstrings(fixed)
    path.write_text(fixed)


def main(path: Path) -> None:
    if path.is_dir():
        for file in path.rglob(".py"):
            fix_file(file)
    else:
        fix_file(path)


if __name__ == "__main__":
    fix_file(Path.cwd() / sys.argv[1])
