import importlib.metadata
import json
import shutil
import subprocess
from pathlib import Path
import argparse
import shutil
from typing import TypedDict

parser = argparse.ArgumentParser()
parser.add_argument("--version", required=False)
parser.add_argument("--push", action="store_true")


class VersionSpec(TypedDict):
    versions: list[str]
    latest: str


def add_to_versions_file(version: str) -> VersionSpec:
    versions_file = Path("versions.json")
    version_spec: VersionSpec
    if versions_file.exists():
        version_spec = json.loads(versions_file.read_text())
    else:
        version_spec = {"versions": [], "latest": ""}

    if version not in version_spec["versions"]:
        version_spec["versions"].append(version)

    versions_file.write_text(json.dumps(version_spec))

    return version_spec


def clean_files(keep: list[str]) -> None:
    keep.extend(["versions.json", ".git", ".nojekyll"])

    for path in Path().iterdir():
        if path.name in keep:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def make_version(version: str, push: bool) -> None:
    subprocess.run(["make", "docs"], check=True)

    subprocess.run(["git", "checkout", "gh-pages"], check=True)

    Path(".nojekyll").touch(exist_ok=True)

    version_spec = add_to_versions_file(version)
    is_latest = version == version_spec["latest"]

    docs_src_path = Path("docs/_build/html")

    shutil.copytree(docs_src_path / "lib", version)

    if is_latest:
        for path in docs_src_path.iterdir():
            if path.is_dir():
                shutil.copytree(path, ".")
            else:
                shutil.copy2(path, ".")

    clean_files(version_spec["versions"])

    subprocess.run(["git", "add", "."])


def main() -> None:
    args = parser.parse_args()
    version = args.version or importlib.metadata.version("starlite").rsplit(".")[0]
    make_version(version=version, push=args.push)


if __name__ == "__main__":
    main()
