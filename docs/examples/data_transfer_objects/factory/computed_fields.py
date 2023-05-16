from __future__ import annotations

import binascii
import hashlib
import os
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from litestar import Litestar, post
from litestar.dto.factory import DTOConfig, DTOData, dto_field
from litestar.dto.factory.stdlib.dataclass import DataclassDTO


@dataclass
class Person:
    id: UUID
    name: str
    age: int
    hashed_password: bytes = field(metadata=dto_field("write-only"))


def hash_password(password: str) -> bytes:
    """Hash password."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    hashed_password = binascii.hexlify(dk)
    return salt + hashed_password


class WriteDTO(DataclassDTO[Person]):
    """Don't allow client to set the id."""

    config = DTOConfig(
        exclude={"id"},
        computed_fields={"hashed_password": hash_password},
    )


@post("/person", dto=WriteDTO, return_dto=DataclassDTO[Person], sync_to_thread=False)
def create_person(data: DTOData[Person]) -> Person:
    """Create a person."""
    return data.create_instance(id=uuid4())


app = Litestar(route_handlers=[create_person])

# run: /person -H "Content-Type: application/json" -d '{"name":"Peter","age":41,"password":"secret"}'
