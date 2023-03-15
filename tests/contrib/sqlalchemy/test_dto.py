from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, declared_attr, mapped_column
from typing_extensions import Annotated

from starlite.contrib.sqlalchemy.dto import ModelT, SQLAlchemyDTO
from starlite.dto import DTOConfig, DTOField, Mark, Purpose
from starlite.dto.config import DTO_FIELD_META_KEY
from starlite.enums import MediaType
from starlite.serialization import encode_json

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType


@pytest.fixture(name="base")
def fx_base() -> type[DeclarativeBase]:
    class Base(DeclarativeBase):
        id: Mapped[UUID] = mapped_column(
            default=uuid4, primary_key=True, info={DTO_FIELD_META_KEY: DTOField(mark=Mark.READ_ONLY)}
        )
        created: Mapped[datetime] = mapped_column(
            default=datetime.now, info={DTO_FIELD_META_KEY: DTOField(mark=Mark.READ_ONLY)}
        )
        updated: Mapped[datetime] = mapped_column(
            default=datetime.now, info={DTO_FIELD_META_KEY: DTOField(mark=Mark.READ_ONLY)}
        )

        # noinspection PyMethodParameters
        @declared_attr.directive
        def __tablename__(cls) -> str:  # pylint: disable=no-self-argument
            """Infer table name from class name."""
            return cls.__name__.lower()

    return Base


@pytest.fixture(name="author_model")
def fx_author_model(base: DeclarativeBase) -> type[DeclarativeBase]:
    class Author(base):
        name: Mapped[str]
        dob: Mapped[date]

    return Author


@pytest.fixture(name="raw_author")
def fx_raw_author() -> bytes:
    return b"""{
        "id": "97108ac1-ffcb-411d-8b1e-d9183399f63b",
        "name": "Agatha Christie",
        "dob": "1890-09-15",
        "created": "0001-01-01T00:00:00",
        "updated": "0001-01-01T00:00:00"
    }"""


T = TypeVar("T")


def get_model_from_dto(dto_type: SQLAlchemyDTO[ModelT], raw_data: bytes) -> ModelT:
    dto_type.postponed_cls_init()
    dto_instance = dto_type.from_bytes(raw_data, MediaType.JSON)
    return dto_instance.data


def assert_model_values(model_instance: DeclarativeBase, expected_values: dict[str, Any]) -> None:
    assert {k: v for k, v in model_instance.__dict__.items() if not k.startswith("_")} == expected_values


def test_model_dto(author_model: type[DeclarativeBase], raw_author: bytes) -> None:
    model = get_model_from_dto(SQLAlchemyDTO[author_model], raw_author)
    assert_model_values(
        model,
        {
            "id": UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"),
            "created": datetime(1, 1, 1, 0, 0),
            "updated": datetime(1, 1, 1, 0, 0),
            "name": "Agatha Christie",
            "dob": date(1890, 9, 15),
        },
    )


def test_model_write_dto(author_model: type[DeclarativeBase], raw_author: bytes) -> None:
    config = DTOConfig(purpose=Purpose.WRITE)
    model = get_model_from_dto(SQLAlchemyDTO[Annotated[author_model, config]], raw_author)
    assert_model_values(
        model,
        {
            "name": "Agatha Christie",
            "dob": date(1890, 9, 15),
        },
    )


def test_model_read_dto(author_model: type[DeclarativeBase], raw_author: bytes) -> None:
    config = DTOConfig(purpose=Purpose.READ)
    dto_type = SQLAlchemyDTO[Annotated[author_model, config]]
    model = get_model_from_dto(dto_type, raw_author)
    assert_model_values(
        model,
        {
            "id": UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"),
            "created": datetime(1, 1, 1, 0, 0),
            "updated": datetime(1, 1, 1, 0, 0),
            "name": "Agatha Christie",
            "dob": date(1890, 9, 15),
        },
    )


