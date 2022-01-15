from pydantic import BaseModel
from sqlalchemy import Column, Enum, Float, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship
from typing_extensions import get_args

from starlite.plugins.sql_alchemy import SQLAlchemyPlugin
from tests import Species
from tests.plugins.sql_alchemy_plugin import SQLAlchemyBase

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


class Pet(SQLAlchemyBase):
    id = Column(Integer, primary_key=True)
    species = Column(Enum(Species))
    name = Column(String)
    age = Column(Float)
    onwer_id = Column(Integer, ForeignKey("user.id"))
    owner = relationship("User", back_populates="pets")


class User(SQLAlchemyBase):
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
    fields = result.__fields__
    friends = fields["friends"]
    assert get_args(friends.outer_type_)  # we assert this is a List[]
    # assert friends.type_ is result
    pets = fields["pets"]
    assert get_args(pets.outer_type_)  # we assert this is a List[]
    assert issubclass(pets.type_, BaseModel)


def test_table_name():
    pet_table = Pet
    user_table = User
    assert pet_table.__tablename__ == "pet" and user_table.__tablename__ == "user"
