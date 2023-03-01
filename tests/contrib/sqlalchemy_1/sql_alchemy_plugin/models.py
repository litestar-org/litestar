from dataclasses import dataclass
from typing import List

from sqlalchemy import JSON, Column, Enum, Float, ForeignKey, Integer, String, Table
from sqlalchemy.dialects import mysql, postgresql, sqlite
from sqlalchemy.orm import as_declarative, declared_attr, registry, relationship

from tests import Species

mapper_registry = registry()


@as_declarative()
class SQLAlchemyBase:
    id: Column

    # Generate the table name from the class name
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


association_table = Table(
    "association",
    SQLAlchemyBase.metadata,
    Column("pet_id", ForeignKey("pet.id")),
    Column("user_id", ForeignKey("user.id")),
)
friendship_table = Table(
    "friendships",
    SQLAlchemyBase.metadata,
    Column("friend_a_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("friend_b_id", Integer, ForeignKey("user.id"), primary_key=True),
)

activities_table = Table(
    "activities",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
)


class Pet(SQLAlchemyBase):
    id = Column(Integer, primary_key=True)
    species = Column(Enum(Species))
    name = Column(String)
    age = Column(Float)
    owner_id = Column(Integer, ForeignKey("user.id"))
    owner: "User" = relationship("User", back_populates="pets", uselist=False)


class WildAnimal(SQLAlchemyBase):
    id = Column(Integer, primary_key=True)
    sa_json = Column(JSON, default={})
    my_json = Column(mysql.JSON, default=[])
    pg_json = Column(postgresql.JSON, default={})
    pg_jsonb = Column(postgresql.JSONB, default=[])
    sl_json = Column(sqlite.JSON, default={})


class Company(SQLAlchemyBase):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    worth = Column(Float)


class User(SQLAlchemyBase):
    id = Column(Integer, primary_key=True)
    name = Column(String, default="moishe")
    pets: List[Pet] = relationship("Pet", back_populates="owner", uselist=True)
    friends: List["User"] = relationship(
        "User",
        secondary=friendship_table,
        primaryjoin=id == friendship_table.c.friend_a_id,
        secondaryjoin=id == friendship_table.c.friend_b_id,
        uselist=True,
    )
    company_id = Column(Integer, ForeignKey("company.id"))
    company: Company = relationship("Company")


@dataclass
class Activity:
    id: int
    name: str


mapper_registry.map_imperatively(Activity, activities_table)
