# ruff: noqa: UP007
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Optional, Sequence
from unittest.mock import MagicMock

import msgspec
import pytest
from typing_extensions import Annotated

from litestar import patch, post
from litestar.datastructures import UploadFile
from litestar.dto.factory import DTOConfig, DTOData, dto_field
from litestar.dto.factory.stdlib.dataclass import DataclassDTO
from litestar.dto.factory.types import RenameStrategy
from litestar.enums import MediaType, RequestEncodingType
from litestar.params import Body
from litestar.testing import TestClient, create_test_client

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Any, Callable


def test_url_encoded_form_data() -> None:
    @dataclass
    class User:
        name: str
        age: int
        read_only: str = field(default="read-only", metadata=dto_field("read-only"))

    @post(dto=DataclassDTO[User], signature_namespace={"User": User})
    def handler(data: User = Body(media_type=RequestEncodingType.URL_ENCODED)) -> User:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post(
            "/",
            content=b"id=1&name=John&age=42&read_only=whoops",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.json() == {"name": "John", "age": 42, "read_only": "read-only"}


async def test_multipart_encoded_form_data() -> None:
    @dataclass
    class Payload:
        file: UploadFile
        forbidden: UploadFile = field(
            default=UploadFile(content_type="text/plain", filename="forbidden", file_data=b"forbidden"),
            metadata=dto_field("read-only"),
        )

    @post(
        dto=DataclassDTO[Payload], return_dto=None, signature_namespace={"Payload": Payload}, media_type=MediaType.TEXT
    )
    async def handler(data: Payload = Body(media_type=RequestEncodingType.MULTI_PART)) -> bytes:
        return await data.forbidden.read()

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post(
            "/",
            files={"file": b"abc123", "forbidden": b"123abc"},
        )
        assert response.content == b"forbidden"


def test_renamed_field() -> None:
    @dataclass
    class Foo:
        bar: str

    config = DTOConfig(rename_fields={"bar": "baz"})
    dto = DataclassDTO[Annotated[Foo, config]]

    @post(dto=dto, signature_namespace={"Foo": Foo})
    def handler(data: Foo) -> Foo:
        assert data.bar == "hello"
        return data

    with create_test_client(route_handlers=[handler], debug=True) as client:
        response = client.post("/", json={"baz": "hello"})
        assert response.json() == {"baz": "hello"}


@dataclass
class Spam:
    main_id: str = "spam-id"


@dataclass
class Foo:
    bar: str = "hello"
    SPAM: str = "bye"
    spam_bar: str = "welcome"
    spam_model: Optional[Spam] = None


@pytest.mark.parametrize(
    "rename_strategy, instance, tested_fields, data",
    [
        ("upper", Foo(bar="hi"), ["BAR"], {"BAR": "hi"}),
        ("lower", Foo(SPAM="goodbye"), ["spam"], {"spam": "goodbye"}),
        (lambda x: x[::-1], Foo(bar="h", SPAM="bye!"), ["rab", "MAPS"], {"rab": "h", "MAPS": "bye!"}),
        ("camel", Foo(spam_bar="star"), ["spamBar"], {"spamBar": "star"}),
        ("pascal", Foo(spam_bar="star"), ["SpamBar"], {"SpamBar": "star"}),
        ("camel", Foo(spam_model=Spam()), ["spamModel"], {"spamModel": {"mainId": "spam-id"}}),
    ],
)
def test_fields_alias_generator(
    rename_strategy: RenameStrategy,
    instance: Foo,
    tested_fields: list[str],
    data: dict[str, str],
) -> None:
    config = DTOConfig(rename_strategy=rename_strategy)
    dto = DataclassDTO[Annotated[Foo, config]]

    @post(dto=dto, signature_namespace={"Foo": Foo})
    def handler(data: Foo) -> Foo:
        assert data.bar == instance.bar
        assert data.SPAM == instance.SPAM
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response_callback = client.post("/", json=data)
        assert all(response_callback.json()[f] == data[f] for f in tested_fields)


def test_dto_data_injection() -> None:
    @dataclass
    class Foo:
        bar: str

    @post(dto=DataclassDTO[Foo], return_dto=None, signature_namespace={"Foo": Foo})
    def handler(data: DTOData[Foo]) -> Foo:
        assert isinstance(data, DTOData)
        assert data.as_builtins() == {"bar": "hello"}
        assert isinstance(data.create_instance(), Foo)
        return data.create_instance()

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"bar": "hello"})
        assert response.json() == {"bar": "hello"}


