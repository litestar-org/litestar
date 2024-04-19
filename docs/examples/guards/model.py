from pydantic import BaseModel, UUID4
from enum import Enum


class UserRole(str, Enum):
    CONSUMER = "consumer"
    ADMIN = "admin"


class User(BaseModel):
    id: UUID4
    role: UserRole

    @property
    def is_admin(self) -> bool:
        """Determines whether the user is an admin user"""
        return self.role == UserRole.ADMIN