def test_dto_exclude(author_model: type[DeclarativeBase], raw_author: bytes) -> None:
    config = DTOConfig(exclude={"id"})
    model = get_model_from_dto(SQLAlchemyDTO[Annotated[author_model, config]], raw_author)
    assert "id" not in vars(model)


def test_write_dto_field_default(base: type[DeclarativeBase]) -> None:
    class Model(base):
        field: Mapped[int] = mapped_column(default=3)

    dto_type = SQLAlchemyDTO[Annotated[Model, DTOConfig(purpose=Purpose.WRITE, include={"field"})]]
    model = get_model_from_dto(dto_type, b"{}")
    assert_model_values(model, {"field": 3})


def test_write_dto_for_model_field_factory_default(base: type[DeclarativeBase]) -> None:
    val = uuid4()

    class Model(base):
        field: Mapped[UUID] = mapped_column(default=lambda: val)

    dto_type = SQLAlchemyDTO[Annotated[Model, DTOConfig(purpose=Purpose.WRITE, include={"field"})]]
    model = get_model_from_dto(dto_type, b"{}")
    assert_model_values(model, {"field": val})


def test_write_dto_for_model_field_unsupported_default(base: type[DeclarativeBase]) -> None:
    """Test for error condition where we don't know what to do with a default
    type."""

    class Model(base):
        field: Mapped[datetime] = mapped_column(default=func.now())

    with pytest.raises(ValueError):
        SQLAlchemyDTO[Annotated[Model, DTOConfig(purpose=Purpose.WRITE)]].postponed_cls_init()


@pytest.mark.parametrize("purpose", [None, Purpose.WRITE, Purpose.READ])
def test_dto_for_private_model_field(purpose: Purpose | None, base: type[DeclarativeBase]) -> None:
    class Model(base):
        field: Mapped[datetime] = mapped_column(
            info={DTO_FIELD_META_KEY: DTOField(mark=Mark.PRIVATE)},
        )

    dto_type = SQLAlchemyDTO[Annotated[Model, DTOConfig(purpose=purpose)]]
    dto_type.postponed_cls_init()
    dto_instance = dto_type(
        data=Model(
            id=UUID("0956ca9e-5671-4d7d-a862-b98e6368ed2c"),
            created=datetime.min,
            updated=datetime.min,
            field=datetime.min,
        )
    )
    serializable = dto_instance.to_encodable_type(MediaType.JSON)
    assert b"field" not in encode_json(serializable)
    assert "field" not in vars(
        get_model_from_dto(
            dto_type,
            b"""{"id": "97108ac1-ffcb-411d-8b1e-d9183399f63b",
            "created": "0001-01-01T00:00:00",
            "updated": "0001-01-01T00:00:00",
            "field": "0001-01-01T00:00:00"}""",
        )
    )


@pytest.mark.parametrize("purpose", [Purpose.WRITE, Purpose.READ, None])
def test_dto_for_non_mapped_model_field(purpose: Purpose | None, base: type[DeclarativeBase]) -> None:
    class Model(base):
        field: ClassVar[datetime]

    dto_type = SQLAlchemyDTO[Annotated[Model, DTOConfig(purpose=purpose)]]
    dto_type.postponed_cls_init()
    assert "field" not in vars(
        get_model_from_dto(
            dto_type,
            b"""{"id": "97108ac1-ffcb-411d-8b1e-d9183399f63b",
            "created": "0001-01-01T00:00:00",
            "updated": "0001-01-01T00:00:00",
            "field": "0001-01-01T00:00:00"}""",
        )
    )


def test_dto_mapped_as_dataclass_model_type(base: type[DeclarativeBase]) -> None:
    """Test declare pydantic type on `dto.DTOField`."""

    class Model(base, MappedAsDataclass):
        clz_var: ClassVar[str]
        field: Mapped[str]

    dto_type = SQLAlchemyDTO[Annotated[Model, DTOConfig(purpose=Purpose.WRITE)]]
    model = get_model_from_dto(dto_type, b'{"clz_var": "nope", "field": "yep"}')
    assert_model_values(model, {"field": "yep"})