def test_dto_data_injection_with_nested_model(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from typing import Any, Dict

from typing_extensions import Annotated

from litestar import post
from litestar.dto.factory import DTOConfig, DTOData
from litestar.dto.factory.stdlib import DataclassDTO

@dataclass
class Foo:
    bar: str
    baz: str

@dataclass
class Bar:
    foo: Foo

config = DTOConfig(exclude={"foo.baz"})
dto = DataclassDTO[Annotated[Bar, config]]

@post(dto=dto, return_dto=None)
def handler(data: DTOData[Bar]) -> Dict[str, Any]:
    assert isinstance(data, DTOData)
    return data.as_builtins()
"""
    )

    with create_test_client(route_handlers=[module.handler]) as client:
        resp = client.post("/", json={"foo": {"bar": "hello"}})
        assert resp.status_code == 201
        assert resp.json() == {"foo": {"bar": "hello"}}


def test_dto_data_create_instance_nested_kwargs(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from typing import Any, Dict

from typing_extensions import Annotated

from litestar import post
from litestar.dto.factory import DTOConfig, DTOData
from litestar.dto.factory.stdlib import DataclassDTO

@dataclass
class Foo:
    bar: str
    baz: str

@dataclass
class Bar:
    foo: Foo

config = DTOConfig(exclude={"foo.baz"})
dto = DataclassDTO[Annotated[Bar, config]]

@post(dto=dto, return_dto=None)
def handler(data: DTOData[Bar]) -> Dict[str, Any]:
    assert isinstance(data, DTOData)
    res = data.create_instance(foo__baz="world")
    assert res.foo.baz == "world"
    return res
"""
    )

    with create_test_client(route_handlers=[module.handler]) as client:
        resp = client.post("/", json={"foo": {"bar": "hello"}})
        assert resp.status_code == 201
        assert resp.json() == {"foo": {"bar": "hello", "baz": "world"}}


def test_dto_data_with_url_encoded_form_data() -> None:
    @dataclass
    class User:
        name: str
        age: int
        read_only: str = field(default="read-only", metadata=dto_field("read-only"))

    @post(dto=DataclassDTO[User], signature_namespace={"User": User})
    def handler(data: DTOData[User] = Body(media_type=RequestEncodingType.URL_ENCODED)) -> User:
        return data.create_instance()

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post(
            "/",
            content=b"id=1&name=John&age=42&read_only=whoops",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.json() == {"name": "John", "age": 42, "read_only": "read-only"}


def test_dto_data_with_patch_request() -> None:
    @dataclass
    class User:
        name: str
        age: int
        read_only: str = field(default="read-only", metadata=dto_field("read-only"))

    class PatchDTO(DataclassDTO[User]):
        config = DTOConfig(partial=True)

    @patch(dto=PatchDTO, return_dto=None, signature_namespace={"User": User})
    def handler(data: DTOData[User]) -> User:
        return data.update_instance(User(name="John", age=42))

    with create_test_client(route_handlers=[handler]) as client:
        response = client.patch("/", json={"age": 41, "read_only": "whoops"})
        assert response.json() == {"name": "John", "age": 41, "read_only": "read-only"}


def test_dto_openapi_model_name_collision() -> None:
    @dataclass
    class Bar:
        id: int
        foo: str

    write_dto = DataclassDTO[Annotated[Bar, DTOConfig(exclude={"id"})]]
    read_dto = DataclassDTO[Bar]

    @post(dto=write_dto, return_dto=read_dto, signature_namespace={"Bar": Bar})
    def handler(data: Bar) -> Bar:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.get("/schema/openapi.json")
        schemas = list(response.json()["components"]["schemas"].values())
        assert len(schemas) == 2
        assert schemas[0] != schemas[1]
        assert all(
            k.startswith(
                "tests.unit.test_dto.test_factory.test_integration.test_dto_openapi_model_name_collision.<locals>.Bar"
            )
            for k in response.json()["components"]["schemas"]
        )


def test_url_encoded_form_data_patch_request() -> None:
    @dataclass
    class User:
        name: str
        age: int
        read_only: str = field(default="read-only", metadata=dto_field("read-only"))

    dto = DataclassDTO[Annotated[User, DTOConfig(partial=True)]]

    @post(dto=dto, return_dto=None, signature_namespace={"User": User, "dict": Dict})
    def handler(data: DTOData[User] = Body(media_type=RequestEncodingType.URL_ENCODED)) -> dict[str, Any]:
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

    @post(dto=DataclassDTO[User], signature_namespace={"User": User})
    def handler(data: Sequence[User]) -> Sequence[User]:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json=[{"name": "John", "age": 42}])
        assert response.json() == [{"name": "John", "age": 42}]


def test_dto_private_fields() -> None:
    @dataclass
    class Foo:
        bar: str
        _baz: int

    mock = MagicMock()

    @post(dto=DataclassDTO[Foo], return_dto=None, signature_namespace={"Foo": Foo})
    def handler(data: DTOData[Foo]) -> Foo:
        mock.received_data = data.as_builtins()
        return data.create_instance(_baz=42)

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"bar": "hello", "_baz": "world"})
        assert response.status_code == 201
        assert response.json() == {"bar": "hello"}

    assert mock.received_data == {"bar": "hello"}


