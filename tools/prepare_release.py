from __future__ import annotations

import asyncio
import datetime
import os
import re
import shutil
import subprocess
from collections import defaultdict
from dataclasses import dataclass

import click
import httpx2
import msgspec

_polar = "[Polar.sh](https://polar.sh/litestar-org)"
_open_collective = "[OpenCollective](https://opencollective.com/litestar)"
_github_sponsors = "[GitHub Sponsors](https://github.com/sponsors/litestar-org/)"

_REPO = "litestar-org/litestar"
_PRERELEASE_RE = re.compile(r"(a|b|rc)\d+|\.dev\d+")


class PullRequest(msgspec.Struct, kw_only=True):
    title: str
    number: int
    created_at: str
    user: RepoUser


class Comp(msgspec.Struct):
    sha: str

    class _Commit(msgspec.Struct):
        message: str

    commit: _Commit


class RepoUser(msgspec.Struct):
    login: str
    id: int
    type: str


@dataclass
class PRInfo:
    url: str
    clean_title: str
    cc_type: str
    number: int
    created_at: datetime.datetime
    user: RepoUser
    breaking: bool = False


@dataclass
class ReleaseInfo:
    base: str
    release_tag: str
    version: str
    pull_requests: dict[str, list[PRInfo]]
    first_time_prs: list[PRInfo]

    @property
    def compare_url(self) -> str:
        return f"https://github.com/{_REPO}/compare/{self.base}...{self.release_tag}"


def _pr_number_from_commit(comp: Comp) -> int | None:
    # squash-merge subjects carry the PR number; the API offers no better link
    message_head = comp.commit.message.split("\n\n")[0]
    match = re.search(r"\(#(\d+)\)$", message_head)
    if not match:
        print(f"Could not find PR number in {message_head}")  # noqa: T201
    return int(match[1]) if match else None


class _Thing:
    def __init__(self, *, gh_token: str, base: str, release_branch: str, tag: str, version: str) -> None:
        self._base = base
        self._new_release_tag = tag
        self._release_branch = release_branch
        self._new_release_version = version
        self._api_client = httpx2.AsyncClient(
            headers={
                "Authorization": f"Bearer {gh_token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "Accept": "application/vnd.github+json",
            },
            base_url=f"https://api.github.com/repos/{_REPO}/",
        )

    async def _get_pr_info_for_pr(self, number: int) -> PRInfo | None:
        res = await self._api_client.get(f"/pulls/{number}")
        if res.is_client_error:
            click.secho(
                f"Could not get PR info for {number}.  Fetch request returned a status of {res.status_code}",
                fg="yellow",
            )
            return None
        res.raise_for_status()
        pr = msgspec.convert(res.json(), type=PullRequest)

        # 553 of the last 3000 merged PRs have no conventional-commit prefix; they belong in
        # "Other changes", not in a crash that takes the whole run down.
        cc_prefix, separator, clean_title = pr.title.partition(":")
        if not separator:
            cc_prefix, clean_title = "", pr.title
        cc_prefix = cc_prefix.strip()
        cc_type = cc_prefix.split("(", maxsplit=1)[0].rstrip("!").lower()

        return PRInfo(
            number=pr.number,
            cc_type=cc_type,
            clean_title=clean_title.strip(),
            breaking=cc_prefix.endswith("!"),
            url=f"https://github.com/{_REPO}/pull/{pr.number}",
            created_at=datetime.datetime.strptime(pr.created_at, "%Y-%m-%dT%H:%M:%S%z"),
            user=pr.user,
        )

    async def _get_compare_commits(self) -> list[Comp]:
        collected: list[Comp] = []
        seen: set[str] = set()
        total: int | None = None
        page = 1
        while True:
            res = await self._api_client.get(
                f"/compare/{self._base}...{self._release_branch}",
                params={"per_page": 100, "page": page},
            )
            res.raise_for_status()
            payload = res.json()
            if total is None:
                total = payload.get("total_commits")
                if total is None:
                    raise click.ClickException(
                        f"{self._base}...{self._release_branch}: the compare response carries no "
                        "`total_commits`, so the range cannot be verified as complete."
                    )
            fresh = [comp for comp in msgspec.convert(payload["commits"], list[Comp]) if comp.sha not in seen]
            seen.update(comp.sha for comp in fresh)
            collected.extend(fresh)
            if not fresh or len(collected) >= total:
                break
            page += 1

        if len(collected) < total:
            raise click.ClickException(
                f"{self._base}...{self._release_branch}: the API reports {total} commits but only "
                f"{len(collected)} could be collected — refusing to build incomplete release notes."
            )
        return collected

    async def get_prs(self) -> dict[str, list[PRInfo]]:
        compares = await self._get_compare_commits()
        pr_numbers = [n for n in (_pr_number_from_commit(c) for c in compares) if n is not None]
        pulls = await asyncio.gather(*map(self._get_pr_info_for_pr, pr_numbers))

        prs = defaultdict(list)
        for pr in pulls:
            if not pr:
                continue
            if pr.user.type != "Bot":
                prs[pr.cc_type].append(pr)
        return prs

    async def _get_first_time_contributions(self, prs: dict[str, list[PRInfo]]) -> list[PRInfo]:
        # no commit on main before this release's first commit => first contribution
        prs_by_user_login: dict[str, list[PRInfo]] = defaultdict(list)
        for pr in [p for type_prs in prs.values() for p in type_prs]:
            prs_by_user_login[pr.user.login].append(pr)

        first_prs: list[PRInfo] = []

        async def is_user_first_commit(user_login: str) -> None:
            first_pr = sorted(prs_by_user_login[user_login], key=lambda p: p.created_at)[0]
            res = await self._api_client.get(
                "/commits",
                params={
                    "author": user_login,
                    "sha": "main",
                    "until": first_pr.created_at.isoformat(),
                    "per_page": 1,
                },
            )
            res.raise_for_status()

            if len(res.json()) == 0:
                first_prs.append(first_pr)

        await asyncio.gather(*map(is_user_first_commit, prs_by_user_login.keys()))

        return sorted(first_prs, key=lambda pr: pr.created_at)

    async def get_release_info(self) -> ReleaseInfo:
        prs = await self.get_prs()
        first_time_contributors = await self._get_first_time_contributions(prs)
        return ReleaseInfo(
            pull_requests=prs,
            first_time_prs=first_time_contributors,
            base=self._base,
            release_tag=self._new_release_tag,
            version=self._new_release_version,
        )

    async def create_draft_release(self, body: str, release_branch: str) -> str:
        # mark alpha/beta/rc/dev versions as a GitHub pre-release (the API won't derive this)
        is_prerelease = bool(_PRERELEASE_RE.search(self._new_release_version))
        res = await self._api_client.post(
            "/releases",
            json={
                "tag_name": self._new_release_tag,
                "target_commitish": release_branch,
                "name": self._new_release_tag,
                "draft": True,
                "prerelease": is_prerelease,
                "body": body,
            },
        )
        res.raise_for_status()
        return res.json()["html_url"]  # type: ignore[no-any-return]


