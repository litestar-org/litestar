from typing import Type, Union

from redis.asyncio import Redis  # pylint: disable=import-error

from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig


class RedisBackend(ServerSideBackend["RedisBackendConfig"]):
    def __init__(self, config: "RedisBackendConfig") -> None:
        """Session backend to store data in redis.

        Notes:
            - Requires `redis`. Install with `pip install starlite[redis]`
        """
        super().__init__(config=config)
        self.redis = config.redis

    def _id_to_storage_key(self, session_id: str) -> str:
        return f"{self.config.key_prefix}:{session_id}"

    async def get(self, session_id: str) -> Union[bytes, str, None]:
        """Load data associate with `session_id` from redis."""
        return await self.redis.get(self._id_to_storage_key(session_id))

    async def set(self, session_id: str, data: bytes) -> None:
        """Store `data` in redis under `<prefix>:<session_id>`.

        Previously existing data will be overwritten and expiry times
        will be updated
        """
        await self.redis.set(self._id_to_storage_key(session_id), data, ex=self.config.max_age)

    async def delete(self, session_id: str) -> None:
        """Delete data associated with `session_id` from redis.

        Fails silently if no such key exists
        """
        await self.redis.delete(self._id_to_storage_key(session_id))

    async def delete_all(self) -> None:
        """Delete all session data stored in redis."""
        pattern = f"{self.config.key_prefix}:*"
        cursor: int | None = None
        while (cursor is None) or cursor > 0:
            cursor, keys = await self.redis.scan(cursor=cursor or 0, match=pattern, count=3000)
            if keys:
                await self.redis.delete(*keys)


class RedisBackendConfig(ServerSideSessionConfig):
    _backend_class: Type[RedisBackend] = RedisBackend
    redis: Redis
    """`redis.asyncio.Redis` instance"""
    key_prefix: str = "STARLITE_SESSION"
    """Prefix to store data under after the schema of `<prefix>:<session-ID>`"""
