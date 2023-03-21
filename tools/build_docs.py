from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import TypedDict

parser = argparse.ArgumentParser()
parser.add_argument("--version", required=False)
parser.add_argument("output")


class VersionSpec(TypedDict):
    versions: list[str]
    latest: str


def add_to_versions_file(version: str) -> VersionSpec:
    versions_file = Path("docs/_static/versions.json")
    version_spec: VersionSpec
    version_spec = json.loads(versions_file.read_text()) if versions_file.exists() else {"versions": [], "latest": ""}

    if version not in version_spec["versions"]:
        version_spec["versions"].append(version)

    versions_file.write_text(json.dumps(version_spec))

    return version_spec


def build(output_dir: str, version: str | None) -> None:
    if version is None:
        version = importlib.metadata.version("starlite").rsplit(".")[0]
    else:
        os.environ["_STARLITE_DOCS_BUILD_VERSION"] = version

    subprocess.run(["make", "docs"], check=True)

    docs_build_path = Path(output_dir)
    docs_build_path.mkdir()
    docs_build_path.joinpath(".nojekyll").touch(exist_ok=True)

    version_spec = add_to_versions_file(version)
    is_latest = version == version_spec["latest"]

    docs_src_path = Path("docs/_build/html")

    if is_latest:
        shutil.copytree(docs_src_path, docs_build_path / "latest", dirs_exist_ok=True)
    shutil.copytree(docs_src_path, docs_build_path / version, dirs_exist_ok=True)


def main() -> None:
    args = parser.parse_args()
    build(output_dir=args.output, version=args.version)


if __name__ == "__main__":
    main()
