from pydantic import BaseModel
from sqlalchemy import Column, Enum, Float, ForeignKey, Integer, String, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from starlite.plugins.sql_alchemy import SQLAlchemyPlugin
from tests import Species

Base = declarative_base()

association_table = Table(
    "association", Base.metadata, Column("pet_id", ForeignKey("pet.id")), Column("user_id", ForeignKey("user.id"))
)

friendship_table = Table(
    "friendships",
    Base.metadata,
    Column("friend_a_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("friend_b_id", Integer, ForeignKey("user.id"), primary_key=True),
)


class Pet(Base):
    __tablename__ = "pet"

    id = Column(Integer, primary_key=True)
    species = Column(Enum(Species))
    name = Column(String)
    age = Column(Float)
    onwer_id = Column(Integer, ForeignKey("user.id"))
    owner = relationship("User", back_populates="pets")


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    pets = relationship(
        "Pet",
        back_populates="owner",
    )
    friends = relationship(
        "User",
        secondary=friendship_table,
        primaryjoin=id == friendship_table.c.friend_a_id,
        secondaryjoin=id == friendship_table.c.friend_b_id,
    )


def test_relationship():
    result = SQLAlchemyPlugin().to_pydantic_model_class(model_class=User)
    assert issubclass(result, BaseModel)
