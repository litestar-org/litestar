# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, make_dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from types import ModuleType
from typing import TYPE_CHECKING, Annotated, Generic, Literal, Optional, TypeVar, Union, cast

import annotated_types
import msgspec
import pytest
from msgspec import UNSET, Meta, Struct, UnsetType
from typing_extensions import TypeAliasType as TeTypeAliasType

from litestar import Controller, Litestar, Response, get, patch, post
from litestar.connection.request import Request
from litestar.datastructures import UploadFile
from litestar.dto import DataclassDTO, DTOConfig, DTOData, DTOField, MsgspecDTO, dto_field
from litestar.enums import MediaType
from litestar.exceptions import DTOTransferTypeError, InvalidAnnotationException
from litestar.params import JSONBody, MultipartBody, QueryParameter, URLEncodedBody
from litestar.serialization import encode_json
from litestar.testing import create_test_client
from tests.helpers import not_none

try:
    from typing import TypeAliasType  # type: ignore[attr-defined]
except ImportError:
    TypeAliasType = TeTypeAliasType

if TYPE_CHECKING:
    from typing import Any


def test_url_encoded_form_data() -> None:
    @dataclass()
    class User:
        name: str
        age: int
        read_only: str = field(default="read-only", metadata=dto_field("read-only"))

    class UserDTO(DataclassDTO[User]):
        pass

    @post(dto=UserDTO, signature_types=[User])
    def handler(data: URLEncodedBody[User]) -> User:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post(
            "/",
            content=b"id=1&name=John&age=42&read_only=whoops",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.json() == {"name": "John", "age": 42, "read_only": "read-only"}


async def test_multipart_encoded_form_data() -> None:
    default_file = UploadFile(content_type="text/plain", filename="forbidden", file_data=b"forbidden")

    @dataclass
    class Payload:
        file: UploadFile
        forbidden: UploadFile = field(
            default=default_file,
            metadata=dto_field("read-only"),
        )

    class PayloadDTO(DataclassDTO[Payload]):
        pass

    @post(dto=PayloadDTO, return_dto=None, signature_types=[Payload], media_type=MediaType.TEXT)
    async def handler(data: MultipartBody[Payload]) -> bytes:
        return await data.forbidden.read()

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post(
            "/",
            files={"file": b"abc123", "forbidden": b"123abc"},
        )
        assert response.content == b"forbidden"

    await default_file.close()


def test_renamed_field_nested(create_module: Callable[[str], ModuleType]) -> None:
    # https://github.com/litestar-org/litestar/issues/2721
    module = create_module(
        """
from dataclasses import dataclass
from typing import List

@dataclass
class Bar:
    id: str

@dataclass
class Foo:
    id: str
    bar: Bar
    bars: list[Bar]
"""
    )

    Foo = module.Foo

    config = DTOConfig(
        rename_fields={"id": "foo_id", "bar.id": "bar_id", "bars.0.id": "bars_id"},
    )
    dto = DataclassDTO[Annotated[Foo, config]]  # type: ignore[valid-type]

    @post(dto=dto, signature_types=[Foo])
    def handler(data: JSONBody[Foo]) -> Foo:  # type: ignore[valid-type]
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"foo_id": "1", "bar": {"bar_id": "2"}, "bars": [{"bars_id": "3"}]})
        assert response.json() == {"foo_id": "1", "bar": {"bar_id": "2"}, "bars": [{"bars_id": "3"}]}


def test_dto_data_injection() -> None:
    @dataclass
    class Foo:
        bar: str

    @post(dto=DataclassDTO[Foo], return_dto=None, signature_types=[Foo])
    def handler(data: JSONBody[DTOData[Foo]]) -> Foo:
        assert isinstance(data, DTOData)
        assert data.as_builtins() == {"bar": "hello"}
        assert isinstance(data.create_instance(), Foo)
        return data.create_instance()

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"bar": "hello"})
        assert response.json() == {"bar": "hello"}


@dataclass
class NestedFoo:
    bar: str
    baz: str


@dataclass
class NestingBar:
    foo: NestedFoo


def test_dto_data_injection_with_nested_model() -> None:
    @post(
        dto=DataclassDTO[Annotated[NestingBar, DTOConfig(exclude={"foo.baz"})]],
        return_dto=None,
    )
    def handler(data: JSONBody[DTOData[NestingBar]]) -> dict[str, Any]:
        assert isinstance(data, DTOData)
        return cast("dict[str, Any]", data.as_builtins())

    with create_test_client(route_handlers=[handler]) as client:
        resp = client.post("/", json={"foo": {"bar": "hello"}})
        assert resp.status_code == 201
        assert resp.json() == {"foo": {"bar": "hello"}}


def test_dto_data_create_instance_nested_kwargs() -> None:
    @post(
        dto=DataclassDTO[Annotated[NestingBar, DTOConfig(exclude={"foo.baz"})]],
        return_dto=None,
    )
    def handler(data: JSONBody[DTOData[NestingBar]]) -> NestingBar:
        assert isinstance(data, DTOData)
        result = data.create_instance(foo__baz="world")
        assert result.foo.baz == "world"
        return result

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"foo": {"bar": "hello"}})
        assert response.status_code == 201
        assert response.json() == {"foo": {"bar": "hello", "baz": "world"}}


@dataclass
class TupleItem:
    bar: str
    baz: str = "secret"


@dataclass
class TupleNestingBar:
    foo: tuple[TupleItem, int]


def test_dto_nested_model_in_fixed_length_tuple() -> None:
    @post(dto=DataclassDTO[Annotated[TupleNestingBar, DTOConfig(exclude={"foo.0.baz"})]])
    def handler(data: JSONBody[TupleNestingBar]) -> TupleNestingBar:
        assert isinstance(data.foo[0], TupleItem)
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"foo": [{"bar": "hello"}, 1]})
        assert response.status_code == 201
        assert response.json() == {"foo": [{"bar": "hello"}, 1]}


@dataclass
class Dog:
    id: int
    nick_name: str
    secret: str = field(default="s", metadata=dto_field("private"))
    _hidden: str = "h"


@dataclass
class Cat:
    id: int
    color: str


@dataclass
class Person:
    id: int
    name: str
    pets: tuple[Dog, Cat]


def test_dto_fixed_length_tuple_excludes_and_renames_nested_fields() -> None:
    received: dict[str, Person] = {}

    @get(
        "/",
        return_dto=DataclassDTO[
            Annotated[Person, DTOConfig(exclude={"id", "pets.0.id", "pets.1.id"}, rename_strategy="camel")]
        ],
    )
    def read_person() -> Person:
        return Person(id=1, name="John", pets=(Dog(id=2, nick_name="Dog"), Cat(id=3, color="White")))

    @post(
        "/",
        dto=DataclassDTO[Annotated[Person, DTOConfig(rename_fields={"pets.0.nick_name": "nn"})]],
        return_dto=None,
    )
    def write_person(data: JSONBody[Person]) -> None:
        received["data"] = data

    with create_test_client(route_handlers=[read_person, write_person]) as client:
        response = client.get("/")
        assert response.json() == {"name": "John", "pets": [{"nickName": "Dog"}, {"color": "White"}]}

        response = client.post(
            "/", json={"id": 1, "name": "n", "pets": [{"id": 7, "nn": "d"}, {"id": 8, "color": "c"}]}
        )
        assert response.status_code == 201
        assert received["data"].pets == (Dog(id=7, nick_name="d"), Cat(id=8, color="c"))


