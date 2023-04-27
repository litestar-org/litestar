from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from litestar.dto.factory.stdlib.dataclass import DataclassDTO


@dataclass
class User:
    id: UUID
    name: str


UserDTO = DataclassDTO[User]
UserReturnDTO = DataclassDTO[User]
