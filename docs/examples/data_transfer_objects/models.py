"""
Shared models used in DTO documentation examples.

This file demonstrates how to create reusable DTOs that can be imported
across multiple modules in your application.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from litestar.dto import DataclassDTO
from litestar.dto.config import DTOConfig


@dataclass
class User:
    """
    User model representing our internal data structure.
    
    This model contains all fields that might be used internally,
    including sensitive information that should not always be exposed.
    """
    name: str
    email: str
    age: int
    id: UUID = field(default_factory=uuid4)


# Simple DTO that can be used for both input and output
UserDTO = DataclassDTO[User]

# More specific DTO for returning user data
# In this simple example, it's identical to UserDTO, but in real applications
# you might want to exclude sensitive fields or add computed fields
UserReturnDTO = DataclassDTO[User]


# Example of a more configured DTO for input validation
class UserCreateDTO(DataclassDTO[User]):
    """DTO for creating users that excludes auto-generated fields."""
    config = DTOConfig(exclude={"id"})


# Example of a DTO for responses that might exclude sensitive data
class UserPublicDTO(DataclassDTO[User]):
    """DTO for public user data that might exclude private fields."""
    # In this simple example we include all fields, but you might exclude
    # things like email or other private information
    config = DTOConfig()
