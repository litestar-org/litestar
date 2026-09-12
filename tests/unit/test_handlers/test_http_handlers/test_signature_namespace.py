from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from litestar import Controller, Router, delete, get, patch, post, put
from litestar.di import Provide
from litestar.params import FromQuery
from litestar.testing import create_test_client
from litestar.types import HTTPHandlerDecorator

if TYPE_CHECKING:
    # Imported under TYPE_CHECKING only, so the name is absent from this module's runtime
    # globals. Resolving it in a handler annotation therefore exercises the forward-ref
    # global namespace (regression for #4870).
    from litestar.di import NamedDependency


class _DIService:
    value = "provided"


async def _provide_di_service() -> _DIService:
    return _DIService()


@get("/di-name")
async def _named_dependency_handler(service: NamedDependency[_DIService]) -> dict[str, str]:
    return {"value": service.value}


def test_named_dependency_resolvable_in_type_checking_block() -> None:
    """Regression for #4870: ``NamedDependency`` must resolve when only imported under
    ``TYPE_CHECKING``, without the user having to pass it via ``signature_types``.

    ``NamedDependency`` is the alias ``Annotated[T, Dependency(kind="named")]``, whose
    ``__name__`` is ``"Annotated"`` -- so keying ``signature_types`` by ``__name__`` never
    made it resolvable under its own name.
    """
    with create_test_client(
        route_handlers=[_named_dependency_handler],
        dependencies={"service": Provide(_provide_di_service)},
    ) as client:
        assert client.get("/di-name").json() == {"value": "provided"}


@pytest.mark.parametrize(
    ("method", "decorator"),
    [
        ("GET", get),
        ("PUT", put),
        ("POST", post),
        ("PATCH", patch),
        ("DELETE", delete),
    ],
)
def test_websocket_signature_namespace(method: str, decorator: HTTPHandlerDecorator) -> None:
    class MyController(Controller):
        path = "/"
        signature_namespace = {"c": float}

        @decorator(path="/", signature_namespace={"d": list[str], "dict": dict}, status_code=200)
        async def simple_handler(
            self,
            a: FromQuery[a],  # type:ignore[name-defined]  # noqa: F821
            b: FromQuery[b],  # type:ignore[name-defined]  # noqa: F821
            c: FromQuery[c],  # type:ignore[name-defined]  # noqa: F821
            d: FromQuery[d],  # type:ignore[name-defined]  # noqa: F821
        ) -> dict[str, Any]:
            return {"a": a, "b": b, "c": c, "d": d}

    router = Router("/", route_handlers=[MyController], signature_namespace={"b": str})

    with create_test_client(route_handlers=[router], signature_namespace={"a": int}) as client:
        response = client.request(method=method, url="/?a=1&b=two&c=3.0&d=d")
        assert response.json() == {"a": 1, "b": "two", "c": 3.0, "d": ["d"]}
