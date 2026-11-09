"""Offline tests for the changelog folding in ``tools/consolidate_prereleases.py``."""

import pytest
from tools.consolidate_prereleases import _same_line, consolidate


def _section(version: str, date: str, *titles: str) -> str:
    body = "".join(f"\n    .. change:: {title}\n        :type: feature\n        :pr: 1\n" for title in titles)
    return f".. changelog:: {version}\n    :date: {date}\n{body}\n"


def _versions(text: str) -> list[str]:
    return [line.removeprefix(".. changelog:: ").strip() for line in text.splitlines() if line.startswith(".. chan")]


def _titles(text: str) -> list[str]:
    return [line.strip().removeprefix(".. change:: ") for line in text.splitlines() if ".. change::" in line]


class TestSameLine:
    @pytest.mark.parametrize(
        "version",
        [
            "3.1.0",
            "3.1.0a1",
            "3.1.0b2",
            "3.1.0rc1",
            "3.1.0.dev1",
            "3.1.0b1.dev3",
            "3.1.0alpha1",
            "3.1.0beta4",
            "v3.1.0rc1",
        ],
    )
    def test_belongs_to_the_line(self, version: str) -> None:
        assert _same_line(version, "3.1.0") is True

    @pytest.mark.parametrize("version", ["3.1.1", "3.1.10b1", "3.2.0", "2.1.0", "3.1.0.post1", "nonsense"])
    def test_does_not_belong_to_the_line(self, version: str) -> None:
        assert _same_line(version, "3.1.0") is False


class TestConsolidate:
    def test_folds_pre_releases_into_the_final(self) -> None:
        text = _section("3.1.0", "2026-12-01", "final fix") + _section("3.1.0rc1", "2026-11-20", "rc work")

        out = consolidate(text, "3.1.0")

        assert _versions(out) == ["3.1.0"]
        assert _titles(out) == ["final fix", "rc work"]
        assert ":date: 2026-12-01" in out

    def test_keeps_an_interleaved_section_of_another_line(self) -> None:
        text = (
            _section("3.1.0", "2026-12-01", "final fix")
            + _section("3.1.0rc1", "2026-11-20", "rc work")
            + _section("3.0.1", "2026-11-15", "HOTFIX auth bypass")
            + _section("3.1.0b1", "2026-11-10", "beta work")
            + _section("3.0.0", "2026-11-01", "the major")
        )

        out = consolidate(text, "3.1.0")

        assert _versions(out) == ["3.1.0", "3.0.1", "3.0.0"]
        assert "HOTFIX auth bypass" in out
        assert _titles(out) == ["final fix", "rc work", "beta work", "HOTFIX auth bypass", "the major"]

    def test_is_idempotent(self) -> None:
        text = (
            _section("3.1.0", "2026-12-01", "final fix")
            + _section("3.1.0rc1", "2026-11-20", "rc work")
            + _section("3.0.1", "2026-11-15", "hotfix")
        )

        once = consolidate(text, "3.1.0")

        assert consolidate(once, "3.1.0") == once

    def test_a_missing_final_section_does_not_inherit_a_pre_release_date(self) -> None:
        text = _section("3.1.0rc1", "2026-11-20", "rc work") + _section("3.1.0b1", "2026-11-10", "beta work")

        out = consolidate(text, "3.1.0", date="2026-12-01")

        assert _versions(out) == ["3.1.0"]
        assert ":date: 2026-12-01" in out
        assert "2026-11-20" not in out

    def test_a_lone_pre_release_is_still_renamed_to_the_final(self) -> None:
        text = _section("3.1.0rc1", "2026-11-20", "rc work")

        out = consolidate(text, "3.1.0", date="2026-12-01")

        assert _versions(out) == ["3.1.0"]
        assert _titles(out) == ["rc work"]

    def test_a_final_with_no_pre_releases_is_untouched(self) -> None:
        text = _section("3.1.0", "2026-12-01", "final fix") + _section("3.0.0", "2026-11-01", "the major")

        assert consolidate(text, "3.1.0") == text

    def test_text_without_any_section_is_untouched(self) -> None:
        assert consolidate("just some prose\n", "3.1.0") == "just some prose\n"

    def test_unrecognised_pre_release_spellings_are_folded_not_dropped(self) -> None:
        text = (
            _section("3.1.0", "2026-12-01", "final fix")
            + _section("3.1.0b1.dev3", "2026-11-18", "dev of beta")
            + _section("3.1.0b1", "2026-11-10", "beta work")
        )

        out = consolidate(text, "3.1.0")

        assert _versions(out) == ["3.1.0"]
        assert "dev of beta" in out

    def test_change_blocks_are_copied_verbatim(self) -> None:
        text = (
            ".. changelog:: 3.1.0\n    :date: 2026-12-01\n\n"
            "    .. change:: a thing\n        :type: feature\n        :pr: 1\n        :breaking:\n\n"
            "        Indented body with a ``literal``.\n\n" + _section("3.1.0rc1", "2026-11-20", "rc work")
        )

        out = consolidate(text, "3.1.0")

        assert "        :breaking:" in out
        assert "        Indented body with a ``literal``." in out
