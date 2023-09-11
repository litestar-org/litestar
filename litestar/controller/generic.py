# ruff: noqa: UP007, UP006
from __future__ import annotations

from dataclasses import is_dataclass
from functools import cached_property
from inspect import isawaitable
from operator import attrgetter
from typing import TYPE_CHECKING, Any, Callable, Generic, List, Sequence, TypeVar, cast, get_args

from typing_extensions import Self, get_origin, get_type_hints

from litestar.connection.request import Request
from litestar.controller.base import Controller
from litestar.dto import DataclassDTO, DTOConfig, DTOData, MsgspecDTO
from litestar.enums import HttpMethod
from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers import BaseRouteHandler, HTTPRouteHandler
from litestar.repository.filters import CollectionFilter
from litestar.types import Empty
from litestar.typing import FieldDefinition
from litestar.utils import (
    is_class_and_subclass,
    is_piccolo_class,
    is_pydantic_model_class,
    is_sqlalchemy_model,
    is_struct_class,
)
from litestar.utils.typing import get_safe_generic_origin

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.dto import AbstractDTO
    from litestar.repository import AbstractAsyncRepository, AbstractSyncRepository
    from litestar.router import Router
    from litestar.types import EmptyType

ModelT = TypeVar("ModelT")

GENERIC_METHOD_NAMES = (
    "create_instance",
    "update_instance",
    "delete_instance",
    "get_instance",
    "create_many",
    "update_many",
    "delete_many",
    "get_many",
)


