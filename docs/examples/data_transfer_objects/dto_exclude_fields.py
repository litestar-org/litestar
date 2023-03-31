from __future__ import annotations

from dataclasses import dataclass

from typing_extensions import Annotated

from starlite.dto.factory import DTOConfig
from starlite.dto.factory.stdlib import DataclassDTO


@dataclass
class MyClass:
    first: int
    second: int


config = DTOConfig(exclude={"first"})

MyClassDTO = DataclassDTO[Annotated[MyClass, config]]
