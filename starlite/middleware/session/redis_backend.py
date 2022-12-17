from typing import Optional, Type, Union

from redis.asyncio import Redis

from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig


class RedisBackend(ServerSideBackend["RedisBackendConfig"]):
    """Session backend to store data in redis."""

    __slots__ = ("redis",)

    def __init__(self, config: "RedisBackendConfig") -> None:
        """Initialize `RedisBackend`.

        Notes:
            - Requires `redis`. Install with `pip install starlite[redis]`
        """
        super().__init__(config=config)
        self.redis = config.redis

    def _id_to_storage_key(self, session_id: str) -> str:
        return f"{self.config.key_prefix}:{session_id}"

    async def get(self, session_id: str) -> Union[bytes, str, None]:
        """Load data associated with `session_id` from redis.

        Args:
            session_id: The session-ID

        Returns:
            The session data, if existing, otherwise `None`.
        """

        return await self.redis.get(self._id_to_storage_key(session_id))

    async def set(self, session_id: str, data: bytes) -> None:
        """Store `data` in redis under `<prefix>:<session_id>`

        If there is already data associated with `session_id`, replace
        it with `data` and reset its expiry time

        Args:
            session_id: The session-ID
            data: Serialized session data

        Returns:
            None
        """
        await self.redis.set(self._id_to_storage_key(session_id), data, ex=self.config.max_age)

    async def delete(self, session_id: str) -> None:
        """Delete the data associated with `session_id` from redis. Fail silently if no such session-ID exists.

        Args:
            session_id: The session-ID

        Returns:
            None
        """
        await self.redis.delete(self._id_to_storage_key(session_id))

    async def delete_all(self) -> None:
        """Delete all session data stored in redis.

        Returns:
            None
        """
        pattern = f"{self.config.key_prefix}:*"
        cursor: Optional[int] = None
        while (cursor is None) or cursor > 0:
            cursor, keys = await self.redis.scan(cursor=cursor or 0, match=pattern, count=3000)
            if keys:
                await self.redis.delete(*keys)


class RedisBackendConfig(ServerSideSessionConfig):
    """Configuration for `RedisBackend`"""

    _backend_class: Type[RedisBackend] = RedisBackend

    redis: Redis
    """`redis.asyncio.Redis` instance."""
    key_prefix: str = "STARLITE_SESSION"
    """Prefix to store data under after the schema of `<prefix>:<session-ID>`"""
