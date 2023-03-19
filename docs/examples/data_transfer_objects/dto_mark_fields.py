from __future__ import annotations

from dataclasses import dataclass, field

from typing_extensions import Annotated

from starlite.dto.config import DTOConfig, dto_field
from starlite.dto.enums import Purpose
from starlite.dto.stdlib.dataclass import DataclassDTO


@dataclass
class Company:
    id: int = field(metadata=dto_field("read-only"))
    name: str
    worth: float
    super_sensitive: str = field(metadata=dto_field("private"))


config = DTOConfig(purpose=Purpose.WRITE)

CompanyDTO = DataclassDTO[Annotated[Company, config]]
