from __future__ import annotations

import abc
import secrets
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Generic, TypedDict, TypeVar, cast

import anyio
import orjson
from starlette.datastructures import MutableHeaders

from starlite import ASGIConnection, Cookie
from starlite.middleware.session.base import SessionBackend
from starlite.middleware.session.config import CookieConfig

if TYPE_CHECKING:
    from aiomcache import Client as MemcacheClient
    from redis.asyncio import Redis

    from starlite.types import Message


class ServerSideSessionConfig(CookieConfig):
    session_id_bytes: int = 32
    identity_mode: Literal["cookie", "header"] = "cookie"


C = TypeVar("C", bound=ServerSideSessionConfig)


class ServerSideBackend(Generic[C], SessionBackend[C]):
    def __init__(self, config: ServerSideSessionConfig) -> None:
        """Starlite session middleware for storing session data server-side."""

        super().__init__(config=config)

    @abc.abstractmethod
    async def get(self, session_id: str) -> bytes | str | None | dict[str, Any]:
        """Retrieve data associate with `session_id`.

        If no data for the given `session_id` exists, return an empty
        dict
        """

    @abc.abstractmethod
    async def set(self, session_id: str, data: bytes) -> None:
        """Store `data` under the `session_id` for later retrieval.

        If there is already data associated with `session_id`, replace
        it with `data` and reset its expiry time
        """

    @abc.abstractmethod
    async def delete(self, session_id: str) -> None:
        """Delete the data associated with `session_id`"""

    @abc.abstractmethod
    async def delete_all(self) -> None:
        """Delete all data stored within this backend."""

    def generate_session_id(self) -> str:
        """Generate a new session-id, with
        n=[session_id_bytes][ServerSideSessionMiddleware.session_id_bytes]
        random bytes."""
        return secrets.token_hex(self.config.session_id_bytes)

    async def store_session(self, message: "Message", connection: ASGIConnection) -> None:
        scope = connection.scope
        headers = MutableHeaders(scope=message)
        scope_session = scope.get("session")

        session_id_source = connection.cookies if self.config.identity_mode == "cookie" else connection.headers
        session_id = session_id_source.get(self.config.key, self.generate_session_id())

        if scope_session:
            serialised_data = self.serialise_data(scope_session, scope)
            await self.set(session_id=session_id, data=serialised_data)
            cookie_params = self.config.dict(exclude_none=True, exclude={"secret", "key"})
            headers["Set-Cookie"] = Cookie(value=session_id, key=self.config.key, **cookie_params).to_header(header="")

    async def load_session(self, connection: ASGIConnection) -> dict[str, Any]:
        session_id = connection.cookies.get(self.config.key)
        if session_id:
            data = await self.get(session_id)
            if isinstance(data, dict):
                return data
            return self.deserialise_data(data)
        return {}


class RedisBackend(ServerSideBackend["RedisBackendConfig"]):
    def __init__(self, config: RedisBackendConfig) -> None:
        """Session backend storing data in redis."""
        super().__init__(config=config)
        self.redis = config.redis

    def _id_to_storage_key(self, session_id: str) -> str:
        return f"{self.config.key_prefix}:{session_id}"

    async def get(self, session_id: str) -> bytes | str | None:
        """Retrieve and deserialise data associated with `session_id` from
        redis.

        If no data exists under the key for the given `session_id`,
        return an empty dictionary
        """
        return await self.redis.get(self._id_to_storage_key(session_id))

    async def set(self, session_id: str, data: bytes) -> None:
        """Serialise data and store it in redis under the key associated with
        `session_id`"""
        await self.redis.set(self._id_to_storage_key(session_id), orjson.dumps(data), ex=self.config.expires)

    async def delete(self, session_id: str) -> None:
        """Delete session data under the key associated with `session_id`"""
        await self.redis.delete(self._id_to_storage_key(session_id))

    async def delete_all(self) -> None:
        """Delete all data stored under the `key_prefix`"""
        pattern = f"{self.config.key_prefix}:*"
        cursor = None
        while cursor is None or cursor > 0:
            cursor, keys = await self.redis.scan(cursor=cursor or 0, match=pattern, count=3000)
            if keys:
                await self.redis.delete(*keys)