@dataclass
class Deep2:
    y: int


@dataclass
class Deep:
    x: int
    inner: Optional[Deep2] = None


@dataclass
class Holder:
    t: tuple[Deep, int]


@pytest.mark.parametrize(
    "max_nested_depth, expected",
    [
        (0, {}),
        (1, {"t": [{"x": 1}, 5]}),
        (2, {"t": [{"x": 1, "inner": {"y": 2}}, 5]}),
    ],
)
def test_dto_fixed_length_tuple_respects_max_nested_depth(max_nested_depth: int, expected: dict[str, Any]) -> None:
    @get("/", return_dto=DataclassDTO[Annotated[Holder, DTOConfig(max_nested_depth=max_nested_depth)]])
    def read_holder() -> Holder:
        return Holder(t=(Deep(x=1, inner=Deep2(y=2)), 5))

    with create_test_client(route_handlers=[read_holder]) as client:
        assert client.get("/").json() == expected


@dataclass
class Holder2:
    u: Union[tuple[Deep2, int], None] = None
    lt: list[tuple[Deep2, str]] = field(default_factory=list)


@pytest.mark.parametrize(
    "value, expected",
    [
        (Holder2(u=(Deep2(y=3), 4), lt=[(Deep2(y=9), "a")]), {"u": [{}, 4], "lt": [[{}, "a"]]}),
        (Holder2(), {"u": None, "lt": []}),
    ],
)
def test_dto_fixed_length_tuple_inside_union_and_list(value: Holder2, expected: dict[str, Any]) -> None:
    @get("/", return_dto=DataclassDTO[Annotated[Holder2, DTOConfig(exclude={"u.0.0.y", "lt.0.0.y"})]])
    def read_holder2() -> Holder2:
        return value

    with create_test_client(route_handlers=[read_holder2]) as client:
        assert client.get("/").json() == expected


@dataclass
class PathAddress:
    street: str
    city: str


@dataclass
class OptionalPathPerson:
    work: Optional[PathAddress] = None
    home: None | PathAddress = None
    homes: Optional[list[PathAddress]] = None
    either: Union[PathAddress, int, None] = None


@pytest.mark.parametrize(
    "config, work, home, homes, either",
    [
        pytest.param(
            {"exclude": {"work.street", "home.street"}}, {"city": "c"}, {"city": "c"}, None, None, id="exclude"
        ),
        pytest.param({"exclude": {"homes.0.street"}}, None, None, [{"city": "c"}], None, id="exclude-optional-list"),
        pytest.param(
            {"exclude": {"work.0.street", "homes.0.0.street"}}, {"city": "c"}, None, [{"city": "c"}], None, id="index"
        ),
        pytest.param(
            {"include": {"work.city", "home", "homes", "either"}}, {"city": "c"}, None, None, None, id="include"
        ),
        pytest.param(
            {"rename_fields": {"work.street": "road"}}, {"road": "s", "city": "c"}, None, None, None, id="rename"
        ),
        pytest.param(
            {"exclude": {"either.street", "either.0.city"}}, None, None, None, {"street": "s"}, id="multi-member-union"
        ),
    ],
)
def test_dto_config_paths_reach_through_optional(
    config: dict[str, Any], work: Any, home: Any, homes: Any, either: Any
) -> None:
    full = {"street": "s", "city": "c"}
    expected = {"work": work or full, "home": home or full, "homes": homes or [full], "either": either or full}

    @get("/", return_dto=DataclassDTO[Annotated[OptionalPathPerson, DTOConfig(**config)]])
    def read_person() -> OptionalPathPerson:
        address = PathAddress(street="s", city="c")
        return OptionalPathPerson(work=address, home=address, homes=[address], either=address)

    with create_test_client(route_handlers=[read_person]) as client:
        response = client.get("/").json()
        schemas = client.get("/schema/openapi.json").json()["components"]["schemas"]

    assert response == expected
    documented = sorted(sorted(schema["properties"]) for name, schema in schemas.items() if "PathAddress" in name)
    sent = [response["work"], response["home"], response["homes"][0], response["either"]]
    assert documented == sorted(sorted(value) for value in sent)


def test_dto_rename_through_optional_applies_to_request_data() -> None:
    dto = DataclassDTO[Annotated[OptionalPathPerson, DTOConfig(rename_fields={"work.street": "st"})]]

    @post("/", dto=dto, return_dto=None, sync_to_thread=False)
    def create_person(data: JSONBody[OptionalPathPerson]) -> str:
        return not_none(data.work).street

    with create_test_client(route_handlers=[create_person]) as client:
        response = client.post("/", json={"work": {"st": "s", "city": "c"}})

    assert (response.status_code, response.text) == (201, "s")


@dataclass
class A:
    x: int


@dataclass
class H:
    t: tuple[A, int]


@pytest.mark.parametrize("value", [(A(1),), (A(1), 2, 3)])
def test_dto_fixed_length_tuple_of_wrong_length_fails(value: tuple[Any, ...]) -> None:
    @get("/", return_dto=DataclassDTO[H])
    def read_h() -> H:
        return H(t=value)

    with create_test_client(route_handlers=[read_h], raise_server_exceptions=False) as client:
        assert client.get("/").status_code == 500


@dataclass
class User:
    name: str
    age: int
    read_only: str = field(default="read-only", metadata=dto_field("read-only"))


def test_dto_data_with_url_encoded_form_data() -> None:
    @post(dto=DataclassDTO[User])
    def handler(data: URLEncodedBody[DTOData[User]]) -> User:
        return data.create_instance()

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post(
            "/",
            content=b"id=1&name=John&age=42&read_only=whoops",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.json() == {"name": "John", "age": 42, "read_only": "read-only"}


RenamedBarT = TypeVar("RenamedBarT")


@dataclass
class GenericRenamedBar(Generic[RenamedBarT]):
    bar: str
    spam_bar: RenamedBarT
    foo_foo: str


@dataclass
class InnerBar:
    best_greeting: str


@dataclass
class RenamedBar(GenericRenamedBar[InnerBar]):
    pass


def test_dto_data_create_instance_renamed_fields() -> None:
    @post(
        dto=DataclassDTO[
            Annotated[
                RenamedBar,
                DTOConfig(
                    exclude={"foo_foo"},
                    rename_strategy="camel",
                ),
            ]
        ],
        return_dto=DataclassDTO[
            Annotated[
                RenamedBar,
                DTOConfig(rename_strategy="camel"),
            ]
        ],
    )
    def handler(data: JSONBody[DTOData[RenamedBar]]) -> RenamedBar:
        assert isinstance(data, DTOData)
        result = data.create_instance(foo_foo="world")
        assert result.foo_foo == "world"
        assert result.spam_bar.best_greeting == "hello world"
        return result

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"bar": "hello", "spamBar": {"bestGreeting": "hello world"}})
        assert response.status_code == 201
        assert response.json() == {"bar": "hello", "fooFoo": "world", "spamBar": {"bestGreeting": "hello world"}}


