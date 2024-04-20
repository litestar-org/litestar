from uuid import UUID

from dataclasses import dataclass
from litestar.dto import DTOConfig, DataclassDTO


@dataclass
class User:
    first_name: str
    last_name: str
    id: UUID


class PartialUserDTO(DataclassDTO[User]):
    config = DTOConfig(exclude={"id"}, partial=True)