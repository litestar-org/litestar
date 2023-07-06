from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from pymongo.errors import DuplicateKeyError, PyMongoError

from litestar.contrib.repository import ConflictError, RepositoryError


@contextmanager
def wrap_pymongo_exception() -> Any:
    """Do something within context to raise a `RepositoryError` chained
    from an original `PyMongoError`.

    >>> try:
    ...     with wrap_pymongo_exception():
    ...         raise PyMongoError("Original Exception")
    ... except RepositoryError as exc:
    ...     print(f"caught repository exception from {type(exc.__context__)}")
    ...
    caught repository exception from <class 'pymongo.errors.PyMongoError'>
    """
    try:
        yield
    except DuplicateKeyError as exc:
        raise ConflictError from exc
    except PyMongoError as exc:
        raise RepositoryError(f"An exception occurred: {exc}") from exc
    except AttributeError as exc:
        raise RepositoryError from exc
