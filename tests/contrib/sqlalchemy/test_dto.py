from __future__ import annotations

import sys
from datetime import date, datetime
from typing import TYPE_CHECKING, ClassVar, List, TypeVar
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, declared_attr, mapped_column
from typing_extensions import Annotated

from litestar import post
from litestar.contrib.sqlalchemy.dto import DataT, SQLAlchemyDTO
from litestar.dto.factory import DTOConfig, DTOField, Mark, Purpose
from litestar.dto.factory.field import DTO_FIELD_META_KEY
from litestar.serialization import encode_json
from litestar.utils.signature import ParsedType

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType
    from typing import Any, Collection

    from litestar.connection import Request
    from litestar.testing import RequestFactory


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
def fx_raw_author() -> dict[str, Any]:
    return {
        "id": "97108ac1-ffcb-411d-8b1e-d9183399f63b",
        "name": "Agatha Christie",
        "dob": "1890-09-15",
        "created": "0001-01-01T00:00:00",
        "updated": "0001-01-01T00:00:00",
    }


T = TypeVar("T")


async def get_model_from_dto(
    dto_type: SQLAlchemyDTO[DataT], annotation: Any, connection: Request[Any, Any, Any]
) -> DataT | Collection[DataT]:
    @post(signature_namespace={"annotation": annotation})
    def handler(data: annotation) -> annotation:
        return data

    connection.scope["route_handler"] = handler
    dto_type.on_registration(ParsedType(annotation), handler)
    dto_instance = await dto_type.from_connection(connection)
    return dto_instance._data


def assert_model_values(model_instance: DeclarativeBase, expected_values: dict[str, Any]) -> None:
    assert {k: v for k, v in model_instance.__dict__.items() if not k.startswith("_")} == expected_values


async def test_model_dto(
    author_model: type[DeclarativeBase], raw_author: dict[str, Any], request_factory: RequestFactory
) -> None:
    model = await get_model_from_dto(SQLAlchemyDTO[author_model], author_model, request_factory.post(data=raw_author))
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


async def test_model_write_dto(
    author_model: type[DeclarativeBase], raw_author: dict[str, Any], request_factory: RequestFactory
) -> None:
    config = DTOConfig(purpose=Purpose.WRITE)
    model = await get_model_from_dto(
        SQLAlchemyDTO[Annotated[author_model, config]], author_model, request_factory.post(data=raw_author)
    )
    assert_model_values(
        model,
        {
            "name": "Agatha Christie",
            "dob": date(1890, 9, 15),
        },
    )


async def test_model_read_dto(
    author_model: type[DeclarativeBase], raw_author: dict[str, Any], request_factory: RequestFactory
) -> None:
    config = DTOConfig(purpose=Purpose.READ)
    dto_type = SQLAlchemyDTO[Annotated[author_model, config]]
    model = await get_model_from_dto(dto_type, author_model, request_factory.post(data=raw_author))
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


async def test_model_list_dto(author_model: type[DeclarativeBase], request_factory: RequestFactory) -> None:
    dto_type = SQLAlchemyDTO[author_model]
    request = request_factory.post(
        data=[
            {
                "id": "97108ac1-ffcb-411d-8b1e-d9183399f63b",
                "name": "Agatha Christie",
                "dob": "1890-09-15",
                "created": "0001-01-01T00:00:00",
                "updated": "0001-01-01T00:00:00",
            }
        ]
    )
    dto_data = await get_model_from_dto(dto_type, List[author_model], request)
    assert isinstance(dto_data, list)
    assert_model_values(
        dto_data[0],
        {
            "id": UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"),
            "created": datetime(1, 1, 1, 0, 0),
            "updated": datetime(1, 1, 1, 0, 0),
            "name": "Agatha Christie",
            "dob": date(1890, 9, 15),
        },
    )


async def test_dto_exclude(
    author_model: type[DeclarativeBase], raw_author: bytes, request_factory: RequestFactory
) -> None:
    config = DTOConfig(exclude={"id"})
    model = await get_model_from_dto(
        SQLAlchemyDTO[Annotated[author_model, config]], author_model, request_factory.post(data=raw_author)
    )
    assert "id" not in vars(model)


async def test_write_dto_field_default(base: type[DeclarativeBase], request_factory: RequestFactory) -> None:
    class Model(base):
        field: Mapped[int] = mapped_column(default=3)

    dto_type = SQLAlchemyDTO[Annotated[Model, DTOConfig(purpose=Purpose.WRITE, include={"field"})]]
    model = await get_model_from_dto(dto_type, Model, request_factory.post(data={"a": "b"}))
    assert_model_values(model, {"field": 3})


