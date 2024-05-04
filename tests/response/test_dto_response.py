from sys import version_info
from typing import Any, Iterable, List, Tuple

import pytest
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, declarative_base

from starlite import DTOFactory, HTTPException, create_test_client, get, post
from starlite.plugins.sql_alchemy import SQLAlchemyConfig, SQLAlchemyPlugin
from starlite.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND
from tests import Person, PersonFactory

factory = DTOFactory()
PersonDTO = factory(name="PersonDTO", source=Person)


@pytest.mark.parametrize("data", (PersonFactory.build(), PersonFactory.build().dict()))
def test_dto_singleton_response(data: Any) -> None:
    @get("/")
    def handler() -> PersonDTO:  # type: ignore
        return data  # type: ignore

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert PersonDTO(**response.json())


if version_info >= (3, 10):
    py_310_plus_annotation = [
        (PersonFactory.batch(5), list[PersonDTO]),  # type: ignore
        ([p.dict() for p in PersonFactory.batch(5)], list[PersonDTO]),  # type: ignore
        (PersonFactory.batch(5), tuple[PersonDTO, ...]),  # type: ignore
        ([p.dict() for p in PersonFactory.batch(5)], tuple[PersonDTO, ...]),  # type: ignore
    ]
else:
    py_310_plus_annotation = []


@pytest.mark.parametrize(
    "data, annotation",
    (
        (PersonFactory.batch(0), List[PersonDTO]),  # type: ignore
        (PersonFactory.batch(5), List[PersonDTO]),  # type: ignore
        ([p.dict() for p in PersonFactory.batch(5)], List[PersonDTO]),  # type: ignore
        (PersonFactory.batch(5), Tuple[PersonDTO, ...]),
        ([p.dict() for p in PersonFactory.batch(5)], Tuple[PersonDTO, ...]),
        (PersonFactory.batch(5), Iterable[PersonDTO]),  # type: ignore
        ([p.dict() for p in PersonFactory.batch(5)], Iterable[PersonDTO]),  # type: ignore
        *py_310_plus_annotation,
    ),
)
def test_dto_list_response(data: Any, annotation: Any) -> None:
    @get("/")
    def handler() -> annotation:
        return data

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        results = [PersonDTO(**p) for p in response.json()]
        assert results == data


def test_dto_response_with_the_sqla_plugin() -> None:
    Base = declarative_base()

    sqlalchemy_config = SQLAlchemyConfig(
        connection_string="sqlite+aiosqlite:///test.sqlite", dependency_key="async_session"
    )
    sqlalchemy_plugin = SQLAlchemyPlugin(config=sqlalchemy_config)
    dto_factory = DTOFactory(plugins=[sqlalchemy_plugin])

    class User(Base):  # pyright: ignore
        __tablename__ = "user"
        id: Mapped[int] = Column(Integer, primary_key=True)  # type: ignore
        name: Mapped[str] = Column(String)  # type: ignore
        secret: Mapped[str] = Column(String)  # type: ignore

        class Config:
            orm_mode = True

    CreateUserDTO = dto_factory("CreateUserDTO", User, exclude=["id"])
    ReadUserDTO = dto_factory(name="ReadUserDTO", source=User, exclude=["secret"])

    async def on_startup() -> None:
        """Initialize the database."""
        async with sqlalchemy_config.engine.begin() as conn:  # type: ignore
            await conn.run_sync(Base.metadata.drop_all)  # pyright: ignore
            await conn.run_sync(Base.metadata.create_all)  # pyright: ignore

    async def on_shutdown() -> None:
        async with sqlalchemy_config.engine.begin() as conn:  # type: ignore
            await conn.run_sync(Base.metadata.drop_all)  # pyright: ignore

    @post(path="/users")
    async def create_user(
        data: CreateUserDTO,  # type: ignore
        async_session: AsyncSession,
    ) -> ReadUserDTO:  # type: ignore
        """Create a new user and return it."""
        user: User = data.to_model_instance()  # type: ignore
        async_session.add(user)  # pyright: ignore
        await async_session.commit()
        return user

    @get(path="/users/{user_id:int}")
    async def get_user(user_id: str, async_session: AsyncSession) -> ReadUserDTO:  # type: ignore
        """Get a user by its ID and return it.

        If a user with that ID does not exist, return a 404 response
        """
        result = await async_session.scalars(select(User).where(User.id == user_id))
        user = result.one_or_none()
        if not user:
            raise HTTPException(
                detail=f"User with ID {user_id} not found",
                status_code=HTTP_404_NOT_FOUND,
            )
        return user  # type: ignore

    @get(path="/users/")
    async def get_users(async_session: AsyncSession) -> List[ReadUserDTO]:  # type: ignore
        """Get all users."""
        result = await async_session.scalars(select(User))
        return result.all()

    with create_test_client(
        route_handlers=[create_user, get_user, get_users],
        on_startup=[on_startup],
        on_shutdown=[on_shutdown],
        plugins=[sqlalchemy_plugin],
    ) as client:
        response = client.post("/users", json={"name": "moishe zuchmir", "secret": "123jeronimo"})
        assert response.status_code == HTTP_201_CREATED
        assert ReadUserDTO(**response.json())
        response = client.get("/users")
        assert response.status_code == HTTP_200_OK
        assert len(response.json()) == 1
        data = [ReadUserDTO(**datum) for datum in response.json()]
        assert data
        response = client.get(f"/users/{data[0].id}")  # type: ignore
        assert response.status_code == HTTP_200_OK
        assert ReadUserDTO(**response.json())
