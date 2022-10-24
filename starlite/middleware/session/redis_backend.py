from typing import ClassVar, Type, Union

from redis.asyncio import Redis  # pylint: disable=import-error

from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig


class RedisBackend(ServerSideBackend["RedisBackendConfig"]):
    def __init__(self, config: "RedisBackendConfig") -> None:
        """Session backend storing data in redis."""
        super().__init__(config=config)
        self.redis = config.redis

    def _id_to_storage_key(self, session_id: str) -> str:
        return f"{self.config.key_prefix}:{session_id}"

    async def get(self, session_id: str) -> Union[bytes, str, None]:
        """Retrieve and deserialise data associated with `session_id` from
        redis.

        If no data exists under the key for the given `session_id`,
        return an empty dictionary
        """
        return await self.redis.get(self._id_to_storage_key(session_id))

    async def set(self, session_id: str, data: bytes) -> None:
        """Serialise data and store it in redis under the key associated with
        `session_id`"""
        await self.redis.set(self._id_to_storage_key(session_id), data, ex=self.config.max_age)

    async def delete(self, session_id: str) -> None:
        """Delete session data under the key associated with `session_id`"""
        await self.redis.delete(self._id_to_storage_key(session_id))

    async def delete_all(self) -> None:
        """Delete all data stored under the `key_prefix`"""
        pattern = f"{self.config.key_prefix}:*"
        cursor: int | None = None
        while (cursor is None) or cursor > 0:
            cursor, keys = await self.redis.scan(cursor=cursor or 0, match=pattern, count=3000)
            if keys:
                await self.redis.delete(*keys)


class RedisBackendConfig(ServerSideSessionConfig):
    _backend_class: ClassVar[Type[RedisBackend]] = RedisBackend
    redis: Redis
    key_prefix: str = "STARLITE_SESSION"