async def test_write_dto_for_model_field_factory_default(
    base: type[DeclarativeBase], request_factory: RequestFactory
) -> None:
    val = uuid4()

    class Model(base):
        field: Mapped[UUID] = mapped_column(default=lambda: val)

    dto_type = SQLAlchemyDTO[Annotated[Model, DTOConfig(purpose=Purpose.WRITE, include={"field"})]]
    model = await get_model_from_dto(dto_type, Model, request_factory.post(data={"a": "b"}))
    assert_model_values(model, {"field": val})


async def test_write_dto_for_model_field_unsupported_default(
    base: type[DeclarativeBase], request_factory: RequestFactory
) -> None:
    """Test for error condition where we don't know what to do with a default
    type."""

    class Model(base):
        field: Mapped[datetime] = mapped_column(default=func.now())

    with pytest.raises(ValueError):
        await get_model_from_dto(
            SQLAlchemyDTO[Annotated[Model, DTOConfig(purpose=Purpose.WRITE)]], Model, request_factory.get()
        )


@pytest.mark.parametrize("purpose", [None, Purpose.WRITE, Purpose.READ])
async def test_dto_for_private_model_field(
    purpose: Purpose | None, base: type[DeclarativeBase], request_factory: RequestFactory
) -> None:
    class Model(base):
        field: Mapped[datetime] = mapped_column(
            info={DTO_FIELD_META_KEY: DTOField(mark=Mark.PRIVATE)},
        )

    dto_type = SQLAlchemyDTO[Annotated[Model, DTOConfig(purpose=purpose)]]
    request = request_factory.post(
        data={
            "id": "97108ac1-ffcb-411d-8b1e-d9183399f63b",
            "created": "0001-01-01T00:00:00",
            "updated": "0001-01-01T00:00:00",
            "field": "0001-01-01T00:00:00",
        }
    )
    assert "field" not in vars(await get_model_from_dto(dto_type, Model, request))

    dto_instance = dto_type(
        data=Model(
            id=UUID("0956ca9e-5671-4d7d-a862-b98e6368ed2c"),
            created=datetime.min,
            updated=datetime.min,
            field=datetime.min,
        )
    )
    serializable = dto_instance.to_encodable_type(request)
    assert b"field" not in encode_json(serializable)


@pytest.mark.parametrize("purpose", [Purpose.WRITE, Purpose.READ, None])
async def test_dto_for_non_mapped_model_field(
    purpose: Purpose | None, base: type[DeclarativeBase], request_factory: RequestFactory
) -> None:
    class Model(base):
        field: ClassVar[datetime]

    dto_type = SQLAlchemyDTO[Annotated[Model, DTOConfig(purpose=purpose)]]
    assert "field" not in vars(
        await get_model_from_dto(
            dto_type,
            Model,
            request_factory.post(
                data={
                    "id": "97108ac1-ffcb-411d-8b1e-d9183399f63b",
                    "created": "0001-01-01T00:00:00",
                    "updated": "0001-01-01T00:00:00",
                    "field": "0001-01-01T00:00:00",
                }
            ),
        )
    )


async def test_dto_mapped_as_dataclass_model_type(base: type[DeclarativeBase], request_factory: RequestFactory) -> None:
    """Test declare pydantic type on `dto.DTOField`."""

    class Model(base, MappedAsDataclass):
        clz_var: ClassVar[str]
        field: Mapped[str]

    dto_type = SQLAlchemyDTO[Annotated[Model, DTOConfig(purpose=Purpose.WRITE)]]
    model = await get_model_from_dto(dto_type, Model, request_factory.post(data={"clz_var": "nope", "field": "yep"}))
    assert_model_values(model, {"field": "yep"})


