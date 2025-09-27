import pytest


def test_contrib_minijnja_deprecation() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.contrib.minijnja import MiniJinjaTemplateEngine  # noqa: F401


def test_minijinja_from_state_deprecation() -> None:
    with pytest.warns(DeprecationWarning):
        from litestar.contrib.minijinja import minijinja_from_state  # noqa: F401