def _pr_lines(infos: list[PRInfo]) -> list[str]:
    # not .capitalize(), which lowercases acronyms like "OpenAPI"
    return [f"* {i.clean_title[:1].upper() + i.clean_title[1:]} by @{i.user.login} in {i.url}" for i in infos]


def build_gh_release_notes(release_info: ReleaseInfo) -> str:
    # this is for the most part just recreating GitHub's autogenerated release notes
    # but with three important differences:
    # 1. PRs are sorted into categories
    # 2. The conventional commit type is stripped from the title
    # 3. It works with our release branch process. GitHub doesn't pick up (all) commits
    #    made there depending on how things were merged
    sections = (
        ("feat", "### New features"),
        ("fix", "### Bugfixes"),
        ("perf", "### Performance"),
        ("refactor", "### Refactors"),
        ("docs", "### Documentation"),
    )
    titled_types = {cc_type for cc_type, _ in sections}
    ignored_types = {"ci", "chore"}  # internal noise, kept out of the notes
    section_order = {cc_type: index for index, (cc_type, _) in enumerate(sections)}

    lines = ["## What's changed"]

    if breaking := sorted(
        (pr for prs in release_info.pull_requests.values() for pr in prs if pr.breaking),
        key=lambda pr: (section_order.get(pr.cc_type, len(section_order)), pr.number),
    ):
        lines += ["", "### Breaking changes", *_pr_lines(breaking)]

    for cc_type, title in sections:
        if prs := [pr for pr in release_info.pull_requests.get(cc_type, []) if not pr.breaking]:
            lines += ["", title, *_pr_lines(prs)]

    if other := [
        pr
        for cc_type, prs in release_info.pull_requests.items()
        if cc_type not in titled_types and cc_type not in ignored_types
        for pr in prs
        if not pr.breaking
    ]:
        lines += ["", "### Other changes", *_pr_lines(other)]

    if release_info.first_time_prs:
        lines += ["", "## New contributors"]
        lines += [f"* @{pr.user.login} made their first contribution in {pr.url}" for pr in release_info.first_time_prs]

    version = release_info.version
    # the sponsor handles are NOT auto-fetched (no single API across the three platforms) —
    # maintainers fill the empty slots from the dashboards before publishing the draft.
    lines.append(f"""
**Full Changelog**
{release_info.compare_url}

## Installation
Install or upgrade to `{version}`:
```shell
# uv
uv add "litestar=={version}"
# pip
pip install --upgrade "litestar=={version}"
```

## Sponsors
Thanks to these incredible business sponsors:
-{" "}

Thanks to these incredible personal sponsors:
- {_polar}:{" "}
- {_github_sponsors}:{" "}
- {_open_collective}:{" "}""")

    return "\n".join(lines) + "\n"


