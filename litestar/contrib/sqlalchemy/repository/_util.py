from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from litestar.contrib.repository import ConflictError, RepositoryError

if TYPE_CHECKING:
    from sqlalchemy.orm import InstrumentedAttribute

    from litestar.contrib.sqlalchemy.base import ModelProtocol


@contextmanager
def wrap_sqlalchemy_exception() -> Any:
    """Do something within context to raise a `RepositoryError` chained
    from an original `SQLAlchemyError`.

        >>> try:
        ...     with wrap_sqlalchemy_exception():
        ...         raise SQLAlchemyError("Original Exception")
        ... except RepositoryError as exc:
        ...     print(f"caught repository exception from {type(exc.__context__)}")
        ...
        caught repository exception from <class 'sqlalchemy.exc.SQLAlchemyError'>
    """
    try:
        yield
    except IntegrityError as exc:
        raise ConflictError from exc
    except SQLAlchemyError as exc:
        raise RepositoryError(f"An exception occurred: {exc}") from exc
    except AttributeError as exc:
        raise RepositoryError from exc


def get_instrumented_attr(model: type[ModelProtocol], key: str | InstrumentedAttribute) -> InstrumentedAttribute:
    if isinstance(key, str):
        return cast("InstrumentedAttribute", getattr(model, key))
    return key
