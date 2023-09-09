# ruff: noqa: UP007, UP006
from __future__ import annotations

from inspect import isawaitable
from operator import attrgetter
from typing import TYPE_CHECKING, Any, Generic, List, Sequence, TypeVar, cast, get_args
from uuid import UUID

from typing_extensions import get_origin, get_type_hints

from litestar.connection.request import Request
from litestar.controller.base import Controller
from litestar.enums import HttpMethod
from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers import BaseRouteHandler, HTTPRouteHandler
from litestar.repository.filters import CollectionFilter
from litestar.types import Empty
from litestar.utils import is_class_and_subclass
from litestar.utils.typing import get_safe_generic_origin

if TYPE_CHECKING:
    from litestar.dto import AbstractDTO
    from litestar.repository import AbstractAsyncRepository, AbstractSyncRepository
    from litestar.types import EmptyType

ModelT = TypeVar("ModelT")
IdAttrT = TypeVar("IdAttrT", str, int, UUID)

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


class GenericController(Controller, Generic[ModelT, IdAttrT]):
    repository_type: type[AbstractAsyncRepository[ModelT]] | type[AbstractSyncRepository[ModelT]]
    """Repository for the controller's model."""
    id_attribute: str = "id"
    """The name of the models's ID attribute."""

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

    def _normalize_annotation(self, annotation: Any) -> Any:
        if (origin := get_origin(annotation)) and (args := get_args(annotation)):
            safe_origin = get_safe_generic_origin(origin, origin)
            return safe_origin[tuple(self._normalize_annotation(arg) for arg in args)]
        if annotation is ModelT:  # type: ignore[misc]
            return self.model_type
        return self.id_attribute_type if annotation is IdAttrT else annotation  # type: ignore[misc]

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
                    method.__annotations__[k] = self._normalize_annotation(v)

                route_handler = HTTPRouteHandler(
                    handler_path.replace("path_param_type", self.path_param_type),
                    http_method=http_method,
                    operation_id=operation_id.replace("{model_name}", self.model_type.__name__),
                    signature_namespace={
                        self.model_type.__name__: self.model_type,
                        self.id_attribute_type.__name__: self.id_attribute_type,
                    },
                )(method)
                route_handler.owner = self
                route_handlers.append(route_handler)

        route_handlers.sort(key=attrgetter("handler_id"))
        return route_handlers

    @classmethod
    def get_generic_annotations(cls) -> tuple[type, type]:
        try:
            if (generic_bases := getattr(cls, "__orig_bases__", None)) and (
                args := next(
                    getattr(base, "__args__", ())
                    for base in generic_bases
                    if is_class_and_subclass(getattr(base, "__origin__", None), GenericController)
                )
            ):
                return cast("tuple[type, type]", args)
        except StopIteration:
            pass

        raise ImproperlyConfiguredException(
            "generic controllers must be defined with two generic parameters - a model type and id attribute type"
        )

    @property
    def id_attribute_type(self) -> type[IdAttrT]:
        return cast("type[IdAttrT]", self.get_generic_annotations()[1])

    @property
    def model_type(self) -> type[ModelT]:
        return cast("type[ModelT]", self.get_generic_annotations()[0])

    @property
    def path_param_type(self) -> str:
        if self.id_attribute_type is str or is_class_and_subclass(self.id_attribute, str):
            return "str"
        if self.id_attribute_type is int or is_class_and_subclass(self.id_attribute, int):
            return "int"
        return "uuid"

    def create_repository(
        self, *, request: Request[Any, Any, Any], **kwargs: Any
    ) -> AbstractAsyncRepository[ModelT] | AbstractSyncRepository[ModelT]:
        kwargs["request"] = request
        return self.repository_type(**kwargs)

    async def create_instance(self, data: ModelT, request: Request[Any, Any, Any]) -> ModelT:
        result = self.create_repository(request=request).add(data=data)
        if isawaitable(result):
            result = await result
        return cast("ModelT", result)

    async def update_instance(self, data: ModelT, request: Request[Any, Any, Any]) -> ModelT:
        result = self.create_repository(request=request).update(data=data)
        if isawaitable(result):
            result = await result
        return cast("ModelT", result)

    async def delete_instance(self, item_id: IdAttrT, request: Request[Any, Any, Any]) -> None:
        result = self.create_repository(request=request).delete(item_id=item_id)
        if isawaitable(result):
            await result

    async def get_instance(self, item_id: IdAttrT, request: Request[Any, Any, Any]) -> ModelT:
        result = self.create_repository(request=request).get(item_id=item_id)
        if isawaitable(result):
            result = await result
        return cast("ModelT", result)

    async def create_many(self, data: List[ModelT], request: Request[Any, Any, Any]) -> List[ModelT]:
        result = self.create_repository(request=request).add_many(data)
        if isawaitable(result):
            result = await result
        return cast("list[ModelT]", result)

    async def update_many(self, data: List[ModelT], request: Request[Any, Any, Any]) -> List[ModelT]:
        result = self.create_repository(request=request).update_many(data=data)
        if isawaitable(result):
            result = await result
        return cast("list[ModelT]", result)

    async def delete_many(self, item_ids: List[IdAttrT], request: Request[Any, Any, Any]) -> None:
        result = self.create_repository(request=request).delete_many(item_ids=item_ids)
        if isawaitable(result):
            await result

    async def get_many(self, item_ids: List[IdAttrT], request: Request[Any, Any, Any]) -> List[ModelT]:
        result = self.create_repository(request=request).list(
            CollectionFilter(field_name=self.id_attribute, values=item_ids)
        )
        if isawaitable(result):
            result = await result
        return cast("list[ModelT]", result)