async def test_to_mapped_model_with_collection_relationship(
    base: type[DeclarativeBase], create_module: Callable[[str], ModuleType], request_factory: RequestFactory
) -> None:
    """Test building a DTO with collection relationship, and parsing data."""

    module = create_module(
        """
from __future__ import annotations

from typing import List

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing_extensions import Annotated

from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto.factory import DTOConfig, Purpose

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

    model = await get_model_from_dto(
        module.dto_type,
        module.B,
        request_factory.post(data={"id": 1, "a": [{"id": 2, "b_id": 1}, {"id": 3, "b_id": 1}]}),
    )
    assert isinstance(model, module.B)
    assert len(model.a) == 2
    assert all(isinstance(val, module.A) for val in model.a)


async def test_to_mapped_model_with_scalar_relationship(
    create_module: Callable[[str], ModuleType], request_factory: RequestFactory
) -> None:
    """Test building DTO with Scalar relationship, and parsing data."""

    module = create_module(
        """
from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing_extensions import Annotated

from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto.factory import DTOConfig, Purpose

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
    model = await get_model_from_dto(
        module.dto_type, module.B, request_factory.post(data={"id": 2, "a_id": 1, "a": {"id": 1}})
    )
    assert isinstance(model, module.B)
    assert isinstance(model.a, module.A)


async def test_dto_mapped_union(create_module: Callable[[str], ModuleType], request_factory: RequestFactory) -> None:
    """Test where a column type declared as e.g., `Mapped[str | None]`."""

    module = create_module(
        """
from __future__ import annotations

from typing import Union

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing_extensions import Annotated

from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto.factory import DTOConfig, Purpose

class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)

class A(Base):
    __tablename__ = "a"
    a: Mapped[Union[str, None]]

dto_type = SQLAlchemyDTO[A]
    """
    )
    model = await get_model_from_dto(module.dto_type, module.A, request_factory.post(data={"id": 1}))
    assert vars(model)["a"] is None


@pytest.mark.skipif(sys.version_info < (3, 10), reason="requires python3.10 or higher")
async def test_dto_mapped_union_type(
    create_module: Callable[[str], ModuleType], request_factory: RequestFactory
) -> None:
    """Test where a column type declared as e.g., `Mapped[str | None]`."""

    module = create_module(
        """
from __future__ import annotations

from typing import Union

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing_extensions import Annotated

from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto.factory import DTOConfig, Purpose

class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)

class A(Base):
    __tablename__ = "a"
    a: Mapped[str | None]

dto_type = SQLAlchemyDTO[A]
    """
    )
    model = await get_model_from_dto(module.dto_type, module.A, request_factory.post(data={"id": 1}))
    assert vars(model)["a"] is None
    model = await get_model_from_dto(module.dto_type, module.A, request_factory.post(data={"id": 1, "a": "a"}))
    assert vars(model)["a"] == "a"


async def test_dto_self_referencing_relationships(
    create_module: "Callable[[str], ModuleType]", request_factory: RequestFactory
) -> None:
    module = create_module(
        """
from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing_extensions import Annotated

from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto.factory import DTOConfig, Purpose

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
    request = request_factory.post(data={"id": 1, "b_id": 1, "b": {"id": 1, "a": {"id": 1, "b_id": 1}}})
    model = await get_model_from_dto(module.dto_type, module.A, request)
    assert isinstance(model, module.A)
    assert isinstance(model.b, module.B)
    assert isinstance(model.b.a, module.A)
    encodable_type = module.dto_type(data=model).to_encodable_type(request)
    assert encodable_type.id == 1
    assert encodable_type.b_id == 1
    assert encodable_type.b.id == 1


async def test_dto_optional_relationship_with_none_value(
    create_module: Callable[[str], ModuleType], request_factory: RequestFactory
) -> None:
    module = create_module(
        """
from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing_extensions import Annotated

from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto.factory import DTOConfig, Purpose

class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)

class A(Base):
    __tablename__ = "a"

class B(Base):
    __tablename__ = "b"
    a_id: Mapped[Optional[int]] = mapped_column(ForeignKey("a.id"))
    a: Mapped[Optional[A]] = relationship(A)

dto_type = SQLAlchemyDTO[Annotated[B, DTOConfig(purpose=Purpose.WRITE)]]
"""
    )
    model = await get_model_from_dto(
        module.dto_type,
        module.B,
        request_factory.post(data={"id": 2, "a_id": None, "a": None}),
    )
    assert isinstance(model, module.B)
    assert model.a is None


async def test_forward_ref_relationship_resolution(
    create_module: Callable[[str], ModuleType], request_factory: RequestFactory
) -> None:
    """Testing that classes related to the mapped class for the dto are considered for forward-ref resolution.

    The key part of this test is that the `B` type is only imported inside an `if TYPE_CHECKING:` block
    in `a_module`, so it should not be available for forward-ref resolution when `a_module` is imported. This
    works due to related mapped classes (via `mapper.registry.mappers`) being added to foward-ref resolution
    namespace.
    """
    base_module = create_module(
        """
from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)
"""
    )

    b_module = create_module(
        f"""
from __future__ import annotations

from {base_module.__name__} import Base

class B(Base):
    __tablename__ = "b"
"""
    )

    a_module = create_module(
        f"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing_extensions import Annotated

from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.dto.factory import DTOConfig, Purpose

from {base_module.__name__} import Base

if TYPE_CHECKING:
    from {b_module.__name__} import B

class A(Base):
    __tablename__ = "a"
    b_id: Mapped[int] = mapped_column(ForeignKey("b.id"))
    b: Mapped[B] = relationship()

dto_type = SQLAlchemyDTO[Annotated[A, DTOConfig(purpose=Purpose.WRITE)]]
"""
    )

    model = await get_model_from_dto(
        a_module.dto_type,
        a_module.A,
        request_factory.post(data={"id": 1, "b_id": 2, "b": {"id": 2}}),
    )
    assert isinstance(model, a_module.A)
    assert isinstance(model.b, b_module.B)
