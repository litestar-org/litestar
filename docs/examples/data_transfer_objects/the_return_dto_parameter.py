from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from litestar import post
from litestar.dto import DataclassDTO
from litestar.dto.config import DTOConfig


@dataclass
class User:
    """User model with all internal fields."""
    name: str
    email: str
    age: int
    internal_notes: str = ""  # Internal field we don't want to expose
    id: UUID = field(default_factory=uuid4)


# DTO for receiving input data - allows all user-providable fields
class UserInputDTO(DataclassDTO[User]):
    """DTO for parsing input data, excluding auto-generated fields."""
    config = DTOConfig(exclude={"id", "internal_notes"})


# DTO for returning data - excludes sensitive internal fields
class UserResponseDTO(DataclassDTO[User]):
    """DTO for response data that excludes internal fields."""
    config = DTOConfig(exclude={"internal_notes"})


@post("/users", dto=UserInputDTO, return_dto=UserResponseDTO, sync_to_thread=False)
def create_user(data: User) -> User:
    """
    Create a new user with different DTOs for input and output.
    
    - UserInputDTO: Handles parsing client data (excludes id, internal_notes)
    - UserResponseDTO: Handles response serialization (excludes internal_notes)
    """
    # Add some internal notes that clients shouldn't see
    data.internal_notes = "Created via API"
    return data

# When you POST with:
# {"name": "Bob", "email": "bob@example.com", "age": 30}
#
# You get back (note: no internal_notes field):
# {"name": "Bob", "email": "bob@example.com", "age": 30, "id": "..."}
#
# But internally, the User object has internal_notes set
