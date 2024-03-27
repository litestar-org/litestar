from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.ext.asyncio import AsyncEngine

EngineT_co = TypeVar("EngineT_co", bound="Engine | AsyncEngine", covariant=True)


class HasGetEngine(Protocol[EngineT_co]):
    def get_engine(self) -> EngineT_co: ...


class _CreateEngineMixin(Generic[EngineT_co]): ...
