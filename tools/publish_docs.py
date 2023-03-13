import argparse
import importlib.metadata
import json
import os
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import TypedDict

parser = argparse.ArgumentParser()
parser.add_argument("--version", required=False)
parser.add_argument("--push", action="store_true")


class VersionSpec(TypedDict):
    versions: list[str]
    latest: str
    docs_latest: str


@contextmanager
def checkout(branch: str) -> None:
    subprocess.run(["git", "checkout", branch], check=True)
    yield
    subprocess.run(["git", "checkout", "-"], check=True)


def add_to_versions_file(version: str) -> VersionSpec:
    versions_file = Path("versions.json")
    version_spec: VersionSpec
    if versions_file.exists():
        version_spec = json.loads(versions_file.read_text())
    else:
        version_spec = {"versions": [], "latest": "", "docs_latest": ""}

    if version not in version_spec["versions"]:
        version_spec["versions"].append(version)

    versions_file.write_text(json.dumps(version_spec))

    return version_spec


def make_version(version: str | None, push: bool) -> None:
    if version is None:
        version = importlib.metadata.version("starlite").rsplit(".")[0]
    else:
        os.environ["_STARLITE_DOCS_BUILD_VERSION"] = version

    git_add = [".nojekyll", "versions.json", version]
    subprocess.run(["make", "docs"], check=True)

    with checkout("gh-pages"):
        Path(".nojekyll").touch(exist_ok=True)

        version_spec = add_to_versions_file(version)
        rebuild_page = version_spec["docs_latest"] == version
        is_latest = version == version_spec["latest"]

        docs_src_path = Path("docs/_build/html")

        inventory_file = docs_src_path / "objects.inv"
        shutil.copytree(docs_src_path / "lib", version, dirs_exist_ok=True)
        shutil.copy2(inventory_file, version)
        git_add.append(f"{version}/objects.inv")

        if rebuild_page:
            for path in docs_src_path.iterdir():
                git_add.append(path.name)
                if path.is_dir():
                    if path == docs_src_path / "lib" and not is_latest:
                        continue
                    shutil.copytree(path, path.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(path, ".")

        if is_latest:
            shutil.copytree(docs_src_path / "lib", "lib", dirs_exist_ok=True)
            shutil.copy2(inventory_file, "lib")
            git_add.append("lib/objects.inv")

        shutil.rmtree("docs/_build")
        Path("objects.inv").unlink()

        for file in git_add:
            subprocess.run(["git", "add", file], check=True)

        subprocess.run(
            ["git", "commit", "-m", f"Automatic docs build for version {version!r}", "--no-verify"],
            check=True,
        )

        if push:
            subprocess.run(["git", "push"], check=True)


def main() -> None:
    args = parser.parse_args()
    make_version(version=args.version, push=args.push)


if __name__ == "__main__":
    main()
