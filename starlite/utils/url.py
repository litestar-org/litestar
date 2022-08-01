import re
from typing import Sequence


def normalize_path(path: str) -> str:
    """
    Normalizes a given path by ensuring it starts with a slash and does not end with a slash
    """
    if path == "":
        return path
    path = path.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    path = re.sub("//+", "/", path)
    return path


def join_paths(paths: Sequence[str]) -> str:
    """
    Normalizes and joins path fragments
    """
    normalized_fragments = []
    for fragment in paths:
        fragment = normalize_path(fragment)
        normalized_fragments.append(fragment)
    return "".join(normalized_fragments)
