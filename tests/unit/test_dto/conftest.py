from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any, TypeVar, get_type_hints

import pytest

from litestar import Request, get
from litestar.dto import AbstractDTO, DTOField, DTOFieldDefinition
from litestar.enums import MediaType
from litestar.testing import RequestFactory
from litestar.typing import FieldDefinition

from . import Model

T = TypeVar("T", bound=Model)


@pytest.fixture
def int_factory() -> Callable[[], int]:
    return lambda: 2


@pytest.fixture
def ModelDataDTO() -> type[AbstractDTO]:
    class DTOCls(AbstractDTO[Model]):
        @classmethod
        def generate_field_definitions(cls, model_type: type[Any]) -> Generator[DTOFieldDefinition, None, None]:
            for k, v in get_type_hints(model_type).items():
                yield DTOFieldDefinition.from_field_definition(
                    field_definition=FieldDefinition.from_kwarg(annotation=v, name=k),
                    model_name="Model",
                    default_factory=None,
                    dto_field=DTOField(),
                )

        @classmethod
        def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
            return False

    return DTOCls


@pytest.fixture()
def ModelReturnDTO() -> type[AbstractDTO]:
    class ReturnDO(AbstractDTO[Model]):
        @classmethod
        def generate_field_definitions(cls, model_type: type[Any]) -> Generator[DTOFieldDefinition, None, None]:
            for k, v in get_type_hints(model_type).items():
                yield DTOFieldDefinition.from_field_definition(
                    field_definition=FieldDefinition.from_kwarg(annotation=v, name=k),
                    model_name="Model",
                    default_factory=None,
                    dto_field=DTOField(),
                )

        @classmethod
        def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
            return False

    return ReturnDO


@pytest.fixture()
def asgi_connection() -> Request[Any, Any, Any]:
    @get("/", name="handler_id", media_type=MediaType.JSON)
    def _handler() -> None: ...

    return RequestFactory().get(path="/", route_handler=_handler)
