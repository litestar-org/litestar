import importlib.metadata
import json
import shutil
import subprocess
from pathlib import Path
import argparse
import shutil

parser = argparse.ArgumentParser()
parser.add_argument("--version", required=False)
parser.add_argument("--push", action="store_true")
parser.add_argument("--latest", action="store_true")


def add_to_versions_file(version: str, latest: bool) -> None:
    versions_file = Path("versions.json")
    versions = []
    if versions_file.exists():
        versions = json.loads(versions_file.read_text())

    new_version_spec = {"version": version, "title": version, "aliases": []}
    if any(v["version"] == version for v in versions):
        versions = [v if v["version"] != version else new_version_spec for v in versions]
    else:
        versions.insert(0, new_version_spec)

    if latest:
        for version in versions:
            version["aliases"] = []
        versions[0]["aliases"] = ["latest"]

    versions_file.write_text(json.dumps(versions))


def make_version(version: str, push: bool, latest: bool) -> None:
    subprocess.run(["make", "docs"], check=True)

    subprocess.run(["git", "checkout", "gh-pages"], check=True)

    add_to_versions_file(version, latest)

    docs_src_path = Path("docs/_build/html")
    docs_dest_path = Path(version)
    docs_dest_path_latest = Path("latest")
    if docs_dest_path.exists():
        shutil.rmtree(docs_dest_path)

    docs_src_path.rename(docs_dest_path)
    if latest:
        if docs_dest_path_latest.exists():
            shutil.rmtree(docs_dest_path_latest)
        shutil.copytree(docs_dest_path, docs_dest_path_latest)
        subprocess.run(["git", "add", "latest"], check=True)

    subprocess.run(["git", "add", version], check=True)
    subprocess.run(["git", "add", "versions.json"], check=True)
    subprocess.run(["git", "commit", "-m", f"automated docs build: {version}"], check=True)
    if push:
        subprocess.run(["git", "push"], check=True)
    subprocess.run(["git", "checkout", "-"], check=True)


def main() -> None:
    args = parser.parse_args()
    version = args.version or importlib.metadata.version("starlite").rsplit(".", 1)[0]
    make_version(version=version, push=args.push, latest=args.latest)


if __name__ == "__main__":
    main()
