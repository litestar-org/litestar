from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, List, cast

from pymongo.errors import DuplicateKeyError, PyMongoError

from litestar.contrib.repository import ConflictError, RepositoryError


@contextmanager
def wrap_pymongo_exception() -> Any:
    """Do something within context to raise a ``RepositoryError`` chained
    from an original ``PyMongoError``.

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
    except DuplicateKeyError as e:
        raise ConflictError from e
    except PyMongoError as e:
        raise RepositoryError(f"An exception occurred: {e}") from e


async def _convert_cursor_to_list_async(cursor: Any) -> list[dict[str, Any]]:
    return cast(List[Dict[str, Any]], await cursor.to_list(None))


def _convert_cursor_to_list_sync(cursor: Any) -> list[dict[str, Any]]:
    return list(cursor)
