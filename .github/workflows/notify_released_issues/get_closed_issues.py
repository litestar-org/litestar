from __future__ import annotations

import itertools
import json
import pathlib
import re
import sys

__all__ = (
    "find_resolved_issues",
    "main",
)


def find_resolved_issues(source: str, tag: str) -> list[str]:
    version = tag.split("v", maxsplit=1)[-1]
    changelog_line = f".. changelog:: {version}"
    stop_line = ".. changelog::"
    return list(
        {
            issue
            for line in itertools.takewhile(
                lambda l: stop_line not in l,  # noqa: E741
                source.split(changelog_line, maxsplit=1)[1].splitlines(),
            )
            if re.match(r"\s+:issue: [\d ,]+", line)
            for issue in re.findall(r"\d+", line)
        }
    )


def main(tag: str) -> str:
    source = pathlib.Path("docs/release-notes/changelog.rst").read_text()
    return json.dumps(find_resolved_issues(source, tag))


if __name__ == "__main__":
    print(main(sys.argv[1]))  # noqa: T201