def test_dto_data_with_patch_request() -> None:
    class PatchDTO(DataclassDTO[User]):
        config = DTOConfig(partial=True)

    @patch(dto=PatchDTO, return_dto=None)
    def handler(data: JSONBody[DTOData[User]]) -> User:
        return data.update_instance(User(name="John", age=42))

    with create_test_client(route_handlers=[handler]) as client:
        response = client.patch("/", json={"age": 41, "read_only": "whoops"})
        assert response.json() == {"name": "John", "age": 41, "read_only": "read-only"}


def test_dto_data_update_instance_keywords_take_precedence() -> None:
    class PatchDTO(DataclassDTO[User]):
        config = DTOConfig(partial=True)

    @patch(dto=PatchDTO, return_dto=None)
    def handler(data: JSONBody[DTOData[User]]) -> User:
        return data.update_instance(User(name="John", age=42), age=7)

    with create_test_client(route_handlers=[handler]) as client:
        response = client.patch("/", json={"name": "Jane", "age": 41})

    assert response.json() == {"name": "Jane", "age": 7, "read_only": "read-only"}


@dataclass
class FailingMember:
    label: str

    def __post_init__(self) -> None:
        raise TypeError("server-side failure")


@dataclass
class FailingMemberParent:
    members: list[FailingMember]


def test_dto_data_nested_member_raising_type_error_is_a_server_error() -> None:
    @post(dto=DataclassDTO[FailingMemberParent], return_dto=None)
    def handler(data: JSONBody[DTOData[FailingMemberParent]]) -> None:
        return None

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"members": [{"label": "a"}]})

    assert response.status_code == 500
    assert "server-side failure" not in response.text


@dataclass
class UniqueModelName:
    id: int
    foo: str


def test_dto_openapi_with_unique_handler_names() -> None:
    @post(
        dto=DataclassDTO[Annotated[UniqueModelName, DTOConfig(exclude={"id"})]],
        return_dto=DataclassDTO[UniqueModelName],
        signature_namespace={"UniqueModelName": UniqueModelName},
    )
    def handler(data: JSONBody[UniqueModelName]) -> UniqueModelName:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.get("/schema/openapi.json")
        schemas = list(response.json()["components"]["schemas"].values())
        assert len(schemas) == 2
        assert schemas[0]["title"] == "HandlerUniqueModelNameRequestBody"
        assert schemas[1]["title"] == "HandlerUniqueModelNameResponseBody"


@dataclass
class SharedModelName:
    id: int
    foo: str


def test_dto_openapi_without_unique_handler_names() -> None:
    write_dto = DataclassDTO[Annotated[SharedModelName, DTOConfig(exclude={"id"})]]
    read_dto = DataclassDTO[SharedModelName]

    @post(dto=write_dto, return_dto=read_dto)
    def handler(data: JSONBody[SharedModelName]) -> SharedModelName:
        return data

    class MyController(Controller):
        path = "/sub-path"

        @post(dto=write_dto, return_dto=read_dto)
        def handler(self, data: JSONBody[SharedModelName]) -> SharedModelName:
            return data

    with create_test_client(route_handlers=[handler, MyController]) as client:
        response = client.get("/schema/openapi.json")
        schemas = list(response.json()["components"]["schemas"].values())
        assert len(schemas) == 4
        assert schemas[0]["title"] == "HandlerSharedModelNameRequestBody"
        assert schemas[1]["title"] == "HandlerSharedModelNameResponseBody"
        assert (
            schemas[2]["title"]
            == "tests.unit.test_dto.test_factory.test_integration.test_dto_openapi_without_unique_handler_names.<locals>.MyController.handlerSharedModelNameRequestBody"
        )
        assert (
            schemas[3]["title"]
            == "tests.unit.test_dto.test_factory.test_integration.test_dto_openapi_without_unique_handler_names.<locals>.MyController.handlerSharedModelNameResponseBody"
        )


def test_url_encoded_form_data_patch_request() -> None:
    @dataclass()
    class User:
        name: str
        age: int
        read_only: str = field(default="read-only", metadata=dto_field("read-only"))

    dto = DataclassDTO[Annotated[User, DTOConfig(partial=True)]]

    @post(dto=dto, return_dto=None, signature_types=[User])
    def handler(data: URLEncodedBody[DTOData[User]]) -> dict[str, Any]:
        return data.as_builtins()  # type:ignore[no-any-return]

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post(
            "/",
            content=b"name=John&read_only=whoops",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.json() == {"name": "John"}


def test_dto_with_generic_sequence_annotations() -> None:
    @dataclass
    class User:
        name: str
        age: int

    @post(
        dto=DataclassDTO[User],
        signature_types=[User],
    )
    def handler(data: JSONBody[Sequence[User]]) -> Sequence[User]:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json=[{"name": "John", "age": 42}])
        assert response.json() == [{"name": "John", "age": 42}]


def test_dto_concrete_builtin_collection_types() -> None:
    @dataclass
    class Foo:
        bar: dict
        baz: list

    @post(
        dto=DataclassDTO[
            Annotated[
                Foo,
                DTOConfig(underscore_fields_private=False),
            ]
        ],
        signature_types=[Foo],
    )
    def handler(data: JSONBody[Foo]) -> Foo:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"bar": {"a": 1, "b": [1, 2, 3]}, "baz": [4, 5, 6]})
        assert response.status_code == 201
        assert response.json() == {"bar": {"a": 1, "b": [1, 2, 3]}, "baz": [4, 5, 6]}


@dataclass
class WrappedUser:
    name: str
    age: int


T = TypeVar("T")
V = TypeVar("V")
K = TypeVar("K")


@dataclass
class Wrapped(Generic[T, V]):
    data: T
    other: V


def test_dto_generic_dataclass_wrapped_list_response() -> None:
    @get(dto=DataclassDTO[Annotated[WrappedUser, DTOConfig(exclude={"age"})]])
    def handler() -> Wrapped[list[WrappedUser], int]:
        return Wrapped(
            data=[WrappedUser(name="John", age=42), WrappedUser(name="Jane", age=43)],
            other=2,
        )

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.json() == {"data": [{"name": "John"}, {"name": "Jane"}], "other": 2}


@dataclass
class WrappedWithCollection(Generic[T, V]):
    items: list[T]
    other: V


def test_dto_generic_dataclass_wrapped_collection_response() -> None:
    @get(dto=DataclassDTO[Annotated[WrappedUser, DTOConfig(exclude={"age"})]])
    def handler() -> WrappedWithCollection[WrappedUser, int]:
        return WrappedWithCollection(
            items=[WrappedUser(name="John", age=42), WrappedUser(name="Jane", age=43)],
            other=2,
        )

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.json() == {"items": [{"name": "John"}, {"name": "Jane"}], "other": 2}


@dataclass
class WrappedWithDict(Generic[K, V, T]):
    data: T
    other: dict[K, V]


