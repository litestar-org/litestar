from __future__ import annotations

from dataclasses import dataclass

from typing_extensions import Annotated

from starlite.dto.factory import DTOConfig
from starlite.dto.factory.stdlib import DataclassDTO
from starlite.dto.factory.types import FieldDefinition


@dataclass
class MyClass:
    first: int
    second: int


config = DTOConfig(field_mapping={"first": "third", "second": FieldDefinition(field_name="fourth", field_type=float)})

MyClassDTO = DataclassDTO[Annotated[MyClass, config]]
