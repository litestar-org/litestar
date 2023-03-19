from __future__ import annotations

from dataclasses import dataclass

from starlite.dto.stdlib.dataclass import DataclassDTO


@dataclass
class Company:
    id: int
    name: str
    worth: float


CompanyDTO = DataclassDTO[Company]
