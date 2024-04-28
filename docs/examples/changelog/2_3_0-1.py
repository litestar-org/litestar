from pydantic import BaseModel
from pydantic.v1 import BaseModel as BaseModelV1

from litestar import get


class V1Foo(BaseModelV1):
    bar: str


class V2Foo(BaseModel):
    bar: str


@get("/1")
def foo_v1(data: V1Foo) -> V1Foo:
    return data


@get("/2")
def foo_v2(data: V2Foo) -> V2Foo:
    return data
