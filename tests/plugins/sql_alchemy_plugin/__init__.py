from sqlalchemy import Column, Enum, Float, ForeignKey, Integer, String, Table
from sqlalchemy.orm import as_declarative, declared_attr, relationship

from tests import Species


@as_declarative()
class SQLAlchemyBase:
    id: Column

    # Generate the table name from the class name
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()  # type:ignore[no-any-return,attr-defined]


association_table = Table(
    "association",
    SQLAlchemyBase.metadata,  # type:ignore[attr-defined]
    Column("pet_id", ForeignKey("pet.id")),
    Column("user_id", ForeignKey("user.id")),
)
friendship_table = Table(
    "friendships",
    SQLAlchemyBase.metadata,  # type:ignore[attr-defined]
    Column("friend_a_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("friend_b_id", Integer, ForeignKey("user.id"), primary_key=True),
)


class Pet(SQLAlchemyBase):
    id = Column(Integer, primary_key=True)
    species = Column(Enum(Species))
    name = Column(String)
    age = Column(Float)
    owner_id = Column(Integer, ForeignKey("user.id"))
    owner = relationship("User", back_populates="pets", uselist=False)


class Company(SQLAlchemyBase):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    worth = Column(Float)


class User(SQLAlchemyBase):
    id = Column(Integer, primary_key=True)
    name = Column(String, default="moishe")
    pets = relationship("Pet", back_populates="owner", uselist=True)
    friends = relationship(
        "User",
        secondary=friendship_table,
        primaryjoin=id == friendship_table.c.friend_a_id,
        secondaryjoin=id == friendship_table.c.friend_b_id,
        uselist=True,
    )
    company_id = Column(Integer, ForeignKey("company.id"))
    company = relationship("Company")
