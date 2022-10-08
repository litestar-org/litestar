from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union

from typing_extensions import Protocol, runtime_checkable

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
    from sqlalchemy.orm import Session
    from sqlalchemy.types import BINARY, VARBINARY, LargeBinary


SQLAlchemyBinaryType = Union["BINARY", "VARBINARY", "LargeBinary"]


@runtime_checkable
class SessionMakerTypeProtocol(Protocol):
    def __init__(
        self,
        bind: "Optional[Union[AsyncEngine, Engine, Connection]]",
        class_: "Union[Type[AsyncSession], Type[Session]]",
        autoflush: bool,
        expire_on_commit: bool,
        info: Dict[Any, Any],
        **kwargs: Any,
    ) -> None:
        ...

    def __call__(self) -> "Union[Session, AsyncSession]":
        ...


@runtime_checkable
class SessionMakerInstanceProtocol(Protocol):
    def __call__(self) -> "Union[Session, AsyncSession]":
        ...
