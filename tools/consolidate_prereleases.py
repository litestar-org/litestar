"""Fold pre-release changelog sections into the final version's section.

At a FINAL release, towncrier has just created a ``.. changelog:: <final>`` section from
the fragments accumulated since the last pre-release (or no section at all, when there were
no fragments). This merges the ``.. change::`` blocks from every section of the same release
line — the final itself plus any pre-release or dev release of it, in any PEP 440 spelling —
into a single ``.. changelog:: <final>`` section, and removes the now-empty sections.
A ``.. changelog:: <final>.postN`` section is left alone: a post-release is cut after the
final and keeps its own entry.

Sections belonging to OTHER release lines are preserved wherever they sit, including between
two sections of the line being folded (towncrier inserts newest-first, so a patch shipped
during a beta cycle lands in the middle).

The Sphinx ``changelog`` directive regroups changes by ``:type:`` at render time, so the
order in which the blocks are concatenated does not affect the rendered page.

Usage: python tools/consolidate_prereleases.py <final_version>     e.g. 3.0.0
"""

from __future__ import annotations

import datetime
import pathlib
import re
import sys

CHANGELOG = pathlib.Path(__file__).resolve().parents[1] / "docs" / "release-notes" / "changelog.rst"
_HEADER = re.compile(r"^\.\. changelog:: (?P<version>\S+)\s*$")
# every PEP 440 spelling, because the 2.x cycle really shipped `2.0.0alpha1` / `2.0.0beta1`
_PRE_RELEASE = r"(?:[-_.]?(?:a|alpha|b|beta|c|rc|pre|preview)[-_.]?\d*)"
_DEV = r"(?:[-_.]?dev[-_.]?\d*)"


def _same_line(version: str, final: str) -> bool:
    # the final itself, or any pre-release/dev release of it; NOT a post-release, which is
    # cut after the final and keeps its own section
    return re.fullmatch(rf"v?{re.escape(final)}(?:{_PRE_RELEASE})?(?:{_DEV})?", version) is not None


def consolidate(text: str, final: str, *, date: str | None = None) -> str:
    lines = text.split("\n")
    headers = [(i, m.group("version")) for i, line in enumerate(lines) if (m := _HEADER.match(line))]
    if not headers:
        return text

    spans = []  # (version, start, end-exclusive)
    for k, (start, version) in enumerate(headers):
        end = headers[k + 1][0] if k + 1 < len(headers) else len(lines)
        spans.append((version, start, end))

    line_spans = [(v, s, e) for (v, s, e) in spans if _same_line(v, final)]
    if not line_spans or (len(line_spans) == 1 and line_spans[0][0] == final):
        return text  # nothing to fold

    final_date = date or ""
    change_blocks: list[str] = []
    for version, s, e in line_spans:
        body = lines[s + 1 : e]
        i = 0
        while i < len(body) and (body[i].strip().startswith(":date:") or body[i].strip() == ""):
            if body[i].strip().startswith(":date:") and version == final:
                final_date = body[i].strip()[len(":date:") :].strip()
            i += 1
        block = body[i:]
        while block and block[-1].strip() == "":
            block.pop()
        if block:
            change_blocks.extend(block)
            change_blocks.append("")  # separator between merged sections

    while change_blocks and change_blocks[-1].strip() == "":
        change_blocks.pop()

    merged = [f".. changelog:: {final}"]
    if final_date:
        merged.append(f"    :date: {final_date}")
    merged.append("")
    merged.extend(change_blocks)
    merged.append("")

    # Replace each section on its own, working bottom-up so the earlier offsets stay valid.
    # Splicing the whole first..last range instead would delete any section of ANOTHER release
    # line that towncrier interleaved between them (a patch shipped during a beta cycle).
    out = list(lines)
    for index, (_, start, end) in reversed(list(enumerate(line_spans))):
        out[start:end] = merged if index == 0 else []
    return "\n".join(out)


def main(final: str) -> int:
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:\.post\d+)?", final):
        print(f"refusing to consolidate into non-final version {final!r}", file=sys.stderr)  # noqa: T201
        return 1
    text = CHANGELOG.read_text()
    new = consolidate(text, final, date=datetime.datetime.now(tz=datetime.UTC).date().isoformat())
    if new != text:
        CHANGELOG.write_text(new)
        print(f"Consolidated pre-release sections into '.. changelog:: {final}'")  # noqa: T201
    else:
        print(f"No pre-release sections to consolidate for {final}")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
