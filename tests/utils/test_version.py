import pytest

from litestar.utils.version import Version, parse_version


@pytest.mark.parametrize(
    "raw_version,expected",
    [
        ("2.0.0alpha1", Version(2, 0, 0, "alpha", 1)),
        ("2.0.0a1", Version(2, 0, 0, "alpha", 1)),  # test importlib.metadata.version coercion
        ("2.0.0alpha2", Version(2, 0, 0, "alpha", 2)),
        ("2.0.0beta1", Version(2, 0, 0, "beta", 1)),
        ("2.0.0b1", Version(2, 0, 0, "beta", 1)),  # test importlib.metadata.version coercion
        ("2.0.0beta2", Version(2, 0, 0, "beta", 2)),
        ("2.0.0rc1", Version(2, 0, 0, "rc", 1)),
        ("2.0.0rc2", Version(2, 0, 0, "rc", 2)),
        ("2.0.0", Version(2, 0, 0, "final", 0)),
        ("2.13.45", Version(2, 13, 45, "final", 0)),
    ],
)
def test_parse_version(raw_version: str, expected: Version) -> None:
    assert parse_version(raw_version) == expected


@pytest.mark.parametrize("raw_version", ["0.1", "1.0.0foo1", "1.0.0alpha", "1.0.0.0"])
def test_parse_invalid_version(raw_version: str) -> None:
    with pytest.raises(ValueError):
        parse_version(raw_version)


@pytest.mark.parametrize("short,expected_output", [(True, "2.0.0"), (False, "2.0.0alpha1")])
def test_formatted(short: bool, expected_output: str) -> None:
    assert parse_version("2.0.0alpha1").formatted(short=short) == expected_output
