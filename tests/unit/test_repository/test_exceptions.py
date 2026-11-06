from __future__ import annotations

import pytest

from litestar.repository._exceptions import ConflictError, NotFoundError, RepositoryError


def test_repository_error_is_exception() -> None:
    assert isinstance(RepositoryError(), Exception)


def test_conflict_error_is_repository_error() -> None:
    assert isinstance(ConflictError(), RepositoryError)


def test_not_found_error_is_repository_error() -> None:
    assert isinstance(NotFoundError(), RepositoryError)


def test_repository_error_carries_message() -> None:
    error = RepositoryError("something broke")
    assert str(error) == "something broke"


def test_conflict_error_carries_message() -> None:
    error = ConflictError("duplicate entry")
    assert str(error) == "duplicate entry"


def test_not_found_error_carries_message() -> None:
    error = NotFoundError("item missing")
    assert str(error) == "item missing"


def test_catch_conflict_error_with_repository_error() -> None:
    with pytest.raises(RepositoryError):
        raise ConflictError("duplicate")


def test_catch_not_found_error_with_repository_error() -> None:
    with pytest.raises(RepositoryError):
        raise NotFoundError("missing")


def test_conflict_error_not_caught_by_not_found() -> None:
    with pytest.raises(ConflictError):
        try:
            raise ConflictError("duplicate")
        except NotFoundError:
            pytest.fail("ConflictError should not be caught by NotFoundError")
