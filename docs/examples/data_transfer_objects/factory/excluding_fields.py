"""
Example demonstrating field exclusion in DTOs, particularly with nested objects and collections.

This example shows how to use DTOConfig to exclude specific fields from serialization,
including fields within nested objects and collections.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from litestar import Litestar, post
from litestar.dto import DTOConfig, dto_field
from litestar.plugins.sqlalchemy import SQLAlchemyDTO


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class Address(Base):
    """Address model with street information."""
    __tablename__ = "address"
    
    street: Mapped[str]
    city: Mapped[str]
    state: Mapped[str]
    zip: Mapped[str]


class Pet(Base):
    """Pet model belonging to a user."""
    __tablename__ = "pet"
    
    name: Mapped[str]
    species: Mapped[str]
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"))


class User(Base):
    """User model with address and pets relationships."""
    __tablename__ = "user"
    
    name: Mapped[str]
    email: Mapped[str]
    password: Mapped[str] = mapped_column(info=dto_field("private"))
    created_at: Mapped[datetime] = mapped_column(info=dto_field("read-only"))
    address_id: Mapped[UUID] = mapped_column(ForeignKey("address.id"), info=dto_field("private"))
    address: Mapped[Address] = relationship(info=dto_field("read-only"))
    pets: Mapped[list[Pet]] = relationship(info=dto_field("read-only"))


# Basic DTO for input (respects dto_field markers)
UserDTO = SQLAlchemyDTO[User]

# Configuration that excludes specific fields from output
config = DTOConfig(
    exclude={
        "id",             # Exclude user's id from response
        "address.id",     # Exclude address id from nested address object
        "address.street", # Exclude street from nested address object  
        "pets.0.id",      # Exclude id from ALL pets in the pets list
        "pets.0.user_id", # Exclude user_id from ALL pets in the pets list
    }
)

# DTO for output that applies the exclusion config
ReadUserDTO = SQLAlchemyDTO[Annotated[User, config]]


@post("/users", dto=UserDTO, return_dto=ReadUserDTO, sync_to_thread=False)
def create_user(data: User) -> User:
    """
    Create a new user with address and pets.
    
    Input example:
    {
        "name": "John Doe",
        "email": "john@example.com"
    }
    
    Output will exclude the fields specified in the config:
    {
        "name": "John Doe", 
        "email": "john@example.com",
        "created_at": "2024-01-01T00:00:00",
        "address": {
            // "id" excluded
            // "street" excluded  
            "city": "Anytown",
            "state": "NY",
            "zip": "12345"
        },
        "pets": [
            {
                // "id" excluded from ALL pets
                // "user_id" excluded from ALL pets  
                "name": "Fluffy",
                "species": "cat"
            },
            {
                // "id" excluded from ALL pets
                // "user_id" excluded from ALL pets
                "name": "Rex", 
                "species": "dog"
            }
        ]
    }
    """
    # Set read-only fields
    data.created_at = datetime.now()
    
    # Create related objects
    data.address = Address(
        street="123 Main St", 
        city="Anytown", 
        state="NY", 
        zip="12345"
    )
    
    data.pets = [
        Pet(name="Fluffy", species="cat"),
        Pet(name="Rex", species="dog")
    ]
    
    return data


app = Litestar(route_handlers=[create_user])

# Test with:
# curl -X POST http://localhost:8000/users \
#   -H "Content-Type: application/json" \
#   -d '{"name":"John Doe","email":"john@example.com"}'