def test_dto_private_fields_disabled() -> None:
    @dataclass
    class Foo:
        bar: str
        _baz: int

    @post(
        dto=DataclassDTO[Annotated[Foo, DTOConfig(underscore_fields_private=False)]],
        signature_namespace={"Foo": Foo},
    )
    def handler(data: Foo) -> Foo:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"bar": "hello", "_baz": 42})
        assert response.status_code == 201
        assert response.json() == {"bar": "hello", "_baz": 42}


def test_dto_concrete_builtin_collection_types() -> None:
    @dataclass
    class Foo:
        bar: dict
        baz: list

    @post(
        dto=DataclassDTO[Annotated[Foo, DTOConfig(underscore_fields_private=False)]],
        signature_namespace={"Foo": Foo},
    )
    def handler(data: Foo) -> Foo:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"bar": {"a": 1, "b": [1, 2, 3]}, "baz": [4, 5, 6]})
        assert response.status_code == 201
        assert response.json() == {"bar": {"a": 1, "b": [1, 2, 3]}, "baz": [4, 5, 6]}


def test_dto_classic_pagination(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from typing import List

from typing_extensions import Annotated

from litestar import Litestar, get
from litestar.dto.factory import DTOConfig
from litestar.dto.factory.stdlib import DataclassDTO
from litestar.pagination import ClassicPagination

@dataclass
class User:
    name: str
    age: int

@get(dto=DataclassDTO[Annotated[User, DTOConfig(exclude={"age"})]])
def handler() -> ClassicPagination[User]:
    return ClassicPagination(
        items=[User(name="John", age=42), User(name="Jane", age=43)],
        page_size=2,
        current_page=1,
        total_pages=20,
    )

app = Litestar(route_handlers=[handler])
"""
    )
    with TestClient(app=module.app) as client:
        response = client.get("/")
        assert response.json() == {
            "items": [{"name": "John"}, {"name": "Jane"}],
            "page_size": 2,
            "current_page": 1,
            "total_pages": 20,
        }


def test_dto_cursor_pagination(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from typing import List
from uuid import UUID

from typing_extensions import Annotated

from litestar import Litestar, get
from litestar.dto.factory import DTOConfig
from litestar.dto.factory.stdlib import DataclassDTO
from litestar.pagination import CursorPagination

@dataclass
class User:
    name: str
    age: int

uuid = UUID("00000000-0000-0000-0000-000000000000")

@get(dto=DataclassDTO[Annotated[User, DTOConfig(exclude={"age"})]])
def handler() -> CursorPagination[UUID, User]:
    return CursorPagination(
        items=[User(name="John", age=42), User(name="Jane", age=43)],
        results_per_page=2,
        cursor=uuid,
    )

app = Litestar(route_handlers=[handler])
"""
    )
    with TestClient(app=module.app) as client:
        response = client.get("/")
        assert response.json() == {
            "items": [{"name": "John"}, {"name": "Jane"}],
            "results_per_page": 2,
            "cursor": "00000000-0000-0000-0000-000000000000",
        }


def test_dto_offset_pagination(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from typing import List

from typing_extensions import Annotated

from litestar import Litestar, get
from litestar.dto.factory import DTOConfig
from litestar.dto.factory.stdlib import DataclassDTO
from litestar.pagination import OffsetPagination

@dataclass
class User:
    name: str
    age: int

@get(dto=DataclassDTO[Annotated[User, DTOConfig(exclude={"age"})]])
def handler() -> OffsetPagination[User]:
    return OffsetPagination(
        items=[User(name="John", age=42), User(name="Jane", age=43)],
        limit=2,
        offset=0,
        total=20,
    )

app = Litestar(route_handlers=[handler])
"""
    )
    with TestClient(app=module.app) as client:
        response = client.get("/")
        assert response.json() == {
            "items": [{"name": "John"}, {"name": "Jane"}],
            "limit": 2,
            "offset": 0,
            "total": 20,
        }


def test_dto_generic_dataclass_wrapped_list_response(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from typing import Generic, List, TypeVar

from typing_extensions import Annotated

from litestar import Litestar, get
from litestar.dto.factory import DTOConfig
from litestar.dto.factory.stdlib import DataclassDTO

@dataclass
class User:
    name: str
    age: int

T = TypeVar("T")
V = TypeVar("V")

@dataclass
class Wrapped(Generic[T, V]):
    data: T
    other: V

@get(dto=DataclassDTO[Annotated[User, DTOConfig(exclude={"age"})]])
def handler() -> Wrapped[List[User], int]:
    return Wrapped(
        data=[User(name="John", age=42), User(name="Jane", age=43)],
        other=2,
    )

app = Litestar(route_handlers=[handler])
"""
    )
    with TestClient(app=module.app) as client:
        response = client.get("/")
        assert response.json() == {"data": [{"name": "John"}, {"name": "Jane"}], "other": 2}


