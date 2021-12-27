import re

CAPITAL_LETTERS_PATTERN = re.compile(r"(?=[A-Z])")


def pascal_case_to_text(s: str) -> str:
    """Given a 'PascalCased' string, return its split form- 'Pascal Cased'"""
    return " ".join(re.split(CAPITAL_LETTERS_PATTERN, s)).strip()
