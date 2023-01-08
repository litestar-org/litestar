import re
from typing import Tuple


def indent(string: str, indent_char: str = " ", level: int = 4) -> str:
    return "\n".join((indent_char * level) + line for line in string.splitlines())


RGX_CODE_BLOCK = re.compile(r" *```py[\w\W]+?```")


def get_indentation(text: str) -> Tuple[str, int]:
    if match := re.match("^[ \t]+", text):
        indentation = match.group()
        indent_char = indentation[0]
        return indent_char, len(indentation)
    return " ", 0