def _get_gh_token() -> str:
    if gh_token := os.getenv("GH_TOKEN"):
        click.secho("Using GitHub token from env", fg="blue")
        return gh_token

    gh_executable = shutil.which("gh")
    if not gh_executable:
        click.secho("GitHub CLI not installed", fg="yellow")
    else:
        click.secho("Using GitHub CLI to obtain GitHub token", fg="blue")
        proc = subprocess.run([gh_executable, "auth", "token"], check=True, capture_output=True, text=True)
        if out := (proc.stdout or "").strip():
            return out

    click.secho("Could not find any GitHub token", fg="red")
    quit(1)


def _release_line(version: str) -> str | None:
    match = re.match(r"v?(\d+)\.", version)
    return match[1] if match else None


def _get_latest_tag(gh_token: str | None = None, version: str | None = None) -> str:
    click.secho("Resolving the previous release", fg="blue")
    headers = {"Accept": "application/vnd.github+json"}
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token}"
    try:
        res = httpx2.get(
            f"https://api.github.com/repos/{_REPO}/releases",
            headers=headers,
            params={"per_page": 100},
            timeout=15,
        )
        res.raise_for_status()
        tags: list[str] = [release["tag_name"] for release in res.json() if not release["draft"]]
        if not tags:
            raise ValueError("the repository has no published release")
    except Exception as exc:  # fall back to local tags if the API is unreachable
        click.secho(f"  (API release lookup failed, using local git tags: {exc})", fg="yellow")
        # `creatordate` matches the API order (a release's `created_at` is its tagged commit's
        # date) and, unlike `taggerdate`, is populated for litestar's many lightweight tags.
        # NOT `v:refname`, which ranks a final release below its own pre-releases.
        out = subprocess.run(
            ["git", "tag", "--sort=-creatordate"], check=False, capture_output=True, text=True
        ).stdout.strip()
        if not out:
            raise click.ClickException("no release or tag found to use as a compare base") from exc
        tags = out.splitlines()

    # a final release compares against the previous FINAL, so its notes carry the whole line
    # (matching the changelog, which consolidate_prereleases.py folds the same way); a
    # pre-release compares against its immediate predecessor to stay a delta.
    eligible = tags
    if not _PRERELEASE_RE.search(version or ""):
        eligible = [tag for tag in tags if not _PRERELEASE_RE.search(tag)] or tags

    if (line := _release_line(version or "")) and (
        candidates := [tag for tag in eligible if _release_line(tag) == line]
    ):
        click.secho(f"  using {candidates[0]} (latest {line}.x release)", fg="blue")
        return candidates[0]
    click.secho(f"  using {eligible[0]} (latest release; no {version} line predecessor)", fg="blue")
    return eligible[0]


@click.command()
@click.argument("version")
@click.option("--base", help="Previous release tag. Defaults to the latest tag")
@click.option("--branch", help="Release branch", default="main")
@click.option(
    "--gh-token",
    help="GitHub token. If not provided, read from the GH_TOKEN env variable. "
    "Alternatively, if the GitHub CLI is installed, it will be used to fetch a token",
)
@click.option("-c", "--create-draft-release", is_flag=True, help="Create draft release on GitHub")
def cli(
    base: str | None,
    branch: str,
    version: str,
    gh_token: str | None,
    create_draft_release: bool,
) -> None:
    if gh_token is None:
        gh_token = _get_gh_token()
    if base is None:
        base = _get_latest_tag(gh_token, version)

    if not re.match(r"\d+\.\d+\.\d+", version):
        click.secho(f"Invalid version: {version!r}")
        quit(1)

    new_tag = f"v{version}"

    click.secho(f"Creating release notes for tag {new_tag}, using {base} as a base", fg="cyan")

    thing = _Thing(gh_token=gh_token, base=base, release_branch=branch, tag=new_tag, version=version)
    loop = asyncio.new_event_loop()

    release_info = loop.run_until_complete(thing.get_release_info())
    gh_release_notes = build_gh_release_notes(release_info)

    if create_draft_release:
        click.secho("Creating draft release", fg="blue")
        release_url = loop.run_until_complete(thing.create_draft_release(body=gh_release_notes, release_branch=branch))
        click.echo(f"Draft release available at: {release_url}")
    else:
        click.echo(gh_release_notes)

    loop.close()


if __name__ == "__main__":
    cli()
