from __future__ import annotations

import re
import traceback
from collections.abc import Callable, Generator
from dataclasses import dataclass, make_dataclass
from typing import TYPE_CHECKING, Annotated, Any, Optional, Union, cast

import msgspec
import pytest
from msgspec import Meta

from litestar import Litestar, get, post, websocket_listener
from litestar._layers.errors import HandlerErrorPrefix
from litestar.dto import DataclassDTO, DTOConfig, DTOData, DTOFieldDefinition, MsgspecDTO
from litestar.dto._plan import create_dto_openapi_schema
from litestar.exceptions import (
    DTOFactoryException,
    DTOTransferTypeError,
    ImproperlyConfiguredException,
    InvalidAnnotationException,
    LitestarDeprecationWarning,
    MissingDTOError,
)
from litestar.handlers import WebsocketListener
from litestar.params import JSONBody
from litestar.testing import create_test_client
from litestar.typing import FieldDefinition
from tests.helpers import not_none
from tests.unit.test_dto import registered

if TYPE_CHECKING:
    from litestar._openapi.schema_generation import SchemaCreator


@dataclass
class User:
    id: int
    name: str


@dataclass
class Rejected:
    f: Annotated[Optional[str], Meta(min_length=5)] = None


class RejectedStruct(msgspec.Struct):
    f: Annotated[Optional[str], Meta(min_length=5)] = None


@dataclass
class U1:
    a: int


@dataclass
class U2:
    b: int


@dataclass
class UnionHolder:
    f: Union[U1, U2]


class HookError(DTOFactoryException):
    def __init__(self, message: str, *, code: int) -> None:
        super().__init__(message)
        self.code = code


class HookErrorDTO(DataclassDTO[User]):
    @classmethod
    def generate_field_definitions(cls, model_type: type[Any]) -> Generator[DTOFieldDefinition, None, None]:
        raise HookError("hook failed", code=7)


class RuntimeErrorDTO(DataclassDTO[User]):
    @classmethod
    def generate_field_definitions(cls, model_type: type[Any]) -> Generator[DTOFieldDefinition, None, None]:
        raise RuntimeError("boom")


class OwnDecodingDTO(DataclassDTO[UnionHolder]):
    def decode_bytes(self, value: bytes) -> Any:
        raw = msgspec.json.decode(value)
        return UnionHolder(f=U1(**raw["f"]) if "a" in raw["f"] else U2(**raw["f"]))


def test_missing_dto_error_bases() -> None:
    error = MissingDTOError("no DTO", annotation=DTOData[User])

    assert str(error) == "no DTO"
    assert isinstance(error, ImproperlyConfiguredException)
    assert isinstance(error, DTOFactoryException)
    assert isinstance(error, ValueError)
    assert error.annotation == DTOData[User]
    assert issubclass(DTOTransferTypeError, InvalidAnnotationException)


def test_dto_data_without_dto_raises_missing_dto_error_with_prefix() -> None:
    @post("/")
    async def handler(data: JSONBody[DTOData[User]]) -> None: ...

    with pytest.raises(MissingDTOError) as exc_info:
        Litestar([handler], openapi_config=None)

    assert str(exc_info.value) == (
        f"[paths='/', handler='handler'] The data it receives is annotated "
        f"'litestar.dto.data_structures.DTOData[{__name__}.User]', but no DTO decodes it. Declare 'dto=' on the "
        "handler with a DTO that handles the model."
    )
    assert exc_info.value.annotation == DTOData[User]


def test_listener_function_dto_data_without_dto_raises_at_startup() -> None:
    @websocket_listener("/ws")
    async def listener(data: DTOData[User]) -> None: ...

    with pytest.raises(
        MissingDTOError,
        match=r"^\[paths='/ws', handler='listener'\] The data it receives is annotated ",
    ):
        Litestar([listener], openapi_config=None)


def test_listener_class_dto_data_without_dto_raises_at_startup() -> None:
    class Listener(WebsocketListener):
        path = "/ws"

        async def on_receive(self, data: DTOData[User]) -> None: ...

    with pytest.raises(
        MissingDTOError,
        match=r"^\[paths='/ws', handler='Listener'\] The data it receives is annotated ",
    ):
        Litestar([Listener], openapi_config=None)


def test_inapplicable_data_dto_error_carries_handler_prefix() -> None:
    @post("/items", dto=DataclassDTO[User], return_dto=None)
    async def create(data: JSONBody[dict[str, Any]]) -> None: ...

    with pytest.raises(InvalidAnnotationException, match=r"^\[paths='/items', handler='create'\] "):
        Litestar([create], openapi_config=None)


def test_prefix_uses_handler_name_option() -> None:
    @post("/", name="create-user", dto=DataclassDTO[User], return_dto=None)
    async def create(data: JSONBody[dict[str, Any]]) -> None: ...

    with pytest.raises(InvalidAnnotationException, match=r"^\[paths='/', handler='create-user'\] "):
        Litestar([create], openapi_config=None)


