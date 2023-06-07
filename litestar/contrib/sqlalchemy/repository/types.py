from typing import TYPE_CHECKING, Any, Tuple, TypeVar

if TYPE_CHECKING:
    from sqlalchemy import Select

    from litestar.contrib.sqlalchemy import base

    from .async_repository import SQLAlchemyAsyncRepository
    from .sync_repository import SQLAlchemySyncRepository


__all__ = (
    "ModelT",
    "SelectT",
    "RowT",
    "SQLAlchemySyncRepositoryT",
    "SQLAlchemyAsyncRepositoryT",
)

T = TypeVar("T")
ModelT = TypeVar("ModelT", bound="base.ModelProtocol")


SelectT = TypeVar("SelectT", bound="Select[Any]")
RowT = TypeVar("RowT", bound=Tuple[Any, ...])


SQLAlchemySyncRepositoryT = TypeVar("SQLAlchemySyncRepositoryT", bound="SQLAlchemySyncRepository")
SQLAlchemyAsyncRepositoryT = TypeVar("SQLAlchemyAsyncRepositoryT", bound="SQLAlchemyAsyncRepository")