def test_dto_generic_dataclass_wrapped_scalar_response_with_additional_mapping_data() -> None:
    @get(dto=DataclassDTO[Annotated[WrappedUser, DTOConfig(exclude={"age"})]])
    def handler() -> WrappedWithDict[str, int, WrappedUser]:
        return WrappedWithDict(
            data=WrappedUser(name="John", age=42),
            other={"a": 1, "b": 2},
        )

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.json() == {"data": {"name": "John"}, "other": {"a": 1, "b": 2}}


def test_dto_response_wrapped_scalar_return_type() -> None:
    @get(dto=DataclassDTO[Annotated[WrappedUser, DTOConfig(exclude={"age"})]])
    def handler() -> Response[WrappedUser]:
        return Response(content=WrappedUser(name="John", age=42))

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.json() == {"name": "John"}

        schema_response = client.get("/schema/openapi.json")
        schemas = list(schema_response.json()["components"]["schemas"].values())
        assert len(schemas) == 1
        assert schemas[0]["title"] == "HandlerWrappedUserResponseBody"


def test_dto_response_wrapped_collection_return_type() -> None:
    @get(dto=DataclassDTO[Annotated[WrappedUser, DTOConfig(exclude={"age"})]])
    def handler() -> Response[list[WrappedUser]]:
        return Response(content=[WrappedUser(name="John", age=42), WrappedUser(name="Jane", age=43)])

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.json() == [{"name": "John"}, {"name": "Jane"}]

        schema_response = client.get("/schema/openapi.json")
        schemas = list(schema_response.json()["components"]["schemas"].values())
        assert len(schemas) == 1
        assert schemas[0]["title"] == "HandlerWrappedUserResponseBody"


def test_schema_required_fields_with_msgspec_dto() -> None:
    class MsgspecUser(Struct):
        age: int
        name: str

    class UserDTO(MsgspecDTO[MsgspecUser]):
        pass

    @post(dto=UserDTO, return_dto=None, signature_types=[MsgspecUser])
    def handler(data: JSONBody[MsgspecUser], request: Request) -> dict:
        schema = request.app.openapi_schema
        return schema.to_schema()

    with create_test_client(handler) as client:
        data = MsgspecUser(name="A", age=10)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        received = client.post(
            "/",
            content=msgspec.json.encode(data),
            headers=headers,
        )
        required = next(iter(received.json()["components"]["schemas"].values()))["required"]
        assert len(required) == 2


def test_schema_required_fields_with_dataclass_dto() -> None:
    @dataclass
    class DataclassUser:
        age: int
        name: str

    class UserDTO(DataclassDTO[DataclassUser]):
        pass

    @post(dto=UserDTO, return_dto=None, signature_types=[DataclassUser])
    def handler(data: JSONBody[DataclassUser], request: Request) -> dict:
        schema = request.app.openapi_schema
        return schema.to_schema()

    with create_test_client(handler) as client:
        data = DataclassUser(name="A", age=10)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        received = client.post(
            "/",
            content=msgspec.json.encode(data),
            headers=headers,
        )
        required = next(iter(received.json()["components"]["schemas"].values()))["required"]
        assert len(required) == 2


def test_schema_required_fields_with_msgspec_dto_and_default_fields() -> None:
    class MsgspecUser(Struct):
        age: int
        name: str = "A"

    class UserDTO(MsgspecDTO[MsgspecUser]):
        pass

    @post(dto=UserDTO, return_dto=None, signature_types=[MsgspecUser])
    def handler(data: JSONBody[MsgspecUser], request: Request) -> dict:
        schema = request.app.openapi_schema
        return schema.to_schema()

    with create_test_client(handler) as client:
        data = MsgspecUser(name="A", age=10)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        received = client.post(
            "/",
            content=msgspec.json.encode(data),
            headers=headers,
        )
        required = next(iter(received.json()["components"]["schemas"].values()))["required"]
        assert required == ["age"]


X = TypeVar("X", bound=Struct)


class ClassicNameStyle(Struct):
    first_name: str
    surname: str


class BoundUser(Struct, Generic[X]):
    age: int
    data: X


class Superuser(BoundUser[ClassicNameStyle]):
    pass


