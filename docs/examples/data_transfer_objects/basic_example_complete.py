from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from litestar import Litestar, post
from litestar.dto import DTOConfig, DataclassDTO


@dataclass
class User:
    id: UUID
    name: str
    email: str
    password: str


# Without DTOs, you'd have to manually handle:
# 1. Validation of incoming JSON
# 2. Converting JSON to Python objects
# 3. Filtering sensitive fields in responses
# 4. Converting Python objects back to JSON

# With DTOs, Litestar handles all of this automatically:

# DTO for incoming data - excludes auto-generated ID
class UserCreateDTO(DataclassDTO[User]):
    config = DTOConfig(exclude={"id"})


# DTO for outgoing data - excludes sensitive password
class UserResponseDTO(DataclassDTO[User]):
    config = DTOConfig(exclude={"password"})


@post("/users", dto=UserCreateDTO, return_dto=UserResponseDTO)
def create_user(data: User) -> User:
    """Create a new user.
    
    DTOs automatically:
    - Validate that incoming JSON matches User model (excluding id)
    - Convert JSON to User instance with generated id
    - Serialize response back to JSON (excluding password)
    """
    # Generate an ID for the new user
    data.id = uuid4()
    
    # In a real application, you would:
    # - Hash the password
    # - Save to database
    # - Handle validation errors
    
    return data


app = Litestar(route_handlers=[create_user])

# Example request:
# POST /users
# {
#   "name": "John Doe",
#   "email": "john@example.com", 
#   "password": "secret123"
# }
#
# Example response (password automatically excluded):
# {
#   "id": "123e4567-e89b-12d3-a456-426614174000",
#   "name": "John Doe",
#   "email": "john@example.com"
# }
