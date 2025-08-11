from enum import Enum
from typing import Annotated

from litestar import Litestar, get
from litestar.params import Parameter


class MyEnum(str, Enum):
    """My enum accepts two values"""

    A = "a"
    B = "b"


@get("/")
async def index(
    q1: Annotated[MyEnum, Parameter(description="This is q1", schema_component_key="q1")], q2: MyEnum
) -> None: ...


app = Litestar([index])
