from sqlalchemy import Column
from sqlalchemy.orm import as_declarative, declared_attr


@as_declarative()
class SQLAlchemyBase:
    id: Column

    # Generate the table name from the class name
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()
