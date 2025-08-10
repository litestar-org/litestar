from dataclasses import dataclass
from typing import List

import msgspec
import pytest
from sqlalchemy import ForeignKey
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
from typing_extensions import Annotated

from litestar import post
from litestar.dto import DataclassDTO, DTOConfig
from litestar.testing import create_test_client

try:
    from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
except ImportError:
    from litestar.plugins.sqlalchemy import SQLAlchemyDTO


class Base(DeclarativeBase):
    pass


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str]
    roles: Mapped[List[Role]] = relationship()


@dataclass
class SingleUserContainer:
    user: User
    additional_info: str


@dataclass
class MultiUsersContainer:
    users: List[User]
    additional_info: str


@pytest.fixture
def user_data() -> User:
    return User(
        id=1,
        name="Test User",
        email="test@example.com",
        roles=[
            Role(id=1, name="Admin"),
            Role(id=2, name="SuperAdmin"),
        ],
    )


@pytest.fixture
def single_user_container_data(user_data: User) -> SingleUserContainer:
    return SingleUserContainer(user=user_data, additional_info="Additional information")


@pytest.fixture
def multi_users_container_data(user_data: User) -> MultiUsersContainer:
    return MultiUsersContainer(users=[user_data, user_data], additional_info="Additional information")


def test_dto_with_custom_dto_factories(
    single_user_container_data: SingleUserContainer,
    multi_users_container_data: MultiUsersContainer,
    use_experimental_dto_backend: bool,
) -> None:
    custom_dto_factories = {
        User: SQLAlchemyDTO[
            Annotated[
                User,
                DTOConfig(experimental_codegen_backend=use_experimental_dto_backend),
            ]
        ],
        Role: SQLAlchemyDTO[
            Annotated[
                Role,
                DTOConfig(experimental_codegen_backend=use_experimental_dto_backend),
            ]
        ],
    }

    @post(
        path="/single-user",
        dto=DataclassDTO[
            Annotated[
                SingleUserContainer,
                DTOConfig(
                    max_nested_depth=2,
                    experimental_codegen_backend=use_experimental_dto_backend,
                    custom_dto_factories=custom_dto_factories,
                ),
            ]
        ],
    )
    def handler1(data: SingleUserContainer) -> SingleUserContainer:
        return data

    @post(
        path="/multi-users",
        dto=DataclassDTO[
            Annotated[
                MultiUsersContainer,
                DTOConfig(
                    max_nested_depth=2,
                    experimental_codegen_backend=use_experimental_dto_backend,
                    custom_dto_factories=custom_dto_factories,
                ),
            ]
        ],
    )
    def handler2(data: MultiUsersContainer) -> MultiUsersContainer:
        return data

    with create_test_client(
        [
            handler1,
            handler2,
        ]
    ) as client:
        user_dict = {
            "additional_info": single_user_container_data.additional_info,
            "user": {
                "id": single_user_container_data.user.id,
                "name": single_user_container_data.user.name,
                "email": single_user_container_data.user.email,
                "roles": [
                    {"id": role.id, "name": role.name, "user_id": single_user_container_data.user.id}
                    for role in single_user_container_data.user.roles
                ],
            },
        }
        received = client.post(
            "/single-user",
            headers={"Content-Type": "application/json; charset=utf-8"},
            content=msgspec.json.encode(user_dict),
        )
        assert received.json() == user_dict

        multi_users_dict = {
            "additional_info": multi_users_container_data.additional_info,
            "users": [
                {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "roles": [{"id": role.id, "name": role.name, "user_id": user.id} for role in user.roles],
                }
                for user in multi_users_container_data.users
            ],
        }
        received = client.post(
            "/multi-users",
            headers={"Content-Type": "application/json; charset=utf-8"},
            content=msgspec.json.encode(multi_users_dict),
        )

        assert received.json() == multi_users_dict