def test_dto_generic_dataclass_wrapped_scalar_response(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from typing import Generic, TypeVar

from typing_extensions import Annotated

from litestar import Litestar, get
from litestar.dto.factory import DTOConfig
from litestar.dto.factory.stdlib import DataclassDTO

@dataclass
class User:
    name: str
    age: int

T = TypeVar("T")
V = TypeVar("V")

@dataclass
class Wrapped(Generic[T, V]):
    data: T
    other: V

@get(dto=DataclassDTO[Annotated[User, DTOConfig(exclude={"age"})]])
def handler() -> Wrapped[User, int]:
    return Wrapped(
        data=User(name="John", age=42),
        other=2,
    )

app = Litestar(route_handlers=[handler])
"""
    )
    with TestClient(app=module.app) as client:
        response = client.get("/")
        assert response.json() == {"data": {"name": "John"}, "other": 2}


def test_dto_generic_dataclass_wrapped_scalar_response_with_additional_mapping_data(
    create_module: Callable[[str], ModuleType]
) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from typing import Dict, Generic, TypeVar

from typing_extensions import Annotated

from litestar import Litestar, get
from litestar.dto.factory import DTOConfig
from litestar.dto.factory.stdlib import DataclassDTO

@dataclass
class User:
    name: str
    age: int

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

@dataclass
class Wrapped(Generic[K, V, T]):
    data: T
    other: Dict[K, V]

@get(dto=DataclassDTO[Annotated[User, DTOConfig(exclude={"age"})]])
def handler() -> Wrapped[str, int, User]:
    return Wrapped(
        data=User(name="John", age=42),
        other={"a": 1, "b": 2},
    )

app = Litestar(route_handlers=[handler])
"""
    )
    with TestClient(app=module.app) as client:
        response = client.get("/")
        assert response.json() == {"data": {"name": "John"}, "other": {"a": 1, "b": 2}}


def test_dto_response_wrapped_scalar_return_type(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from typing import Generic, TypeVar

from typing_extensions import Annotated

from litestar import Litestar, Response, get
from litestar.dto.factory import DTOConfig
from litestar.dto.factory.stdlib import DataclassDTO

@dataclass
class User:
    name: str
    age: int

@get(dto=DataclassDTO[Annotated[User, DTOConfig(exclude={"age"})]])
def handler() -> Response[User]:
    return Response(content=User(name="John", age=42))

app = Litestar(route_handlers=[handler])
"""
    )
    with TestClient(app=module.app) as client:
        response = client.get("/")
        assert response.json() == {"name": "John"}


def test_dto_response_wrapped_collection_return_type(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from typing import Generic, List, TypeVar

from typing_extensions import Annotated

from litestar import Litestar, Response, get
from litestar.dto.factory import DTOConfig
from litestar.dto.factory.stdlib import DataclassDTO

@dataclass
class User:
    name: str
    age: int

@get(dto=DataclassDTO[Annotated[User, DTOConfig(exclude={"age"})]])
def handler() -> Response[List[User]]:
    return Response(content=[User(name="John", age=42), User(name="Jane", age=43)])

app = Litestar(route_handlers=[handler])
"""
    )
    with TestClient(app=module.app) as client:
        response = client.get("/")
        assert response.json() == [{"name": "John"}, {"name": "Jane"}]


def test_dto_with_msgspec_and_generic_inherited_models(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from typing import Dict, Generic, TypeVar
from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.dto.factory import DTOConfig
from litestar.dto.factory.stdlib import DataclassDTO
from litestar.contrib.msgspec import MsgspecDTO

from msgspec import Struct

T = TypeVar("T", bound=Struct)

class ClassicNameStyle(Struct):
    first_name: str
    surname: str

class User(Struct, Generic[T]):
    age: int
    data: T

class Superuser(User[ClassicNameStyle]):
    # data: ClassicNameStyle
    pass

class UserDTO(MsgspecDTO[Superuser]):
    pass

@post(dto=UserDTO)
def handler(data: Superuser) -> Superuser:
    return data

app = Litestar(route_handlers=[handler])
"""
    )
    with TestClient(app=module.app) as client:
        data = module.Superuser(data=module.ClassicNameStyle(first_name="A", surname="B"), age=10)
        headers = {}
        headers["Content-Type"] = "application/json; charset=utf-8"
        received = client.post(
            "/",
            content=msgspec.json.encode(data),
            headers=headers,
        )
        print(received.content)
        assert msgspec.json.decode(received.content, type=module.Superuser) == data
