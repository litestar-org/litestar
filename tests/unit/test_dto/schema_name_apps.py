from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Final, Generic, TypeVar

import msgspec

from litestar import Controller, Litestar, get, post
from litestar.dto import DataclassDTO, DTOConfig, DTOData, MsgspecDTO
from litestar.params import JSONBody

T = TypeVar("T")


@dataclass
class User:
    name: str
    age: int = 0


@dataclass
class Tag:
    label: str


@dataclass
class Post:
    title: str
    author: User
    editor: User
    tags: list[Tag] = field(default_factory=list)


@dataclass
class Envelope(Generic[T]):
    data: T
    count: int


class Product(msgspec.Struct):
    name: str
    maker: "Maker"


class Maker(msgspec.Struct):
    name: str


class UserDTO(DataclassDTO[User]):
    config = DTOConfig(exclude={"age"})


class NamedPostDTO(DataclassDTO[Post]):
    __schema_name__ = "PublicPost"


def _user() -> User:
    return User(name="a")


def _post() -> Post:
    return Post(title="t", author=_user(), editor=_user())


def single() -> Litestar:
    @get("/users", return_dto=UserDTO, sync_to_thread=False)
    def get_user() -> User:
        return _user()

    @post("/users", dto=UserDTO, sync_to_thread=False)
    def create_user(data: JSONBody[User]) -> User:
        return data

    @post("/users/partial", dto=UserDTO, return_dto=None, sync_to_thread=False)
    def patch_user(data: JSONBody[DTOData[User]]) -> None:
        return None

    @get("/users/all", return_dto=UserDTO, sync_to_thread=False)
    def list_users() -> list[User]:
        return [_user()]

    return Litestar([get_user, create_user, patch_user, list_users])


def nested() -> Litestar:
    @get("/posts", return_dto=DataclassDTO[Post], sync_to_thread=False)
    def get_post() -> Post:
        return _post()

    @post("/posts", dto=DataclassDTO[Post], sync_to_thread=False)
    def create_post(data: JSONBody[Post]) -> Post:
        return data

    return Litestar([get_post, create_post])


def same_handler_name() -> Litestar:
    class FirstController(Controller):
        path = "/first"
        return_dto = UserDTO

        @get(sync_to_thread=False)
        def fetch(self) -> User:
            return _user()

    class SecondController(Controller):
        path = "/second"
        return_dto = UserDTO

        @get(sync_to_thread=False)
        def fetch(self) -> User:
            return _user()

    return Litestar([FirstController, SecondController])


def schema_name() -> Litestar:
    @get("/posts", return_dto=NamedPostDTO, sync_to_thread=False)
    def get_post() -> Post:
        return _post()

    @get("/posts/all", return_dto=NamedPostDTO, sync_to_thread=False)
    def list_posts() -> list[Post]:
        return [_post()]

    return Litestar([get_post, list_posts])


def generic_wrapper() -> Litestar:
    @get("/users", return_dto=UserDTO, sync_to_thread=False)
    def get_wrapped() -> Envelope[User]:
        return Envelope(data=_user(), count=1)

    return Litestar([get_wrapped])


def msgspec_nested() -> Litestar:
    @get("/products", return_dto=MsgspecDTO[Product], sync_to_thread=False)
    def get_product() -> Product:
        return Product(name="p", maker=Maker(name="m"))

    return Litestar([get_product])


def pydantic_nested() -> Litestar:
    import pydantic

    from litestar.plugins.pydantic import PydanticDTO

    class Owner(pydantic.BaseModel):
        name: str

    class Pet(pydantic.BaseModel):
        name: str
        owner: Owner

    @get("/pets", return_dto=PydanticDTO[Pet], sync_to_thread=False)
    def get_pet() -> Pet:
        return Pet(name="p", owner=Owner(name="o"))

    return Litestar([get_pet])


APPS: Final[dict[str, Callable[[], Litestar]]] = {
    "single": single,
    "nested": nested,
    "same_handler_name": same_handler_name,
    "schema_name": schema_name,
    "generic_wrapper": generic_wrapper,
    "msgspec_nested": msgspec_nested,
    "pydantic_nested": pydantic_nested,
}


def _refs(node: Any) -> list[str]:
    if isinstance(node, dict):
        found = [node["$ref"].rsplit("/", 1)[-1]] if "$ref" in node else []
        return found + [ref for value in node.values() for ref in _refs(value)]
    if isinstance(node, list):
        return [ref for value in node for ref in _refs(value)]
    return []


def describe(app: Litestar) -> dict[str, Any]:
    document = app.openapi_schema.to_schema()
    operations = {
        f"{method.upper()} {path}": _refs({key: operation.get(key) for key in ("requestBody", "responses")})
        for path, item in document["paths"].items()
        for method, operation in item.items()
    }
    return {"components": sorted(document["components"]["schemas"]), "operations": operations}
