from typing import Optional

from sqlalchemy import Column, Float, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.orm import Mapped, Session, declarative_base, relationship

from starlite import Starlite, get
from starlite.contrib.sqlalchemy_1.config import SQLAlchemyConfig
from starlite.contrib.sqlalchemy_1.plugin import SQLAlchemyPlugin
from starlite.exceptions import HTTPException
from starlite.status_codes import HTTP_404_NOT_FOUND

engine = create_engine("sqlite+pysqlite://")
sqlalchemy_config = SQLAlchemyConfig(engine_instance=engine, use_async_engine=False)
sqlalchemy_plugin = SQLAlchemyPlugin(config=sqlalchemy_config)

Base = declarative_base()


class Company(Base):  # pyright: ignore
    __tablename__ = "company"
    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String)
    worth: Mapped[float] = Column(Float)


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String)
    company_id: Mapped[int] = Column(Integer, ForeignKey("company.id"))
    company: Mapped[Company] = relationship("Company", uselist=False)


async def on_startup() -> None:
    """Initialize the database."""
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        peter = User(id=1, name="Peter", company=Company(name="Peter Co.", worth=0.0))
        session.add(peter)
        session.commit()


@get(path="/user/{user_id:int}")
def get_user(user_id: int, db_session: Session) -> User:
    """Get a user by its ID and return it.

    If a user with that ID does not exist, return a 404 response
    """
    user: Optional[User] = db_session.scalars(select(User).where(User.id == user_id)).one_or_none()
    if not user:
        raise HTTPException(detail=f"User with ID {user} not found", status_code=HTTP_404_NOT_FOUND)
    return user


app = Starlite(
    route_handlers=[get_user],
    on_startup=[on_startup],
    plugins=[sqlalchemy_plugin],
)
