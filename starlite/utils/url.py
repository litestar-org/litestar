from typing import Sequence


def normalize_path(path: str) -> str:
    """
    Normalizes a given path by ensuring it starts with a slash and does not end with a slash
    """
    if path == "/":
        return path
    if not path.startswith("/"):
        path = "/" + path
    if path.endswith("/"):
        path = path[: len(path) - 1]
    while "//" in path:
        path = path.replace("//", "/")
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
