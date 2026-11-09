"""Offline tests for the release-notes generator in ``tools/prepare_release.py``."""

import datetime
import subprocess
from typing import Any

import httpx2
import pytest
from click import ClickException
from tools import prepare_release
from tools.prepare_release import (
    PRInfo,
    ReleaseInfo,
    RepoUser,
    _release_line,
    _Thing,
    build_gh_release_notes,
)

_API_BASE = "https://api.github.com/repos/litestar-org/litestar/"


def _thing(handler: Any) -> _Thing:
    thing = _Thing(gh_token="token", base="v2.25.0", release_branch="main", tag="v3.0.0", version="3.0.0")
    transport = httpx2.MockTransport(handler)
    thing._api_client = httpx2.AsyncClient(transport=transport, base_url=_API_BASE)
    return thing


def _commit(number: int) -> dict[str, Any]:
    return {
        "sha": f"sha{number}",
        "commit": {"message": f"feat: change {number} (#{number})", "url": f"{_API_BASE}commits/sha{number}"},
    }


def _compare_handler(total: int, pages: list[list[dict[str, Any]]]) -> Any:
    def handler(request: httpx2.Request) -> httpx2.Response:
        page = int(request.url.params.get("page", 1))
        commits = pages[page - 1] if page <= len(pages) else []
        return httpx2.Response(200, json={"total_commits": total, "commits": commits})

    return handler


def _pr_payload(title: str, login: str = "contributor") -> dict[str, Any]:
    return {
        "title": title,
        "number": 1,
        "body": "",
        "created_at": "2026-01-01T00:00:00Z",
        "user": {"login": login, "id": 1, "type": "User"},
        "merge_commit_sha": "sha1",
    }


def _pr(cc_type: str, *, breaking: bool = False, title: str = "A change", number: int = 1) -> PRInfo:
    return PRInfo(
        url=f"https://github.com/litestar-org/litestar/pull/{number}",
        clean_title=title,
        cc_type=cc_type,
        number=number,
        created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        user=RepoUser(login="contributor", id=1, type="User"),
        breaking=breaking,
    )


def _release_info(**pull_requests: list[PRInfo]) -> ReleaseInfo:
    return ReleaseInfo(
        base="v2.25.0",
        release_tag="v3.0.0",
        version="3.0.0",
        pull_requests=dict(pull_requests),
        first_time_prs=[],
    )