def test_prefix_lists_paths_sorted() -> None:
    @post(["/b", "/a"], dto=DataclassDTO[User], return_dto=None)
    async def create(data: JSONBody[dict[str, Any]]) -> None: ...

    with pytest.raises(InvalidAnnotationException, match=r"^\[paths='/a,/b', handler='create'\] "):
        Litestar([create], openapi_config=None)


def test_third_party_dto_exception_keeps_type_attributes_and_traceback() -> None:
    @post("/", dto=HookErrorDTO, return_dto=None)
    async def create(data: JSONBody[User]) -> None: ...

    with pytest.raises(HookError) as exc_info:
        Litestar([create], openapi_config=None)

    assert type(exc_info.value) is HookError
    assert exc_info.value.code == 7
    assert str(exc_info.value) == "[paths='/', handler='create'] hook failed"
    assert "generate_field_definitions" in [frame.name for frame in traceback.extract_tb(exc_info.value.__traceback__)]


def test_non_dto_exception_is_not_wrapped() -> None:
    @post("/", dto=RuntimeErrorDTO, return_dto=None)
    async def create(data: JSONBody[User]) -> None: ...

    with pytest.raises(RuntimeError, match="^boom$"):
        Litestar([create], openapi_config=None)


def _rejected_dataclass_data() -> Any:
    @post("/", dto=DataclassDTO[Rejected], return_dto=None)
    async def create(data: JSONBody[Rejected]) -> None: ...

    return create


def _rejected_struct_data() -> Any:
    @post("/", dto=MsgspecDTO[RejectedStruct], return_dto=None)
    async def create(data: JSONBody[RejectedStruct]) -> None: ...

    return create


def _rejected_struct_return() -> Any:
    @get("/", return_dto=MsgspecDTO[RejectedStruct])
    async def create() -> RejectedStruct:
        return RejectedStruct()

    return create


def _union_of_models_data() -> Any:
    @post("/", dto=DataclassDTO[UnionHolder], return_dto=None)
    async def create(data: JSONBody[UnionHolder]) -> None: ...

    return create


@pytest.mark.parametrize(
    ("make_handler", "match"),
    [
        pytest.param(_rejected_dataclass_data, "msgspec cannot decode .*min_length", id="dataclass-data"),
        pytest.param(_rejected_struct_data, "msgspec cannot inspect .*min_length", id="msgspec-data"),
        pytest.param(_rejected_struct_return, "msgspec cannot inspect .*min_length", id="msgspec-return"),
        pytest.param(_union_of_models_data, "msgspec cannot decode .*must be tagged", id="union-of-models-data"),
    ],
)
def test_rejected_transfer_type_raises_dto_transfer_type_error(make_handler: Any, match: str) -> None:
    with pytest.raises(DTOTransferTypeError, match=rf"^\[paths='/', handler='create'\] {match}") as exc_info:
        Litestar([make_handler()], openapi_config=None)

    assert isinstance(exc_info.value.__cause__, TypeError)


@dataclass
class RejectedInner:
    g: Annotated[Optional[str], Meta(min_length=5)] = None


@dataclass
class RejectedOuter:
    inner: RejectedInner


CONSTRAINT_HINT = "attach the constraint to the member type it applies to, e.g. Optional[Annotated[str, Meta(...)]]"
_REJECTED_FIELD_CASES = [
    *(
        pytest.param(
            make_dataclass("Model", [("f", annotation)]), "Model", "f", annotation, CONSTRAINT_HINT, id=case_id
        )
        for case_id, annotation in (
            ("optional-meta", Annotated[Optional[str], Meta(min_length=5)]),
            ("int-meta", Annotated[int, Meta(min_length=1)]),
            ("item-meta", list[Annotated[int, Meta(min_length=1)]]),
        )
    ),
    pytest.param(
        RejectedOuter,
        "RejectedInner",
        "g",
        Annotated[Optional[str], Meta(min_length=5)],
        CONSTRAINT_HINT,
        id="nested-field",
    ),
    pytest.param(
        UnionHolder, "UnionHolder", "f", Union[U1, U2], "tag the union members or decode the body yourself", id="union"
    ),
]


@pytest.mark.parametrize("partial", [False, True])
@pytest.mark.parametrize(("model", "owner", "field_name", "annotation", "hint"), _REJECTED_FIELD_CASES)
def test_startup_error_names_the_rejected_field_and_a_hint(
    model: Any, owner: str, field_name: str, annotation: Any, hint: str, partial: bool
) -> None:
    async def create(data: Any) -> None: ...

    create.__annotations__ = {"data": JSONBody[model], "return": None}
    handler = post("/", dto=DataclassDTO[Annotated[model, DTOConfig(partial=partial)]], return_dto=None)(create)

    with pytest.raises(DTOTransferTypeError) as exc_info:
        Litestar([handler], openapi_config=None)

    assert re.fullmatch(
        re.escape(
            f"[paths='/', handler='create'] msgspec cannot decode the transfer model of '{__name__}.{model.__name__}': "
            f"field '{field_name}' of '{__name__}.{owner}', annotated {annotation!r}, is rejected by msgspec ("
        )
        + r"[^;]+"
        + re.escape(f"); {hint}"),
        str(exc_info.value),
    )
    assert isinstance(exc_info.value.__cause__, TypeError)


