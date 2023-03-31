from __future__ import annotations

from dataclasses import dataclass

from typing_extensions import Annotated

from starlite.dto.factory.config import DTOConfig
from starlite.dto.factory.stdlib import DataclassDTO
from starlite.dto.factory.types import FieldDefinition


@dataclass
class MyClass:
    first: int
    second: int


config = DTOConfig(field_definitions=[FieldDefinition(field_name="third", field_type=str)])

MyClassDTO = DataclassDTO[Annotated[MyClass, config]]