def test_dto_with_msgspec_with_bound_generic_and_inherited_models() -> None:
    @post(dto=MsgspecDTO[Superuser])
    def handler(data: JSONBody[Superuser]) -> Superuser:
        return data

    with create_test_client(handler) as client:
        data = Superuser(data=ClassicNameStyle(first_name="A", surname="B"), age=10)
        received = client.post(
            "/",
            content=encode_json(data),
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        assert msgspec.json.decode(received.content, type=Superuser) == data


def test_dto_returning_mapping() -> None:
    @dataclass
    class Lexeme:
        id: int
        name: str

    class LexemeDTO(DataclassDTO[Lexeme]):
        config = DTOConfig(exclude={"id"})

    @get(return_dto=LexemeDTO, signature_types=[Lexeme])
    async def get_definition() -> dict[str, Lexeme]:
        return {"hello": Lexeme(id=1, name="hello"), "world": Lexeme(id=2, name="world")}

    with create_test_client(route_handlers=[get_definition]) as client:
        response = client.get("/")
        assert response.json() == {"hello": {"name": "hello"}, "world": {"name": "world"}}


def test_data_dto_with_default() -> None:
    """A POST request without Body should inject the default value.

    https://github.com/litestar-org/litestar/issues/2902
    """

    @dataclass
    class Foo:
        foo: str

    @post(path="/", dto=DataclassDTO[Foo], signature_types=[Foo])
    def test(data: JSONBody[Optional[Foo]] = None) -> dict:
        return {"foo": data}

    with create_test_client([test]) as client:
        response = client.post("/")
        assert response.json() == {"foo": None}


@pytest.mark.parametrize(
    "field_type, constraint_name, constraint_value, request_data",
    [
        (int, "gt", 2, 2),
        (int, "ge", 2, 1),
        (int, "lt", 2, 2),
        (int, "le", 2, 3),
        (int, "multiple_of", 2, 3),
        (str, "min_length", 2, "1"),
        (str, "max_length", 1, "12"),
        (str, "pattern", r"\d", "a"),
    ],
)
def test_msgspec_dto_copies_constraints(
    field_type: Any, constraint_name: str, constraint_value: Any, request_data: Any
) -> None:
    # https://github.com/litestar-org/litestar/issues/3026
    struct = msgspec.defstruct(
        "Foo",
        fields=[("bar", Annotated[field_type, msgspec.Meta(**{constraint_name: constraint_value})])],  # type: ignore[list-item]
    )

    @post(
        "/",
        dto=MsgspecDTO[struct],  # type: ignore[valid-type]
        signature_namespace={"struct": struct},
    )
    def handler(data: JSONBody[struct]) -> None:  # type: ignore[valid-type]
        pass

    with create_test_client([handler]) as client:
        assert client.post("/", json={"bar": request_data}).status_code == 400


@pytest.mark.parametrize(
    "field_type, constraint_name, constraint_value, request_data",
    [
        (int, "gt", 2, 2),
        (int, "ge", 2, 1),
        (int, "lt", 2, 2),
        (int, "le", 2, 3),
        (int, "multiple_of", 2, 3),
        (str, "min_length", 2, "1"),
        (str, "max_length", 1, "12"),
        (str, "pattern", r"\d", "a"),
    ],
)
def test_msgspec_dto_copies_constraints_for_partial_dto(
    field_type: Any, constraint_name: str, constraint_value: Any, request_data: Any
) -> None:
    struct = msgspec.defstruct(
        "Foo",
        fields=[("bar", Annotated[field_type, msgspec.Meta(**{constraint_name: constraint_value})])],  # type: ignore[list-item]
    )

    with _create_client(MsgspecDTO, struct, partial=True) as client:
        assert client.post("/", json={}).status_code == 201
        assert client.post("/", json={"bar": request_data}).status_code == 400


def test_msgspec_dto_copies_length_constraints_for_partial_dto() -> None:
    class Foo(msgspec.Struct):
        bar: Annotated[str, msgspec.Meta(min_length=2)]
        baz: Annotated[str, msgspec.Meta(max_length=2)]

    class FooDTO(MsgspecDTO[Foo]):
        config = DTOConfig(partial=True)

    @post("/", dto=FooDTO, return_dto=None, signature_types={Foo})
    def handler(data: JSONBody[DTOData[Foo]]) -> None:
        pass

    with create_test_client([handler]) as client:
        assert client.post("/", json={"bar": "1"}).status_code == 400
        assert client.post("/", json={"baz": "123"}).status_code == 400
        assert client.post("/", json={"bar": "12", "baz": "12"}).status_code == 201
        assert client.post("/", json={}).status_code == 201


def _make_model(dto_type: Any, annotation: Any, **default: Any) -> Any:
    if dto_type is DataclassDTO:
        return make_dataclass("Model", [("f", annotation, field(**default))])
    return msgspec.defstruct("Model", [("f", annotation, msgspec.field(**default))])


def _create_client(dto_type: Any, model: Any, partial: bool = False) -> Any:
    async def create(data: Any) -> None:
        return None

    json_body: Any = JSONBody
    dto_data: Any = DTOData
    create.__annotations__["data"] = json_body[dto_data[model] if partial else model]
    dto = dto_type[Annotated[model, DTOConfig(partial=True)]] if partial else dto_type[model]
    return create_test_client([post("/", dto=dto, return_dto=None)(create)], openapi_config=None)


_MEMBER_CONSTRAINT_CASES = [
    pytest.param(list[Annotated[str, Meta(min_length=5)]], ["12"], ["12345"], id="list_item"),
    pytest.param(dict[str, Annotated[str, Meta(min_length=5)]], {"k": "12"}, {"k": "12345"}, id="dict_value"),
    pytest.param(dict[Annotated[str, Meta(min_length=5)], int], {"k": 1}, {"kkkkk": 1}, id="dict_key"),
    pytest.param(tuple[Annotated[str, Meta(min_length=5)], int], ["12", 1], ["12345", 1], id="tuple_member"),
    pytest.param(Union[Annotated[str, Meta(min_length=5)], int], "12", 3, id="union_member"),
]


@pytest.mark.parametrize(
    "dto_type, annotation, invalid, valid",
    [
        *(
            pytest.param(dto_type, *case.values, id=f"{dto_type.__name__}-{case.id}")
            for dto_type in (DataclassDTO, MsgspecDTO)
            for case in _MEMBER_CONSTRAINT_CASES
        ),
        pytest.param(
            DataclassDTO, Optional[Annotated[str, Meta(pattern="^a")]], "b", None, id="DataclassDTO-optional_member"
        ),
    ],
)
def test_dto_enforces_member_constraints(dto_type: Any, annotation: Any, invalid: Any, valid: Any) -> None:
    with _create_client(dto_type, _make_model(dto_type, annotation)) as client:
        assert client.post("/", json={"f": invalid}).status_code == 400
        assert client.post("/", json={"f": valid}).status_code == 201


@pytest.mark.parametrize(
    "dto_type, annotation, default, invalid, valid",
    [
        *(
            pytest.param(dto_type, annotation, {}, invalid, valid, id=f"{dto_type.__name__}-{case_id}")
            for dto_type in (DataclassDTO, MsgspecDTO)
            for annotation, invalid, valid, case_id in (
                (list[Annotated[str, Meta(min_length=5)]], ["12"], ["12345"], "list_item"),
                (Union[Annotated[str, Meta(min_length=5)], int], "12", 3, "union_member"),
            )
        ),
        pytest.param(
            MsgspecDTO,
            Union[Annotated[str, Meta(min_length=8)], UnsetType],
            {"default": UNSET},
            "12",
            "12345678",
            id="MsgspecDTO-unset_union_member",
        ),
    ],
)
def test_dto_enforces_member_constraints_with_partial(
    dto_type: Any, annotation: Any, default: dict[str, Any], invalid: Any, valid: Any
) -> None:
    with _create_client(dto_type, _make_model(dto_type, annotation, **default), partial=True) as client:
        assert client.post("/", json={"f": invalid}).status_code == 400
        assert client.post("/", json={"f": valid}).status_code == 201
        assert client.post("/", json={}).status_code == 201


def test_return_dto_schema_builds_with_member_meta_msgspec_rejects() -> None:
    model = make_dataclass("Model", [("f", list[Annotated[int, Meta(min_length=1, description="d")]])])

    @get("/", return_dto=DataclassDTO[model], signature_namespace={"model": model})  # type: ignore[valid-type]
    def read_member_meta() -> model:  # type: ignore[valid-type]
        return model(f=[1])  # type: ignore[no-any-return]

    with create_test_client([read_member_meta]) as client:
        assert client.get("/").status_code == 200
        assert client.get("/schema/openapi.json").status_code == 200


Limit = TypeAliasType("Limit", Annotated[int, Meta(ge=0)])


@pytest.mark.parametrize("partial", [False, True])
@pytest.mark.parametrize("dto_type", [DataclassDTO, MsgspecDTO])
@pytest.mark.parametrize(
    "annotation, default, invalid, valid",
    [
        pytest.param(Annotated[int, Meta(ge=1)], {"default": 1}, 0, 2, id="meta_ge"),
        pytest.param(Annotated[str, Meta(min_length=5)], {"default": "12345"}, "12", "123456", id="meta_min_length"),
        pytest.param(
            Annotated[list[int], Meta(min_length=2)], {"default_factory": list}, [1], [1, 2], id="meta_list_length"
        ),
        pytest.param(
            Limit,
            {"default": 0},
            -1,
            1,
            id="type_alias",
            marks=pytest.mark.skipif(sys.version_info < (3, 12), reason="msgspec decodes typing.TypeAliasType only"),
        ),
        pytest.param(
            Annotated[str, annotated_types.MinLen(5)], {"default": "12345"}, "12", "123456", id="annotated_types_field"
        ),
        pytest.param(
            list[Annotated[str, annotated_types.MinLen(5)]],
            {"default_factory": list},
            ["12"],
            ["12345"],
            id="annotated_types_item",
        ),
    ],
)
def test_dto_enforces_field_constraints(
    dto_type: Any, partial: bool, annotation: Any, default: dict[str, Any], invalid: Any, valid: Any
) -> None:
    with _create_client(dto_type, _make_model(dto_type, annotation, **default), partial) as client:
        assert client.post("/", json={"f": invalid}).status_code == 400
        assert client.post("/", json={"f": valid}).status_code == 201


@pytest.mark.parametrize("partial", [False, True])
def test_msgspec_dto_enforces_constraints_of_optional_member(partial: bool) -> None:
    class Foo(msgspec.Struct):
        bar: Annotated[str, Meta(min_length=2)] | None
        url: Optional[Annotated[str, Meta(pattern="^a")]] = None

    with _create_client(MsgspecDTO, Foo, partial) as client:
        assert client.post("/", json={"bar": "1"}).status_code == 400
        assert client.post("/", json={"bar": "123", "url": "b"}).status_code == 400
        assert client.post("/", json={"bar": "123", "url": "ab"}).status_code == 201
        assert client.post("/", json={"bar": None, "url": None}).status_code == 201


def test_msgspec_dto_enforces_constraints_of_unset_union_member() -> None:
    class Foo(msgspec.Struct):
        password: Union[Annotated[str, Meta(min_length=8)], UnsetType] = UNSET

    with _create_client(MsgspecDTO, Foo) as client:
        assert client.post("/", json={"password": "12"}).status_code == 400
        assert client.post("/", json={}).status_code == 201
        assert client.post("/", json={"password": "12345678"}).status_code == 201


@pytest.mark.parametrize(
    "annotation, statuses",
    [
        pytest.param(Annotated[int, Meta(ge=1), annotated_types.Ge(3)], {0: 400, 2: 201}, id="same_attribute"),
        pytest.param(
            Annotated[int, Meta(ge=1), annotated_types.Le(5)], {0: 400, 9: 400, 2: 201}, id="different_attribute"
        ),
    ],
)
def test_dto_meta_wins_over_derived_constraint_for_the_same_attribute(
    annotation: Any, statuses: dict[int, int]
) -> None:
    with _create_client(DataclassDTO, _make_model(DataclassDTO, annotation, default=2)) as client:
        assert {value: client.post("/", json={"f": value}).status_code for value in statuses} == statuses


def test_dto_does_not_apply_constraints_to_return_data() -> None:
    model = make_dataclass("Model", [("f", Annotated[str, Meta(min_length=5)])])

    @get("/", return_dto=DataclassDTO[model], signature_namespace={"model": model})  # type: ignore[valid-type]
    def read_constraint_violating() -> model:  # type: ignore[valid-type]
        return model(f="12")  # type: ignore[no-any-return]

    with create_test_client([read_constraint_violating]) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"f": "12"}


