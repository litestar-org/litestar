from __future__ import annotations

import atexit
import importlib.util
import inspect
import logging
import random
import sys
from collections.abc import Awaitable, Generator, Iterator, Sequence
from contextlib import AbstractAsyncContextManager, AbstractContextManager, contextmanager
from pathlib import Path
from typing import Any, TypeVar, cast, overload

from _pytest.logging import LogCaptureHandler, _LiveLoggingNullHandler

from litestar import Litestar, post
from litestar._openapi.datastructures import OpenAPIContext
from litestar._openapi.schema_generation import SchemaCreator
from litestar._openapi.schema_generation.library import SchemaMode
from litestar._openapi.schema_generation.plugins import openapi_schema_plugins
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import Reference, Schema
from litestar.plugins import OpenAPISchemaPlugin
from litestar.typing import FieldDefinition

T = TypeVar("T")

PREFIX = "#/components/schemas/"

RANDOM = random.Random(b"bA\xcd\x00\xa9$\xa7\x17\x1c\x10")


if sys.version_info >= (3, 12):
    getHandlerByName = logging.getHandlerByName
else:
    from logging import _handlers  # type: ignore[attr-defined]

    def getHandlerByName(name: str) -> Any:
        return _handlers.get(name)


@overload
async def maybe_async(obj: Awaitable[T]) -> T: ...


@overload
async def maybe_async(obj: T) -> T: ...


async def maybe_async(obj: Awaitable[T] | T) -> T:
    return await obj if inspect.isawaitable(obj) else obj  # pyright: ignore[reportReturnType]


class _AsyncContextManagerWrapper(AbstractAsyncContextManager):
    def __init__(self, cm: AbstractContextManager):
        self.cm = cm

    async def __aenter__(self) -> Any:
        return self.cm.__enter__()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
        return self.cm.__exit__(exc_type, exc_val, exc_tb)


def maybe_async_cm(obj: AbstractContextManager[T] | AbstractAsyncContextManager[T]) -> AbstractAsyncContextManager[T]:
    if isinstance(obj, AbstractContextManager):
        return cast(AbstractAsyncContextManager[T], _AsyncContextManagerWrapper(obj))
    return obj


def get_components_for_field_definition(
    field_definition: FieldDefinition,
    *,
    plugins: list[OpenAPISchemaPlugin] | None = None,
    schema_mode: SchemaMode = "validation",
) -> tuple[Schema | Reference, dict[str, Schema]]:
    context = OpenAPIContext(
        openapi_config=OpenAPIConfig(title="test", version="1.0.0"),
        plugins=[*openapi_schema_plugins, *(plugins or [])],
    )
    creator = SchemaCreator.from_openapi_context(context, schema_mode=schema_mode)
    result = creator.for_field_definition(field_definition)
    context.schema_registry.library.resolve(context)
    components = context.schema_registry.generate_components_schemas()
    context.schema_registry.library.point_references((result, components))
    return result, components


def get_schema_for_field_definition(
    field_definition: FieldDefinition, *, plugins: list[OpenAPISchemaPlugin] | None = None, library_models: bool = True
) -> Schema:
    creator = SchemaCreator(plugins=[*openapi_schema_plugins, *(plugins or [])], library_models=library_models)
    result = creator.for_field_definition(field_definition)
    if isinstance(result, Schema):
        return result
    if creator.schema_registry.library.is_placeholder(result):
        root, components = get_components_for_field_definition(field_definition, plugins=plugins)
        assert isinstance(root, Reference)
        return components[root.ref.rsplit("/", 1)[-1]]
    return creator.schema_registry.from_reference(result).schema


def document(handlers: list[Any], plugins: Sequence[Any] = (), **config: Any) -> dict[str, Any]:
    app = Litestar(handlers, plugins=list(plugins), openapi_config=OpenAPIConfig(title="t", version="1", **config))
    return app.openapi_schema.to_schema()


def body_schema(doc: dict[str, Any], path: str = "/") -> Any:
    return doc["paths"][path]["post"]["requestBody"]["content"]["application/json"]["schema"]


def response_schema(doc: dict[str, Any], path: str = "/", method: str = "post", status: str | None = None) -> Any:
    status = status or ("201" if method == "post" else "200")
    return doc["paths"][path][method]["responses"][status]["content"]["application/json"]["schema"]


def components(doc: dict[str, Any]) -> dict[str, Any]:
    return cast("dict[str, Any]", doc["components"]["schemas"])


_VERBATIM_KEYS = {"default", "examples", "example", "enum", "const", "required", "dependentRequired"}


def normalise_json_schema(node: Any) -> Any:
    if isinstance(node, list):
        return [normalise_json_schema(value) for value in node]
    if not isinstance(node, dict):
        return node
    node = {key: value for key, value in node.items() if not (key == "default" and value is None)}
    if node.get("items") is False and "prefixItems" in node and node.get("maxItems") == len(node["prefixItems"]):
        del node["items"]
    if "$ref" in node and len(node) > 1:
        node["allOf"] = [{"$ref": node.pop("$ref")}, *node.get("allOf", [])]
    return {key: value if key in _VERBATIM_KEYS else normalise_json_schema(value) for key, value in node.items()}


@contextmanager
def recursion_limit(limit: int) -> Iterator[None]:
    original = sys.getrecursionlimit()
    sys.setrecursionlimit(limit)
    try:
        yield
    finally:
        sys.setrecursionlimit(original)


class Wrapping(OpenAPISchemaPlugin):
    def __init__(self, inner: OpenAPISchemaPlugin, claimed: Any) -> None:
        self.inner = inner
        self.claimed = claimed

    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.annotation is self.claimed

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema | Reference:
        return self.inner.to_openapi_schema(field_definition, schema_creator)


def route(body: Any, response: Any, path: str = "/") -> Any:
    def handler(data: Any) -> Any:
        return None

    handler.__annotations__ = {"data": body, "return": response}
    return post(path, sync_to_thread=False)(handler)


@contextmanager
def cleanup_logging_impl() -> Generator:
    # Reset root logger (`logging` module)
    std_root_logger: logging.Logger = logging.getLogger()
    for std_handler in std_root_logger.handlers:
        # Don't interfere with PyTest handler config
        if not isinstance(std_handler, (_LiveLoggingNullHandler, LogCaptureHandler)):
            std_root_logger.removeHandler(std_handler)

    yield

    # Stop queue_listener listener (mandatory for the 'logging' module with Python 3.12,
    # else the test suite would hang on at the end of the tests and some tests would fail)
    queue_listener_handler = getHandlerByName("queue_listener")
    if queue_listener_handler and hasattr(queue_listener_handler, "listener"):
        atexit.unregister(queue_listener_handler.listener.stop)
        queue_listener_handler.listener.stop()
        queue_listener_handler.close()
        del queue_listener_handler


def not_none(val: T | None) -> T:
    assert val is not None
    return val


def purge_module(module_names: list[str], path: str | Path) -> None:
    for name in module_names:
        if name in sys.modules:
            del sys.modules[name]
    Path(importlib.util.cache_from_source(path)).unlink(missing_ok=True)