class TestCompareCommitPagination:
    async def test_collects_every_page(self) -> None:
        pages = [[_commit(i) for i in range(page * 100, page * 100 + 100)] for page in range(4)]
        pages.append([_commit(i) for i in range(400, 473)])
        thing = _thing(_compare_handler(473, pages))

        commits = await thing._get_compare_commits()

        assert len(commits) == 473

    async def test_single_page_shorter_than_the_limit(self) -> None:
        thing = _thing(_compare_handler(3, [[_commit(1), _commit(2), _commit(3)]]))

        assert len(await thing._get_compare_commits()) == 3

    async def test_refuses_to_build_notes_from_a_truncated_range(self) -> None:
        thing = _thing(_compare_handler(473, [[_commit(i) for i in range(250)]]))

        with pytest.raises(ClickException, match="reports 473 commits but only 250"):
            await thing._get_compare_commits()

    async def test_no_commits_at_all_is_not_an_error(self) -> None:
        thing = _thing(_compare_handler(0, [[]]))

        assert await thing._get_compare_commits() == []

    async def test_sends_the_pagination_parameters(self) -> None:
        seen: list[tuple[str | None, str | None]] = []

        def handler(request: httpx2.Request) -> httpx2.Response:
            seen.append((request.url.params.get("per_page"), request.url.params.get("page")))
            page = int(request.url.params["page"])
            commits = [_commit(i) for i in range(100)] if page == 1 else [_commit(i) for i in range(100, 150)]
            return httpx2.Response(200, json={"total_commits": 150, "commits": commits})

        await _thing(handler)._get_compare_commits()

        assert seen == [("100", "1"), ("100", "2")]

    async def test_a_server_ignoring_page_does_not_inflate_the_count(self) -> None:
        def handler(request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(200, json={"total_commits": 400, "commits": [_commit(i) for i in range(100)]})

        with pytest.raises(ClickException, match="reports 400 commits but only 100"):
            await _thing(handler)._get_compare_commits()

    async def test_a_response_without_a_total_is_refused(self) -> None:
        def handler(request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(200, json={"commits": [_commit(1)]})

        with pytest.raises(ClickException, match="no `total_commits`"):
            await _thing(handler)._get_compare_commits()

    async def test_a_range_that_shrinks_mid_run_does_not_abort(self) -> None:
        def handler(request: httpx2.Request) -> httpx2.Response:
            page = int(request.url.params["page"])
            if page == 1:
                return httpx2.Response(200, json={"total_commits": 150, "commits": [_commit(i) for i in range(100)]})
            return httpx2.Response(200, json={"total_commits": 90, "commits": [_commit(i) for i in range(100, 150)]})

        assert len(await _thing(handler)._get_compare_commits()) == 150


class TestConventionalCommitType:
    @pytest.mark.parametrize(
        ("title", "expected_type", "expected_breaking"),
        [
            ("feat: add a thing", "feat", False),
            ("fix(request): handle a thing", "fix", False),
            ("feat!: drop support for Python 3.9", "feat", True),
            ("chore!: drop pydantic 1", "chore", True),
            ("feat(openapi)!: change the schema", "feat", True),
            ("docs!: update to v3 style", "docs", True),
            ("FEAT: shouty", "feat", False),
        ],
    )
    async def test_type_and_breaking_marker(self, title: str, expected_type: str, expected_breaking: bool) -> None:
        def handler(request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(200, json=_pr_payload(title))

        pr = await _thing(handler)._get_pr_info_for_pr(1)

        assert pr is not None
        assert pr.cc_type == expected_type
        assert pr.breaking is expected_breaking


class TestBreakingChangesSection:
    def test_breaking_changes_lead_the_notes(self) -> None:
        notes = build_gh_release_notes(
            _release_info(
                feat=[_pr("feat", breaking=True, title="Drop Python 3.9", number=1), _pr("feat", number=2)],
            )
        )

        assert notes.index("### Breaking changes") < notes.index("### New features")
        assert "* Drop Python 3.9 by @contributor" in notes

    def test_a_breaking_change_is_not_listed_twice(self) -> None:
        notes = build_gh_release_notes(_release_info(feat=[_pr("feat", breaking=True, title="Drop Python 3.9")]))

        assert notes.count("Drop Python 3.9") == 1
        assert "### New features" not in notes

    def test_breaking_changes_of_an_ignored_type_are_still_announced(self) -> None:
        notes = build_gh_release_notes(
            _release_info(
                chore=[_pr("chore", breaking=True, title="Drop pydantic 1"), _pr("chore", title="Bump a dep")],
            )
        )

        assert "* Drop pydantic 1 by @contributor" in notes
        assert "Bump a dep" not in notes

    def test_no_section_without_breaking_changes(self) -> None:
        notes = build_gh_release_notes(_release_info(feat=[_pr("feat")]))

        assert "### Breaking changes" not in notes

    def test_an_unknown_type_still_falls_through_to_other_changes(self) -> None:
        notes = build_gh_release_notes(_release_info(style=[_pr("style", title="Reformat")]))

        assert "### Other changes" in notes
        assert "* Reformat by @contributor" in notes

    def test_a_breaking_change_is_not_repeated_under_other_changes(self) -> None:
        notes = build_gh_release_notes(_release_info(style=[_pr("style", breaking=True, title="Reformat")]))

        assert "### Other changes" not in notes
        assert notes.count("Reformat") == 1


class TestBaseResolution:
    @staticmethod
    def _releases(monkeypatch: pytest.MonkeyPatch, releases: list[dict[str, Any]]) -> None:
        def fake_get(url: str, **kwargs: Any) -> httpx2.Response:
            return httpx2.Response(200, json=releases, request=httpx2.Request("GET", url))

        monkeypatch.setattr(httpx2, "get", fake_get)

    def test_prefers_the_newest_release_of_the_same_major(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._releases(
            monkeypatch,
            [
                {"tag_name": "v3.0.0b1", "draft": False},
                {"tag_name": "v2.25.0", "draft": False},
            ],
        )

        assert prepare_release._get_latest_tag("token", "3.0.0rc1") == "v3.0.0b1"

    def test_a_parallel_release_of_another_major_does_not_win(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._releases(
            monkeypatch,
            [
                {"tag_name": "v2.26.0", "draft": False},
                {"tag_name": "v3.0.0b1", "draft": False},
                {"tag_name": "v2.25.0", "draft": False},
            ],
        )

        assert prepare_release._get_latest_tag("token", "3.0.0rc1") == "v3.0.0b1"

    def test_falls_back_to_the_newest_release_without_a_line_predecessor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._releases(monkeypatch, [{"tag_name": "v2.25.0", "draft": False}])

        assert prepare_release._get_latest_tag("token", "3.0.0b1") == "v2.25.0"

    def test_a_pre_release_compares_against_its_predecessor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._releases(
            monkeypatch,
            [{"tag_name": "v3.0.0rc1", "draft": False}, {"tag_name": "v3.0.0b1", "draft": False}],
        )

        assert prepare_release._get_latest_tag("token", "3.0.0rc2") == "v3.0.0rc1"

    def test_a_final_release_skips_its_own_pre_releases(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._releases(
            monkeypatch,
            [
                {"tag_name": "v3.0.0rc1", "draft": False},
                {"tag_name": "v3.0.0b1", "draft": False},
                {"tag_name": "v2.25.0", "draft": False},
            ],
        )

        assert prepare_release._get_latest_tag("token", "3.0.0") == "v2.25.0"

    def test_a_patch_release_compares_against_the_previous_final(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._releases(
            monkeypatch,
            [
                {"tag_name": "v3.0.0", "draft": False},
                {"tag_name": "v3.0.0rc1", "draft": False},
                {"tag_name": "v2.25.0", "draft": False},
            ],
        )

        assert prepare_release._get_latest_tag("token", "3.0.1") == "v3.0.0"

    def test_an_empty_release_list_falls_back_to_local_tags(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._releases(monkeypatch, [])
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: subprocess.CompletedProcess(args=[], returncode=0, stdout="v2.25.0\n"),
        )

        assert prepare_release._get_latest_tag("token", "3.0.0b1") == "v2.25.0"

    def test_falls_back_to_local_tags_when_the_api_is_unreachable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def unreachable(url: str, **kwargs: Any) -> httpx2.Response:
            raise httpx2.ConnectError("no network")

        monkeypatch.setattr(httpx2, "get", unreachable)
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: subprocess.CompletedProcess(
                args=[], returncode=0, stdout="v2.25.0\nv3.0.0rc1\nv3.0.0b1\n"
            ),
        )

        assert prepare_release._get_latest_tag("token", "3.0.0rc2") == "v3.0.0rc1"

    def test_drafts_are_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._releases(
            monkeypatch,
            [{"tag_name": "v3.0.0rc2", "draft": True}, {"tag_name": "v3.0.0rc1", "draft": False}],
        )

        assert prepare_release._get_latest_tag("token", "3.0.0") == "v3.0.0rc1"


class TestReleaseLine:
    @pytest.mark.parametrize(
        ("version", "expected"),
        [("3.0.0", "3"), ("v3.0.0", "3"), ("3.0.0rc1", "3"), ("v2.25.0", "2"), ("10.1.0", "10"), ("nonsense", None)],
    )
    def test_release_line(self, version: str, expected: str | None) -> None:
        assert _release_line(version) == expected
