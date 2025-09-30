"""
Data models for DTO examples.

This file demonstrates basic DTO creation patterns.
For complete, runnable examples, see the individual example files
in this directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from litestar.dto import DataclassDTO


@dataclass
class User:
    """Basic user model for demonstration purposes."""
    id: UUID
    name: str
    email: str


# Basic DTO that handles all fields
UserDTO = DataclassDTO[User]

# Alternative: explicitly defined DTO class
class UserReturnDTO(DataclassDTO[User]):
    """DTO for user responses."""
    pass
