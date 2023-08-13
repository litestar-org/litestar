from __future__ import annotations

from abc import ABC, abstractmethod
from inspect import isabstract
from typing import TYPE_CHECKING, Generic, Sequence, TypeVar

from litestar import post
from litestar.exceptions import ImproperlyConfiguredException
from litestar.types import PathParameterType

from .base import Controller

if TYPE_CHECKING:
    from typing import Any

    from litestar.handlers import HTTPRouteHandler

__all__ = ("GenericController",)

T = TypeVar("T")
K = TypeVar("K", bound=PathParameterType)


class GenericMixin(ABC):
    @classmethod
    @abstractmethod
    def create_route_handler(cls) -> HTTPRouteHandler:
        """Factory method called when a subclass of the mixin is initialized, creating a route handler instance.

        This is where logic for the creation of endpoints should exist
        """
        raise NotImplementedError()


class AsyncInstanceCreateMixin(GenericMixin, Generic[T]):
    create_endpoint_path: str | Sequence[str] = "/"
    """Base path for the create endpoint"""
    create_handler_name: str | None = None
    """Name of the route handler for the create_endpoint"""

    @classmethod
    def create_route_handler(cls) -> HTTPRouteHandler:
        return post(cls.create_endpoint_path, name=cls.create_handler_name)(cls.create)

    @abstractmethod
    async def perform_create(self, **kwargs: Any) -> T:
        """Handle a create operation.

        This method should be implemented for a particular backend or repository.
        """
        raise NotImplementedError()

    async def create(self, **kwargs: Any) -> T:
        return await self.perform_create(**kwargs)


class SyncInstanceCreateMixin(GenericMixin, Generic[T]):
    create_endpoint_path: str = "/"
    """Base path for the create endpoint"""
    sync_to_thread: bool = False
    """
    A boolean dictating whether the handler function will be executed in a worker thread or the main event loop.
    """

    @classmethod
    def create_route_handler(cls) -> HTTPRouteHandler:
        return post(
            cls.create_endpoint_path,
            sync_to_thread=cls.sync_to_thread,
        )(cls.create)

    @abstractmethod
    def perform_create(self, **kwargs: Any) -> T:
        """Handle a create operation.

        This method should be implemented for a particular backend or repository.
        """
        raise NotImplementedError()

    def create(self, **kwargs: Any) -> T:
        return self.perform_create(**kwargs)


class GenericController(ABC, Controller, Generic[T, K]):
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
            raise ImproperlyConfiguredException("a model_type attribute must be defined on generic controllers")

        super().__init_subclass__(**kwargs)