class GenericController(Controller, Generic[ModelT]):
    repository_type: type[AbstractAsyncRepository[ModelT]] | type[AbstractSyncRepository[ModelT]]
    """Repository for the controller's model."""
    instance_id_factory: Callable[[], Any]
    """Factory used to generate a new instance id. Used for POST methods"""
    dto_type: type[AbstractDTO] | EmptyType = Empty
    """Subclass of :class:`AbstractDTO <.dto.base_dto.AbstractDTO>` to use for generating DTOs."""
    create_dto: type[AbstractDTO[ModelT]] | EmptyType = Empty
    """:class:`AbstractDTO <.dto.base_dto.AbstractDTO>` to use for create operations."""
    update_dto: type[AbstractDTO[ModelT]] | EmptyType = Empty
    """:class:`AbstractDTO <.dto.base_dto.AbstractDTO>` to use for update operations."""

    create_instance_handler_path: str | Sequence[str] = "/"
    """The path to the handler for create instance operations."""
    create_instance_operation_id: str = "create{model_name}"
    """The OpenAPI operation ID for create instance operations."""
    create_instance_http_method: HttpMethod = HttpMethod.POST
    """The HTTP method for create instance operations."""
    update_instance_handler_path: str | Sequence[str] = "/"
    """The path to the handler for update instance operations."""
    update_instance_operation_id: str = "update{model_name}"
    """The OpenAPI operation ID for update instance operations."""
    update_instance_http_method: HttpMethod = HttpMethod.PATCH
    """The HTTP method for update instance operations."""
    delete_instance_handler_path: str | Sequence[str] = "/{item_id:path_param_type}"
    """The path to the handler for delete instance operations."""
    delete_instance_operation_id: str = "delete{model_name}"
    """The OpenAPI operation ID for delete instance operations."""
    delete_instance_http_method: HttpMethod = HttpMethod.DELETE
    """The HTTP method for delete instance operations."""
    get_instance_handler_path: str | Sequence[str] = "/{item_id:path_param_type}"
    """The path to the handler for get instance operations."""
    get_instance_operation_id: str = "get{model_name}"
    """The OpenAPI operation ID for get instance operations."""
    get_instance_http_method: HttpMethod = HttpMethod.GET
    """The HTTP method for get instance operations."""

    create_many_handler_path: str | Sequence[str] = "/bulk-create"
    """The path to the handler for create many operations."""
    create_many_operation_id: str = "createMany{model_name}"
    """The OpenAPI operation ID for create many operations."""
    create_many_http_method: HttpMethod = HttpMethod.POST
    """The HTTP method for create many operations."""
    update_many_handler_path: str | Sequence[str] = "/bulk-update"
    """The path to the handler for update many operations."""
    update_many_operation_id: str = "updateMany{model_name}"
    """The OpenAPI operation ID for update many operations."""
    update_many_http_method: HttpMethod = HttpMethod.PATCH
    """The HTTP method for update many operations."""
    delete_many_handler_path: str | Sequence[str] = "/bulk-delete"
    """The path to the handler for delete many operations."""
    delete_many_operation_id: str = "deleteMany{model_name}"
    """The OpenAPI operation ID for delete many operations."""
    delete_many_http_method: HttpMethod = HttpMethod.DELETE
    """The HTTP method for delete many operations."""
    get_many_handler_path: str | Sequence[str] = "/"
    """The path to the handler for get many operations."""
    get_many_operation_id: str = "getMany{model_name}"
    """The OpenAPI operation ID for get many operations."""
    get_many_http_method: HttpMethod = HttpMethod.GET
    """The HTTP method for get many operations."""

    def __init__(self, owner: Router) -> None:
        """Initialize a controller.

        Should only be called by routers as part of controller registration.

        Args:
            owner: An instance of :class:`Router <.router.Router>`
        """
        super().__init__(owner=owner)

        if not getattr(self, "repository_type", None):
            raise ImproperlyConfiguredException("generic controllers must define a `repository_type` attribute")
        if not getattr(self, "instance_id_factory", None):
            raise ImproperlyConfiguredException("generic controllers must define a `instance_id_factory` attribute")

    def _normalize_annotation(self, key: str, annotation: Any) -> Any:
        if (origin := get_origin(annotation)) and (args := get_args(annotation)):
            safe_origin = get_safe_generic_origin(origin, origin)
            return safe_origin[tuple(self._normalize_annotation(key, arg) for arg in args)]
        if annotation is ModelT:  # type: ignore[misc]
            return self.model_type
        if key in {"item_id", "item_ids"} and annotation is Any:
            return self.id_attribute_type
        return annotation

    def get_route_handlers(self) -> list[BaseRouteHandler]:
        route_handlers = super().get_route_handlers()

        for method_name in GENERIC_METHOD_NAMES:
            method = getattr(self, method_name)
            if not isinstance(method, BaseRouteHandler):
                handler_path = getattr(self, f"{method_name}_handler_path")
                operation_id = getattr(self, f"{method_name}_operation_id")
                http_method = getattr(self, f"{method_name}_http_method")

                # we are replacing the generic parameters with the concrete types in the method `__annotations__`
                # this is required to ensure we model the signautre correctly, and generate the schemas as required.
                for k, v in get_type_hints(method, localns={"Request": Request}).items():
                    method.__annotations__[k] = self._normalize_annotation(k, v)

                data_dto: type[AbstractDTO] | EmptyType = Empty
                if http_method is HttpMethod.POST:
                    data_dto = self._create_dto
                elif http_method in {HttpMethod.PATCH, HttpMethod.PUT}:
                    data_dto = self._update_dto

                route_handler = HTTPRouteHandler(
                    handler_path.replace("path_param_type", self.path_param_type),
                    http_method=http_method,
                    operation_id=operation_id.replace("{model_name}", self.model_type.__name__),
                    signature_namespace={
                        self.model_type.__name__: self.model_type,
                        self.id_attribute_type.__name__: self.id_attribute_type,
                    },
                    dto=data_dto,
                    return_dto=self._return_dto,
                )(method)
                route_handler.owner = self
                route_handlers.append(route_handler)

        route_handlers.sort(key=attrgetter("handler_id"))
        return route_handlers

    @classmethod
    def get_generic_annotations(cls) -> tuple[Any, ...]:
        try:
            if (generic_bases := getattr(cls, "__orig_bases__", None)) and (
                args := next(
                    getattr(base, "__args__", ())
                    for base in generic_bases
                    if is_class_and_subclass(getattr(base, "__origin__", None), GenericController)
                )
            ):
                return cast("tuple[Any, ...]", args)
        except StopIteration:
            pass

        raise ImproperlyConfiguredException("generic controllers must receive a generic parameter for model type")

    @property
    def id_attribute_type(self) -> Any:
        try:
            return self.model_type.__annotations__[self.repository_type.id_attribute]
        except KeyError as e:
            raise ImproperlyConfiguredException(
                f"the configured `id_attribute` on the controller repository does not exist in model {self.model_type.__name__}"
            ) from e

    @property
    def model_type(self) -> type[ModelT]:
        return cast("type[ModelT]", self.get_generic_annotations()[0])

    @property
    def ownership_layers(self) -> list[Self | Router | Litestar]:
        """Return the layers from the app down to the generic controller handler.

        ``app -> ... -> generic controller``
        """
        layers: list[Self | Router | Litestar] = []

        cur: Self | Router | Litestar | None = self
        while cur:
            layers.append(cur)
            cur = cur.owner

        return list(reversed(layers))

    @cached_property
    def _create_dto(self) -> type[AbstractDTO[ModelT]]:
        if self.create_dto is not Empty:
            return cast("type[AbstractDTO[ModelT]]", self.create_dto)

        dto_type = self._dto_type[self.model_type]  # type: ignore[index]

        class _CreateDTO(dto_type):  # type: ignore[misc,valid-type]
            config = DTOConfig(exclude={self.repository_type.id_attribute}, partial=True)

        return _CreateDTO

    @cached_property
    def _update_dto(self) -> type[AbstractDTO[ModelT]]:
        if self.update_dto is not Empty:
            return cast("type[AbstractDTO[ModelT]]", self.update_dto)

        dto_type = self._dto_type[self.model_type]  # type: ignore[index]

        class _UpdateDTO(dto_type):  # type: ignore[misc,valid-type]
            config = DTOConfig(partial=True)

        return _UpdateDTO

    @cached_property
    def _return_dto(self) -> type[AbstractDTO[ModelT]] | None:
        if self.return_dto is not Empty:
            return cast("type[AbstractDTO[ModelT]] | None", self.return_dto)

        app = cast("Litestar", self.ownership_layers[0])
        if any(
            plugin.supports_type(FieldDefinition.from_annotation(self.model_type))
            for plugin in app.plugins.serialization
        ):
            # since there is a serialization plugin in place, a return dto type is not required.
            return None

        return cast("type[AbstractDTO[ModelT]]", self._dto_type[self.model_type])  # type: ignore[index]

    @cached_property
    def _dto_type(self) -> type[AbstractDTO]:
        if self.dto_type is not Empty:
            return cast("type[AbstractDTO]", self.dto_type)
        if is_dataclass(self.model_type):
            return DataclassDTO
        if is_struct_class(self.model_type):
            return MsgspecDTO
        if is_pydantic_model_class(self.model_type):
            from litestar.contrib.pydantic import PydanticDTO

            return PydanticDTO
        if is_piccolo_class(self.model_type):
            from litestar.contrib.piccolo import PiccoloDTO

            return PiccoloDTO
        if is_sqlalchemy_model(self.model_type):
            # FIX
            from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO

            return SQLAlchemyDTO

        if filtered_data_dtos := [
            layer.dto for layer in self.ownership_layers if layer.dto is not Empty and layer.dto is not None
        ]:
            return cast("type[AbstractDTO]", filtered_data_dtos[-1])

        raise ImproperlyConfiguredException(
            f"cannot determine DTO type for {self.model_type.__name__} on {type(self).__name__} "
            f"Generic Controller. Please specify a `dto_type` to have dtos automatically generated, or "
            f"specify the `create_dto`, `update_dto` and `return_dto` attributes to avoid dto generation.`"
        )

    @property
    def path_param_type(self) -> str:
        if self.id_attribute_type is str or is_class_and_subclass(self.id_attribute_type, str):
            return "str"
        if self.id_attribute_type is int or is_class_and_subclass(self.id_attribute_type, int):
            return "int"
        return "uuid"

    def create_repository(
        self, *, request: Request[Any, Any, Any], **kwargs: Any
    ) -> AbstractAsyncRepository[ModelT] | AbstractSyncRepository[ModelT]:
        kwargs["request"] = request
        return self.repository_type(**kwargs)

    async def create_instance(self, data: DTOData[ModelT], request: Request[Any, Any, Any]) -> ModelT:
        result = self.create_repository(request=request).add(
            data=data.create_instance(**{self.repository_type.id_attribute: self.instance_id_factory()})
        )
        if isawaitable(result):
            result = await result
        return cast("ModelT", result)

    async def update_instance(self, data: DTOData[ModelT], request: Request[Any, Any, Any]) -> ModelT:
        # TODO: formalize this
        id = data.as_builtins().get(self.repository_type.id_attribute, None)
        if not id:
            raise ValueError("can't find id")

        repo = self.create_repository(request=request)
        old_data = repo.get(id)
        if isawaitable(old_data):
            old_data = await old_data

        result = data.update_instance(old_data)
        if isawaitable(result):
            result = await result
        return cast("ModelT", result)

    async def delete_instance(self, item_id: Any, request: Request[Any, Any, Any]) -> None:
        result = self.create_repository(request=request).delete(item_id=item_id)
        if isawaitable(result):
            await result

    async def get_instance(self, item_id: Any, request: Request[Any, Any, Any]) -> ModelT:
        result = self.create_repository(request=request).get(item_id=item_id)
        if isawaitable(result):
            result = await result
        return cast("ModelT", result)

    async def create_many(self, data: List[DTOData[ModelT]], request: Request[Any, Any, Any]) -> List[ModelT]:
        result = self.create_repository(request=request).add_many(
            [datum.create_instance(**{self.repository_type.id_attribute: self.instance_id_factory()}) for datum in data]
        )
        if isawaitable(result):
            result = await result
        return cast("list[ModelT]", result)

    async def update_many(self, data: List[DTOData[ModelT]], request: Request[Any, Any, Any]) -> List[ModelT]:
        repo = self.create_repository(request=request)
        results = []
        for datum in data:
            # TODO: formalize this
            id = datum.as_builtins().get(self.repository_type.id_attribute, None)
            if not id:
                raise ValueError("can't find id")
            old_data = repo.get(id)
            if isawaitable(old_data):
                old_data = await old_data

            result = datum.update_instance(old_data)
            if isawaitable(result):
                result = await result

            results.append(result)
        return cast("list[ModelT]", results)

    async def delete_many(self, item_ids: List[Any], request: Request[Any, Any, Any]) -> None:
        result = self.create_repository(request=request).delete_many(item_ids=item_ids)
        if isawaitable(result):
            await result

    async def get_many(self, item_ids: List[Any], request: Request[Any, Any, Any]) -> List[ModelT]:
        result = self.create_repository(request=request).list(
            CollectionFilter(field_name=self.repository_type.id_attribute, values=item_ids)
        )
        if isawaitable(result):
            result = await result
        return cast("list[ModelT]", result)