class MemcacheBackend(ServerSideBackend["MemcachedBackendConfig"]):
    def __init__(
        self,
        config: MemcachedBackendConfig,
    ) -> None:
        super().__init__(config=config)
        self.memcached = config.memcached

    def _id_to_storage_key(self, session_id: str) -> bytes:
        return f"{self.config.key_prefix}:{session_id}".encode()

    async def get(self, session_id: str) -> bytes | str | None:
        return await self.memcached.get(key=self._id_to_storage_key(session_id))

    async def set(self, session_id: str, data: dict[str, Any]) -> None:
        await self.memcached.set(
            key=self._id_to_storage_key(session_id), value=orjson.dumps(data), exptime=self.config.expires
        )

    async def delete(self, session_id: str) -> None:
        await self.memcached.delete(self._id_to_storage_key(session_id))

    async def delete_all(self) -> None:
        stats = await self.memcached.stats("items")
        for key, val in stats.items():
            _, slab, field = key.split(":")
            if field != "number" or val == 0:
                continue
            item_request = await self.memcached.stats("cachedump", slab, str(val + 10))
            for keys in item_request:
                await self.memcached.delete(keys)


class _MemoryMetaDict(TypedDict):
    expires: datetime
    data: dict[str, Any]


class MemoryBackend(ServerSideBackend["MemoryBackendConfig"]):
    def __init__(self, config: MemcachedBackendConfig) -> None:
        super().__init__(config=config)
        self._store: dict[str, _MemoryMetaDict] = {}

    async def get(self, session_id: str) -> dict[str, Any] | None:
        wrapped_data = self._store.get(session_id)
        if wrapped_data:
            if wrapped_data["expires"] > datetime.utcnow().replace(tzinfo=None):
                return wrapped_data["data"]
            del self._store[session_id]
        return None

    async def set(self, session_id: str, data: dict[str, Any]) -> None:
        self._store[session_id] = {
            "expires": datetime.utcnow().replace(tzinfo=None) + self.config.expires,
            "data": data,
        }

    async def delete(self, session_id: str) -> None:
        if session_id in self._store:
            del self._store[session_id]

    async def delete_all(self) -> None:
        self._store = {}


class FileBackend(ServerSideBackend["FileBackendConfig"]):
    def __init__(self, config: FileBackendConfig) -> None:
        super().__init__(config=config)
        self.path = config.path

    def _id_to_storage_path(self, session_id: str) -> Path:
        return (self.path / session_id).with_suffix(".json")

    def _load(self, session_id: str) -> dict[str, Any]:
        path = self._id_to_storage_path(session_id)
        if path.exists():
            wrapped_data = orjson.loads(path.read_text())
            expires = datetime.fromisoformat(wrapped_data["expires"])
            if expires < datetime.utcnow().replace(tzinfo=None):
                return cast("Dict[str, Any]", wrapped_data["data"])
            path.unlink()
        return {}

    def _store(self, session_id: str, data: dict[str, Any]) -> None:
        path = self._id_to_storage_path(session_id)
        wrapped_data = {
            "expires": (datetime.utcnow().replace(tzinfo=None) + self.config.expires).isoformat(),
            "data": data,
        }
        path.write_text(orjson.dumps(wrapped_data).decode("utf-8"))

    def _delete_all(self) -> None:
        shutil.rmtree(self.path, ignore_errors=True)
        self.path.mkdir()

    async def get(self, session_id: str) -> dict[str, Any]:
        data = await anyio.to_thread.run_sync(self._load, session_id)
        return data or {}

    async def set(self, session_id: str, data: dict[str, Any]) -> None:
        await anyio.to_thread.run_sync(self._store, session_id, data)

    async def delete(self, session_id: str) -> None:
        path = self._id_to_storage_path(session_id)
        await anyio.to_thread.run_sync(path.unlink, True)

    async def delete_all(self) -> None:
        await anyio.to_thread.run_sync(self._delete_all)


class RedisBackendConfig(ServerSideSessionConfig):
    _backend_class = RedisBackend
    redis: Redis
    expires: timedelta
    key_prefix: str = "STARLITE_SESSION"


class MemcachedBackendConfig(ServerSideSessionConfig):
    _backend_class = MemcacheBackend
    memcached: MemcacheClient
    expires: int
    key_prefix: str = "STARLITE_SESSION"


class MemoryBackendConfig(ServerSideSessionConfig):
    _backend_class = MemcacheBackend
    expires: timedelta


class FileBackendConfig(ServerSideSessionConfig):
    _backend_class = FileBackend
    path: Path
    expires: timedelta