def test_dto_schema_documents_field_and_optional_member_constraints() -> None:
    field_model = make_dataclass("FieldModel", [("f", Annotated[int, Meta(ge=1)])])
    optional_annotation: Any = Optional[Annotated[str, Meta(pattern="^a")]]
    optional_model = msgspec.defstruct("OptionalModel", [("o", optional_annotation, None)])

    @post(
        "/field",
        dto=DataclassDTO[field_model],  # type: ignore[valid-type]
        return_dto=None,
        signature_namespace={"field_model": field_model},
    )
    def create_field_model(data: JSONBody[field_model]) -> None:  # type: ignore[valid-type]
        pass

    @post(
        "/optional",
        dto=MsgspecDTO[optional_model],  # type: ignore[valid-type]
        return_dto=None,
        signature_namespace={"optional_model": optional_model},
    )
    def create_optional_model(data: JSONBody[optional_model]) -> None:  # type: ignore[valid-type]
        pass

    with create_test_client([create_field_model, create_optional_model]) as client:
        schemas = client.app.openapi_schema.to_schema()["components"]["schemas"]

    assert set(schemas) == {"CreateFieldModelFieldModelRequestBody", "CreateOptionalModelOptionalModelRequestBody"}
    assert schemas["CreateFieldModelFieldModelRequestBody"]["properties"]["f"]["minimum"] == 1
    assert schemas["CreateOptionalModelOptionalModelRequestBody"]["properties"]["o"]["pattern"] == "^a"


_NON_NUMERIC_BOUNDS = [
    pytest.param(date, annotated_types.Ge(date(2020, 1, 1)), "2019-01-01", "2021-01-01", date(2021, 1, 1), id="date"),
    pytest.param(
        datetime,
        annotated_types.Ge(datetime(2020, 1, 1)),
        "2019-01-01T00:00:00",
        "2021-01-01T00:00:00",
        datetime(2021, 1, 1),
        id="datetime",
    ),
    pytest.param(timedelta, annotated_types.Gt(timedelta(0)), "-PT1S", "PT1S", timedelta(seconds=1), id="timedelta"),
    pytest.param(Decimal, annotated_types.Ge(Decimal(1)), "0", "2", Decimal(2), id="decimal"),
]


@pytest.mark.parametrize("dto_type", [DataclassDTO, MsgspecDTO])
@pytest.mark.parametrize("as_item", [False, True], ids=["field", "item"])
@pytest.mark.parametrize("base_type, bound, below, above, value", _NON_NUMERIC_BOUNDS)
def test_dto_ignores_bounds_msgspec_cannot_express(
    dto_type: Any, as_item: bool, base_type: Any, bound: Any, below: str, above: str, value: Any
) -> None:
    annotation: Any = Annotated[base_type, bound]
    below_payload: Any = below
    above_payload: Any = above
    returned: Any = value
    if as_item:
        annotation, below_payload, above_payload, returned = list[annotation], [below], [above], [value]
    model = _make_model(dto_type, annotation)

    @post("/", dto=dto_type[model], return_dto=None, signature_namespace={"model": model})
    def create_non_numeric_bound(data: JSONBody[model]) -> None:  # type: ignore[valid-type]
        pass

    @get("/", return_dto=dto_type[model], signature_namespace={"model": model})
    def read_non_numeric_bound() -> model:  # type: ignore[valid-type]
        return model(f=returned)  # type: ignore[no-any-return]

    with create_test_client([create_non_numeric_bound, read_non_numeric_bound]) as client:
        assert client.post("/", json={"f": below_payload}).status_code == 201
        assert client.post("/", json={"f": above_payload}).status_code == 201
        assert client.get("/").status_code == 200
        assert client.get("/schema/openapi.json").status_code == 200


