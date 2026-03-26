from enum import StrEnum
from typing import Annotated

from litestar import Litestar, get
from litestar.params import Parameter


class MyEnum(StrEnum):
    """My enum accepts two values"""

    A = "a"
    B = "b"


@get("/")
async def index(
    q1: Annotated[MyEnum, Parameter(description="This is q1", schema_component_key="q1")],
    q2: MyEnum,
    q3: Annotated[MyEnum, Parameter(description="This is q3", schema_component_key="q3")],
) -> None: ...


app = Litestar([index])
