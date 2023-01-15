import re
import sys
from pathlib import Path
from typing import Tuple
import m2r


INLINE_CODE_RGX = re.compile(r"(?<![`:\[])`([\w -]+?)`")
REFERENCE_RGX = re.compile(r"\[(.+?)]\[(.+?)]")
DOCSTRING_RGX = re.compile(r'"""[\w\W]+?"""')
CODE_BLOCK_RGX = re.compile(r" *```python([\w\W]+?)```")
SINGLE_QUOTES_RFGX = re.compile(r"'(\w+?)'")
MD_CODE_REF_RGX = re.compile(r"\[`(.+?)`]")


def indent(string: str, indent_char: str = " ", level: int = 4) -> str:
    return "\n".join((indent_char * level) + line for line in string.splitlines())


def get_indentation(text: str) -> Tuple[str, int]:
    if match := re.match("^[ \t]+", text):
        indentation = match.group()
        indent_char = indentation[0]
        return indent_char, len(indentation)
    return " ", 0


def fix_inline_code(content: str) -> str:
    return INLINE_CODE_RGX.sub(r"``\g<1>``", content)


def fix_single_quoted_ref(content: str) -> str:
    return SINGLE_QUOTES_RFGX.sub(r"``\g<1>``", content)


def fix_mkdocstrings_references(content: str) -> str:
    replacements = {}
    for match in REFERENCE_RGX.finditer(content):
        source = match.group(0)
        label = match.group(1)
        target = match.group(2)

        label = label.replace("`", "")

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
        fixed_docstring = fix_mkdocstrings_references(docstring)
        fixed_docstring = fix_single_quoted_ref(fixed_docstring)
        fixed_docstring = fix_code_blocks(fixed_docstring)
        content = content.replace(docstring, fixed_docstring)

    return content


def fix_code_ref_links(content: str) -> str:
    return MD_CODE_REF_RGX.sub(r"[\g<1>]", content)


def _make_literal_include_block(target: str, caption: str | None = None) -> str:
    block = f".. literalinclude:: {target}"
    if caption:
        block += f"\n    :caption: {caption}"
    block += "\n"
    return block


ADMONITION_MAPPING = {
    "note": "note",
    "abstract": "note",
    "info": "note",
    "tip": "tip",
    "success": "tip",
    "question": "hint",
    "warning": "caution",
    "failure": "error",
    "danger": "danger",
    "example": "admonition",
    "important": "attention",
}


def make_admonition(admonition_type: str, title: str | None) -> str:
    sphinx_type = ADMONITION_MAPPING[admonition_type.lower().strip()]
    if title:
        sphinx_type = "admonition"
    admonition = f".. {sphinx_type}::"
    if title:
        admonition += f" {title}"
    admonition += "\n"
    return admonition


def fix_admonitions(content: str) -> str:
    lines = content.splitlines()
    out_lines = []
    while lines:
        line = lines.pop()
        if admonition_header := re.match(r'!!! (\w*)( ".+?")?', line):
            admonition_type = admonition_header.group(1)
            admonition_title = admonition_header.group(2)
            line = line.replace(admonition_header.group(0), make_admonition(admonition_type, admonition_title))

        out_lines.append(line)
    return "\n".join(reversed(out_lines))


def fix_fenced_blocks(content: str) -> str:
    for match in re.finditer(r'```py +?(?:title="(.+?)")?([\w\W]+?)```', content):
        block = match.group(0)
        caption = match.group(1)
        block_content = match.group(2)
        if snippet_include := re.search(r'--8<-- + ?"(.+?)"', block_content):
            snippet_source = snippet_include.group(1)
            if snippet_source.startswith("examples/"):
                snippet_source = f"/{snippet_source}"
            content = content.replace(block, _make_literal_include_block(snippet_source, caption))
    return content


def convert_md_to_rst(source_path: Path) -> None:
    target_path = Path("docs") / source_path.relative_to("docs_mkdocs").with_suffix(".rst")
    content = source_path.read_text()
    content = fix_fenced_blocks(content)
    content = fix_admonitions(content)
    content = fix_mkdocstrings_references(content)
    content = fix_single_quoted_ref(content)
    content = fix_code_ref_links(content)
    content = m2r.convert(content)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content)


def fix_docstrings_in_place(path: Path) -> None:
    content = path.read_text()
    content = fix_inline_code(content)
    content = fix_docstrings(content)
    path.write_text(content)


def fix_docstrings_in_files(path: Path) -> None:
    if path.is_dir():
        for file in path.rglob("*.py"):
            if file.is_dir():
                continue
            fix_docstrings_in_place(file)
    else:
        fix_docstrings_in_place(path)


def convert_md_files(path: Path):
    if path.is_dir():
        for file in path.rglob("*.md"):
            if file.is_dir():
                continue
            convert_md_to_rst(path)
    else:
        convert_md_to_rst(path)


if __name__ == "__main__":
    convert_md_files(Path(sys.argv[1]))