def test_to_mapped_model_with_collection_relationship(
    base: type[DeclarativeBase], create_module: Callable[[str], ModuleType]
) -> None:
    """Test building a DTO with collection relationship, and parsing data."""

    module = create_module(
        """
from __future__ import annotations

from typing import List

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing_extensions import Annotated

from starlite.contrib.sqlalchemy.dto import SQLAlchemyDTO
from starlite.dto import DTOConfig, Purpose

class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)

class A(Base):
    __tablename__ = "a"
    b_id: Mapped[int] = mapped_column(ForeignKey("b.id"))

class B(Base):
    __tablename__ = "b"
    a: Mapped[List[A]] = relationship("A")

dto_type = SQLAlchemyDTO[Annotated[B, DTOConfig(purpose=Purpose.WRITE)]]
"""
    )

    model = get_model_from_dto(module.dto_type, b'{"id": 1, "a": [{"id": 2, "b_id": 1}, {"id": 3, "b_id": 1}]}')
    assert len(model.a) == 2
    assert all(isinstance(val, module.A) for val in model.a)


def test_to_mapped_model_with_scalar_relationship(create_module: Callable[[str], ModuleType]) -> None:
    """Test building DTO with Scalar relationship, and parsing data."""

    module = create_module(
        """
from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing_extensions import Annotated

from starlite.contrib.sqlalchemy.dto import SQLAlchemyDTO
from starlite.dto import DTOConfig, Purpose

class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)

class A(Base):
    __tablename__ = "a"

class B(Base):
    __tablename__ = "b"
    a_id: Mapped[int] = mapped_column(ForeignKey("a.id"))
    a: Mapped[A] = relationship(A)

dto_type = SQLAlchemyDTO[Annotated[B, DTOConfig(purpose=Purpose.WRITE)]]
"""
    )
    model = get_model_from_dto(module.dto_type, b'{"id":2,"a_id":1,"a":{"id":1}}')
    assert isinstance(model, module.B)
    assert isinstance(model.a, module.A)


def test_dto_mapped_union(create_module: Callable[[str], ModuleType]) -> None:
    """Test where a column type declared as e.g., `Mapped[str | None]`."""

    module = create_module(
        """
from __future__ import annotations

from typing import Union

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing_extensions import Annotated

from starlite.contrib.sqlalchemy.dto import SQLAlchemyDTO
from starlite.dto import DTOConfig, Purpose

class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)

class A(Base):
    __tablename__ = "a"
    a: Mapped[Union[str, None]]

dto_type = SQLAlchemyDTO[A]
    """
    )
    model = get_model_from_dto(module.dto_type, b'{"id":1}')
    assert vars(model)["a"] is None


def test_dto_factory_self_referencing_relationships(
    create_module: "Callable[[str], ModuleType]",
) -> None:
    module = create_module(
        """
from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing_extensions import Annotated

from starlite.contrib.sqlalchemy.dto import SQLAlchemyDTO
from starlite.dto import DTOConfig, Purpose

class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)

class A(Base):
    __tablename__ = "a"
    b_id: Mapped[int] = mapped_column(ForeignKey("b.id"))
    b: Mapped[B] = relationship(back_populates="a")

class B(Base):
    __tablename__ = "b"
    a: Mapped[A] = relationship(back_populates="b")

dto_type = SQLAlchemyDTO[A]
"""
    )
    model = get_model_from_dto(module.dto_type, b'{"id":1,"b_id":1,"b":{"id":1,"a_id":1,"a":{"id":1,"b_id":1}}}')
    assert isinstance(model, module.A)
    assert isinstance(model.b, module.B)
    assert isinstance(model.b.a, module.A)
