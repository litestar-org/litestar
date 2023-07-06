from typing import Any, MutableMapping, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection

__all__ = ("Document", "AsyncMotorCollection")


Document = TypeVar("Document", bound=MutableMapping[str, Any])
AsyncMotorCollection = AsyncIOMotorCollection