@pytest.mark.parametrize(
    "dto_type, annotation, partial, invalid, valid",
    [
        pytest.param(
            MsgspecDTO, Annotated[Decimal, annotated_types.Gt(0)], False, "0", "1", id="MsgspecDTO-decimal_gt"
        ),
        pytest.param(
            MsgspecDTO, Annotated[Decimal, annotated_types.Gt(0)], True, "0", "1", id="MsgspecDTO-decimal_gt-partial"
        ),
        *(
            pytest.param(
                dto_type,
                list[Annotated[Decimal, annotated_types.Gt(0)]],
                False,
                ["0"],
                ["1"],
                id=f"{dto_type.__name__}-decimal_gt_item",
            )
            for dto_type in (DataclassDTO, MsgspecDTO)
        ),
        pytest.param(
            MsgspecDTO, Annotated[Decimal, QueryParameter(gt=0)], False, "0", "1", id="MsgspecDTO-decimal_parameter_gt"
        ),
        pytest.param(MsgspecDTO, Annotated[int, annotated_types.Ge(1.5)], False, 1, 2, id="MsgspecDTO-int_float_bound"),
        pytest.param(
            MsgspecDTO,
            Annotated[timedelta, annotated_types.Ge(0)],
            False,
            "-PT1S",
            "PT1S",
            id="MsgspecDTO-timedelta_int_bound",
        ),
        pytest.param(MsgspecDTO, Annotated[bool, annotated_types.Ge(1)], False, False, True, id="MsgspecDTO-bool_ge"),
        *(
            pytest.param(dto_type, annotation, False, invalid, valid, id=f"{dto_type.__name__}-{case_id}")
            for dto_type in (DataclassDTO, MsgspecDTO)
            for annotation, invalid, valid, case_id in (
                (Annotated[Optional[int], annotated_types.Ge(0)], -1, 1, "optional_ge"),
                (Annotated[Union[str, int], annotated_types.MinLen(2)], "a", "ab", "union_min_len"),
                (Annotated[Optional[int], QueryParameter(ge=1)], 0, 1, "optional_parameter_ge"),
                (Annotated[Optional[str], annotated_types.MinLen(5)], "12", None, "optional_min_len"),
            )
        ),
    ],
)
def test_dto_does_not_enforce_derived_constraints_msgspec_cannot_express(
    dto_type: Any, annotation: Any, partial: bool, invalid: Any, valid: Any
) -> None:
    with _create_client(dto_type, _make_model(dto_type, annotation), partial) as client:
        assert client.post("/", json={"f": invalid}).status_code == 201
        assert client.post("/", json={"f": valid}).status_code == 201


def test_msgspec_dto_raises_invalid_annotation_for_mixed_type_literal() -> None:
    annotation: Any = Literal[1, "a"]
    struct = msgspec.defstruct("Model", [("f", annotation)])

    with pytest.raises(InvalidAnnotationException, match="msgspec cannot inspect") as exc_info:

        @post("/", dto=MsgspecDTO[struct], return_dto=None, signature_namespace={"struct": struct})  # type: ignore[valid-type]
        def create_mixed_literal(data: JSONBody[struct]) -> None:  # type: ignore[valid-type]
            pass

        Litestar(route_handlers=[create_mixed_literal], openapi_config=None)

    assert isinstance(exc_info.value.__cause__, TypeError)


_CONFLICTING_DERIVED_CASES = [
    pytest.param(Annotated[int, annotated_types.Ge(1), annotated_types.Gt(0)], 0, 3, 201, None, id="derived_ge_and_gt"),
    pytest.param(Annotated[int, QueryParameter(ge=1, gt=0)], 0, 3, 201, None, id="parameter_ge_and_gt"),
    pytest.param(Annotated[int, annotated_types.Le(5), annotated_types.Lt(9)], 7, 3, 201, None, id="derived_le_and_lt"),
    pytest.param(
        Annotated[int, Meta(gt=0), annotated_types.Ge(5)],
        0,
        3,
        400,
        ("exclusiveMinimum", 0),
        id="own_gt_and_derived_ge",
    ),
    pytest.param(
        Annotated[int, Meta(lt=9), annotated_types.Le(5)],
        9,
        7,
        400,
        ("exclusiveMaximum", 9),
        id="own_lt_and_derived_le",
    ),
]


@pytest.mark.parametrize("partial", [False, True], ids=["full", "partial"])
@pytest.mark.parametrize("dto_type", [DataclassDTO, MsgspecDTO])
@pytest.mark.parametrize("annotation, rejected, accepted, rejected_status, own_bound", _CONFLICTING_DERIVED_CASES)
def test_dto_drops_derived_constraints_that_conflict(
    dto_type: Any,
    partial: bool,
    annotation: Any,
    rejected: Any,
    accepted: Any,
    rejected_status: int,
    own_bound: tuple[str, int] | None,
) -> None:
    with _create_client(dto_type, _make_model(dto_type, annotation), partial) as client:
        assert client.post("/", json={"f": rejected}).status_code == rejected_status
        assert client.post("/", json={"f": accepted}).status_code == 201


@pytest.mark.parametrize("dto_type", [DataclassDTO, MsgspecDTO])
def test_dto_raises_at_startup_for_an_invalid_pattern(dto_type: Any) -> None:
    with pytest.raises(re.error):
        _create_client(dto_type, _make_model(dto_type, Annotated[str, QueryParameter(pattern="(")]))


@pytest.mark.parametrize("dto_type", [DataclassDTO, MsgspecDTO])
@pytest.mark.parametrize("annotation, rejected, accepted, rejected_status, own_bound", _CONFLICTING_DERIVED_CASES)
def test_return_dto_drops_derived_constraints_that_conflict(
    dto_type: Any,
    annotation: Any,
    rejected: Any,
    accepted: Any,
    rejected_status: int,
    own_bound: tuple[str, int] | None,
) -> None:
    model = _make_model(dto_type, annotation)

    @get("/", return_dto=dto_type[model], signature_namespace={"model": model})
    def read_conflicting() -> model:  # type: ignore[valid-type]
        return model(f=accepted)  # type: ignore[no-any-return]

    with create_test_client([read_conflicting]) as client:
        assert client.get("/").json() == {"f": accepted}
        response = client.get("/schema/openapi.json")
        assert response.status_code == 200

    if own_bound is not None:
        keyword, value = own_bound
        (component,) = response.json()["components"]["schemas"].values()
        assert component["properties"]["f"][keyword] == value


