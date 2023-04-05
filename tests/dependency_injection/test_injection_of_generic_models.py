from typing import Generic, Optional, Type, TypeVar

from pydantic import BaseModel
from pydantic.generics import GenericModel

from starlite import get
from starlite.di import Provide
from starlite.status_codes import HTTP_200_OK
from starlite.testing import create_test_client

T = TypeVar("T")


class Store(GenericModel, Generic[T]):
    """Abstract store."""

    model: Type[T]

    def get(self, value_id: str) -> Optional[T]:
        raise NotImplementedError


class Item(BaseModel):
    name: str


class DictStore(Store[Item]):
    """In-memory store implementation."""

    def get(self, value_id: str) -> Optional[Item]:
        return None


@get("/")
def root(store: DictStore) -> Optional[Item]:
    assert isinstance(store, DictStore)
    return store.get("0")


def get_item_store() -> DictStore:
    return DictStore(model=Item)  # type: ignore


def test_generic_model_injection() -> None:
    with create_test_client(root, dependencies={"store": Provide(get_item_store, use_cache=True)}) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