def test_return_only_dto_rejected_by_msgspec_starts_and_serves() -> None:
    @get("/", return_dto=DataclassDTO[Rejected])
    async def read() -> Rejected:
        return Rejected(f="12")

    with create_test_client([read]) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"f": "12"}
        assert client.get("/schema/openapi.json").status_code == 200


def test_return_only_dto_over_union_of_models_raises_typed_error_on_schema_generation() -> None:
    @get("/union", return_dto=DataclassDTO[UnionHolder])
    async def read_union() -> UnionHolder:
        return UnionHolder(f=U2(b=1))

    with create_test_client([read_union], raise_server_exceptions=False) as client:
        response = client.get("/union")
        assert response.status_code == 200
        assert response.json() == {"f": {"b": 1}}
        with pytest.raises(
            DTOTransferTypeError,
            match=rf"^\[paths='/union', handler='read_union'\] msgspec cannot describe the transfer model of "
            rf"'{__name__}.UnionHolder': .*must be tagged",
        ) as exc_info:
            client.app.openapi_schema
        assert isinstance(exc_info.value.__cause__, TypeError)
        assert client.get("/schema/openapi.json").status_code == 500


def test_dto_overriding_decode_bytes_is_checked_at_startup() -> None:
    @post("/", dto=OwnDecodingDTO, return_dto=None)
    async def create(data: JSONBody[UnionHolder]) -> None: ...

    with pytest.raises(DTOTransferTypeError, match="must be tagged"):
        Litestar([create], openapi_config=None)


def test_unrelated_type_error_in_schema_generation_is_not_converted() -> None:
    class RaisingSchemaCreator:
        def for_field_definition(self, field_definition: FieldDefinition) -> Any:
            raise TypeError("unrelated")

    @get("/", return_dto=DataclassDTO[User])
    async def read() -> User:
        return User(id=1, name="a")

    app = Litestar([read], openapi_config=None)
    handler = registered(app, method="GET")
    direction_plan = not_none(not_none(handler._dto_plan).return_)
    schema_creator = cast("SchemaCreator", RaisingSchemaCreator())

    with pytest.raises(TypeError, match="^unrelated$") as exc_info:
        create_dto_openapi_schema(direction_plan, handler.parsed_return_field, handler, schema_creator)

    assert type(exc_info.value) is TypeError


MISSING_DTO_MESSAGE = "The data it receives is annotated 'DTOData[User]', but no DTO decodes it."


@pytest.mark.parametrize(
    ("make_error", "expected_str", "expected_args"),
    [
        pytest.param(
            lambda: MissingDTOError(MISSING_DTO_MESSAGE, annotation=DTOData[User]),
            f"[paths='/', handler='h'] {MISSING_DTO_MESSAGE}",
            (f"500: [paths='/', handler='h'] {MISSING_DTO_MESSAGE}",),
            id="http-exception",
        ),
        pytest.param(lambda: DTOFactoryException("bad"), "[paths='/', handler='h'] bad", (), id="dto-exception"),
        pytest.param(DTOFactoryException, "[paths='/', handler='h']", (), id="empty-detail"),
    ],
)
def test_wrap_dto_exception_prefixes_http_exception_once(
    make_error: Callable[[], DTOFactoryException], expected_str: str, expected_args: tuple[str, ...]
) -> None:
    error = make_error()

    with (
        pytest.raises(DTOFactoryException) as exc_info,
        HandlerErrorPrefix(handler="h", paths=["/"]).wrap_dto_exception(),
    ):
        raise error

    assert exc_info.value is error
    assert type(error) is type(make_error())
    assert str(error) == expected_str
    assert error.detail.startswith("[paths='/', handler='h']")
    assert error.args == expected_args


def test_wrap_dto_exception_leaves_other_exceptions() -> None:
    error = ImproperlyConfiguredException("bad")

    with (
        pytest.raises(ImproperlyConfiguredException) as exc_info,
        HandlerErrorPrefix(handler="h", paths=["/"]).wrap_dto_exception(),
    ):
        raise error

    assert exc_info.value is error
    assert str(error) == "500: bad"


def test_startup_error_names_the_handler_once() -> None:
    with pytest.raises(DTOTransferTypeError) as exc_info:
        Litestar([_union_of_models_data()], openapi_config=None)

    assert "(handler " not in str(exc_info.value)
    assert str(exc_info.value).count("create") == 1


def test_deprecated_direct_backend_creation_names_the_handler_id() -> None:
    with pytest.warns(LitestarDeprecationWarning), pytest.raises(DTOTransferTypeError) as exc_info:
        DataclassDTO[UnionHolder].create_for_field_definition(
            FieldDefinition.from_annotation(JSONBody[UnionHolder]), "pkg.create::1"
        )

    assert str(exc_info.value).endswith("(handler 'pkg.create::1')")
