from __future__ import annotations

from abc import ABC, abstractmethod
from inspect import isabstract
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from litestar.controller.base import Controller
from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers.http_handlers import post
from litestar.types import PathParameterType

if TYPE_CHECKING:
    from litestar.connection.request import Request


__all__ = ("AbstractGenericControllerMixin",)

T = TypeVar("T")
K = TypeVar("K", bound=PathParameterType)


class AbstractGenericControllerMixin(ABC, Generic[T, K]):
    """Controller type that supports generic inheritance hierarchies."""

    id_kwarg_name: str = "id"
    """
    Name of the the id kwarg - this value will be used for the id path parameter

    Examples
      - /{id:str} - if the value of id_kwarg_name is "id".
      - /{item_id:str} - if the value id_kwarg_name is "item_id".
    """
    id_kwarg_type: K
    """Type of the id kwarg - this value will be used for the id path parameter

    Examples
      - /{id:str} - if the value of id_kwarg_type is "str".
      - /{id:int} - if the value id_kwarg_type is "int".
    """
    model_type: type[T]
    """The model type for the generic controller."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        if not isabstract(cls) and not hasattr(cls, "model_type"):
            raise ImproperlyConfiguredException("a model_type attribute must be defined on generic controller mixins")

        super().__init_subclass__(**kwargs)


class AsyncCreateMixin(Generic[T], AbstractGenericControllerMixin[T, Any]):
    @abstractmethod
    async def perform_create(self, *, data: dict[str, Any], request: Request[Any, Any, Any]) -> T:
        """Handle a create operation.

        This method should be implemented for a particular backend or repository.
        """
        raise NotImplementedError()

    @post("/")
    async def create(self, data: dict[str, Any], request: Request[Any, Any, Any]) -> T:
        return await self.perform_create(data=data, request=request)


class SyncCreateMixin(Controller, Generic[T], AbstractGenericControllerMixin[T, Any]):
    @abstractmethod
    def perform_create(self, *, data: dict[str, Any], request: Request[Any, Any, Any]) -> T:
        """Handle a create operation.

        This method should be implemented for a particular backend or repository.
        """
        raise NotImplementedError()

    @post("/")
    def create(self, data: dict[str, Any], request: Request[Any, Any, Any]) -> T:
        return self.perform_create(data=data, request=request)