def test_return_dto_schema_builds_with_field_constraint_msgspec_rejects() -> None:
    misplaced_meta = make_dataclass(
        "MisplacedMeta", [("f", Annotated[Optional[str], Meta(min_length=5)], field(default=None))]
    )
    min_len_annotation: Any = Annotated[Optional[str], annotated_types.MinLen(5)]
    misplaced_min_len = msgspec.defstruct("MisplacedMinLen", [("f", min_len_annotation, None)])
    described = make_dataclass(
        "Described", [("f", Annotated[Optional[str], Meta(min_length=5, description="d")], field(default=None))]
    )

    @get("/meta", return_dto=DataclassDTO[misplaced_meta], signature_namespace={"misplaced_meta": misplaced_meta})  # type: ignore[valid-type]
    def read_misplaced_meta() -> misplaced_meta:  # type: ignore[valid-type]
        return misplaced_meta(f="12")  # type: ignore[no-any-return]

    @get(
        "/min-len",
        return_dto=MsgspecDTO[misplaced_min_len],  # type: ignore[valid-type]
        signature_namespace={"misplaced_min_len": misplaced_min_len},
    )
    def read_misplaced_min_len() -> misplaced_min_len:  # type: ignore[valid-type]
        return misplaced_min_len(f="12")

    @get("/described", return_dto=DataclassDTO[described], signature_namespace={"described": described})  # type: ignore[valid-type]
    def read_described() -> described:  # type: ignore[valid-type]
        return described(f="12")  # type: ignore[no-any-return]

    with create_test_client([read_misplaced_meta, read_misplaced_min_len, read_described]) as client:
        for path in ("/meta", "/min-len", "/described"):
            assert client.get(path).status_code == 200
        response = client.get("/schema/openapi.json")
        assert response.status_code == 200

    schema = response.json()
    reference = schema["paths"]["/described"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    component = schema["components"]["schemas"][reference["$ref"].rsplit("/", 1)[-1]]
    assert component["properties"]["f"]["description"] == "d"


@pytest.mark.parametrize("direction", ["data", "return"])
def test_msgspec_dto_raises_invalid_annotation_when_msgspec_rejects_the_model(direction: str) -> None:
    annotation: Any = Annotated[Optional[str], Meta(min_length=5)]
    struct = msgspec.defstruct("Model", [("f", annotation, None)])

    with pytest.raises(
        DTOTransferTypeError,
        match=r"^\[paths='/', handler='\w+'\] msgspec cannot inspect .*field 'f'.*min_length.*attach the constraint to the member type it applies to",
    ):
        if direction == "data":

            @post("/", dto=MsgspecDTO[struct], return_dto=None, signature_namespace={"struct": struct})  # type: ignore[valid-type]
            def create_rejected_struct(data: JSONBody[struct]) -> None:  # type: ignore[valid-type]
                pass

            Litestar(route_handlers=[create_rejected_struct], openapi_config=None)
        else:

            @get("/", return_dto=MsgspecDTO[struct], signature_namespace={"struct": struct})  # type: ignore[valid-type]
            def read_rejected_struct() -> struct:  # type: ignore[valid-type]
                return struct()

            Litestar(route_handlers=[read_rejected_struct], openapi_config=None)


@pytest.mark.parametrize(
    "mark, config, token_default, expected_body, post_status, expected_seen",
    [
        pytest.param("private", DTOConfig(), {"default": "t"}, {"name": "a"}, 201, "t", id="private"),
        pytest.param("read-only", DTOConfig(), {"default": "t"}, {"name": "a", "token": "x"}, 201, "t", id="read_only"),
        pytest.param("write-only", DTOConfig(), {"default": "t"}, {"name": "a"}, 201, "x", id="write_only"),
        pytest.param(
            "private",
            DTOConfig(forbid_unknown_fields=True),
            {"default": "t"},
            {"name": "a"},
            400,
            None,
            id="private_forbid_unknown_fields",
        ),
        pytest.param("private", DTOConfig(), {}, {"name": "a"}, 500, None, id="private_without_default"),
    ],
)
def test_dto_honours_mark_given_as_string(
    mark: Any,
    config: DTOConfig,
    token_default: dict[str, Any],
    expected_body: dict[str, Any],
    post_status: int,
    expected_seen: str | None,
) -> None:
    model = make_dataclass(
        "Item", [("name", str), ("token", Annotated[str, DTOField(mark=mark)], field(**token_default))]
    )
    seen: dict[str, Any] = {}

    @get("/", return_dto=DataclassDTO[Annotated[model, config]], signature_namespace={"model": model})  # type: ignore[valid-type]
    def read_string_mark() -> model:  # type: ignore[valid-type]
        return model(name="a", token="x")  # type: ignore[no-any-return]

    @post(
        "/",
        dto=DataclassDTO[Annotated[model, config]],  # type: ignore[valid-type]
        return_dto=None,
        signature_namespace={"model": model},
    )
    def create_string_mark(data: JSONBody[model]) -> None:  # type: ignore[valid-type]
        seen["token"] = data.token  # type: ignore[attr-defined]

    with create_test_client(
        [read_string_mark, create_string_mark], openapi_config=None, raise_server_exceptions=False
    ) as client:
        assert client.get("/").json() == expected_body
        assert client.post("/", json={"name": "a", "token": "x"}).status_code == post_status

    assert seen.get("token") == expected_seen


def test_openapi_schema_for_type_with_custom_generic_type(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, List, TypeVar

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from litestar import Litestar, get
from advanced_alchemy.extensions.litestar import SQLAlchemyDTO
from litestar.dto import DTOConfig

T = TypeVar("T")

@dataclass
class WithCount(Generic[T]):
    count: int
    data: list[T]

class Base(DeclarativeBase): ...

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    password: Mapped[str]
    created_at: Mapped[datetime]

class UserDTO(SQLAlchemyDTO[User]):
    config = DTOConfig(exclude={"password", "created_at"})

@get("/users", dto=UserDTO, sync_to_thread=False)
def get_users() -> WithCount[User]:
    return WithCount(
        count=1, data=[User(id=1, name="Litestar User", password="xyz", created_at=datetime.now())]
    )

app = Litestar(route_handlers=[get_users])
"""
    )
    openapi = cast("Litestar", module.app).openapi_schema
    schema = openapi.components.schemas["WithCount_litestar.dto._backend.GetUsersUserResponseBody_"]
    assert not_none(schema.properties).keys() == {"count", "data"}
    model_schema = openapi.components.schemas["GetUsersUserResponseBody"]
    assert not_none(model_schema.properties).keys() == {"id", "name"}


def test_openapi_schema_for_type_with_litestar_response_generic_type(
    create_module: Callable[[str], ModuleType],
) -> None:
    module = create_module("""
from dataclasses import dataclass
from typing import List

from litestar import Litestar, Response, get
from litestar.dto import DataclassDTO, DTOConfig


@dataclass
class Item:
    id: int
    name: str
    secret: str


class ItemReadDTO(DataclassDTO[Item]):
    config = DTOConfig(exclude=["secret"])


@get("/get_items", return_dto=ItemReadDTO)
async def get_items() -> Response[List[Item]]:
    return Response(
        headers={"X-SomeParam": "SomeValue"},
        content=[
            Item(id=1, name="Item 1", secret="123"),
            Item(id=2, name="Item 2", secret="456"),
        ],
    )

app = Litestar(route_handlers=[get_items])
""")

    openapi = cast("Litestar", module.app).openapi_schema
    schema = openapi.components.schemas["GetItemsItemResponseBody"]
    assert not_none(schema.properties).keys() == {"id", "name"}


def test_openapi_schema_for_dto_includes_body_examples(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from uuid import UUID

from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.dto import DataclassDTO
from litestar.openapi.spec import Example
from litestar.params import Body


@dataclass
class Item:
    id: UUID
    name: str


body = Body(
    title="Create item",
    description="Create a new item.",
    examples=[
        Example(
            summary="Post is Ok",
            value={
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "Swatch",
            },
        )
    ],
)


@post()
async def create_item(data: Annotated[Item, body]) -> Item:
    return data


@post("dto", dto=DataclassDTO[Item])
async def create_item_with_dto(data: Annotated[Item, body]) -> Item:
    return data


app = Litestar(route_handlers=[create_item, create_item_with_dto])
"""
    )

    openapi_schema = module.app.openapi_schema
    item_schema = openapi_schema.components.schemas["Item"]
    item_with_dto_schema = openapi_schema.components.schemas["CreateItemWithDtoItemRequestBody"]
    assert item_schema.examples == item_with_dto_schema.examples
