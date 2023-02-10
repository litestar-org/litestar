import secrets
from typing import Any, Dict, Type

from starlite import ASGIConnection, Cookie
from starlite.datastructures import MutableScopeHeaders
from starlite.middleware.session.base import BaseBackendConfig, BaseSessionBackend
from starlite.storage.base import StorageBackend
from starlite.types import Empty, Message, ScopeSession


class ServerSideBackend(BaseSessionBackend["ServerSideSessionConfig"]):
    """Base class for server-side backends.

    Implements :class:`BaseSessionBackend` and defines and interface which subclasses can
    implement to facilitate the storage of session data.
    """

    __slots__ = ("storage",)

    def __init__(self, config: "ServerSideSessionConfig") -> None:
        """Initialize ``ServerSideBackend``

        Args:
            config: A subclass of ``ServerSideSessionConfig``
        """
        super().__init__(config=config)
        self.storage = config.storage

    async def get(self, session_id: str) -> bytes | None:
        """Retrieve data associated with ``session_id``.

        Args:
            session_id: The session-ID

        Returns:
            The session data, if existing, otherwise ``None``.
        """
        return await self.storage.get(session_id)

    async def set(self, session_id: str, data: bytes) -> None:
        """Store ``data`` under the ``session_id`` for later retrieval.

        If there is already data associated with ``session_id``, replace
        it with ``data`` and reset its expiry time

        Args:
            session_id: The session-ID
            data: Serialized session data

        Returns:
            None
        """
        await self.storage.set(session_id, data, expires=self.config.max_age)

    async def delete(self, session_id: str) -> None:
        """Delete the data associated with ``session_id``. Fails silently if no such session-ID exists.

        Args:
            session_id: The session-ID

        Returns:
            None
        """
        await self.storage.delete(session_id)

    def generate_session_id(self) -> str:
        """Generate a new session-ID, with
        n=:attr:`session_id_bytes <ServerSideSessionConfig.session_id_bytes>` random bytes.

        Returns:
            A session-ID
        """
        return secrets.token_hex(self.config.session_id_bytes)

    async def store_in_message(
        self, scope_session: "ScopeSession", message: "Message", connection: ASGIConnection
    ) -> None:
        """Store the necessary information in the outgoing ``Message`` by setting a cookie containing the session-ID.

        If the session is empty, a null-cookie will be set. Otherwise, the serialised
        data will be stored using :meth:`set <ServerSideBackend.set>`, under the current session-id. If no session-ID
        exists, a new ID will be generated using :meth:`generate_session_id <ServerSideBackend.generate_session_id>`.

        Args:
            scope_session: Current session to store
            message: Outgoing send-message
            connection: Originating ASGIConnection containing the scope

        Returns:
            None
        """
        scope = connection.scope
        headers = MutableScopeHeaders.from_message(message)
        session_id = connection.cookies.get(self.config.key)
        if session_id == "null":
            session_id = None
        if not session_id:
            session_id = self.generate_session_id()

        cookie_params = self.config.dict(
            exclude_none=True,
            exclude={"secret", "key"} | set(self.config.__fields__) - set(BaseBackendConfig.__fields__),
        )

        if scope_session is Empty:
            await self.delete(session_id)
            headers.add(
                "Set-Cookie",
                Cookie(value="null", key=self.config.key, expires=0, **cookie_params).to_header(header=""),
            )
        else:
            serialised_data = self.serialize_data(scope_session, scope)
            await self.set(session_id=session_id, data=serialised_data)

            headers["Set-Cookie"] = Cookie(value=session_id, key=self.config.key, **cookie_params).to_header(header="")

    async def load_from_connection(self, connection: ASGIConnection) -> Dict[str, Any]:
        """Load session data from a connection and return it as a dictionary to be used in the current application
        scope.

        The session-ID will be gathered from a cookie with the key set in
        :attr:`BaseBackendConfig.key`. If a cookie is found, its value will be used as the session-ID and data associated
        with this ID will be loaded using :meth:`get <ServerSideBackend.get>`.
        If no cookie was found or no data was loaded from the store, this will return an
        empty dictionary.

        Args:
            connection: An ASGIConnection instance

        Returns:
            The current session data
        """
        session_id = connection.cookies.get(self.config.key)
        if session_id:
            data = await self.get(session_id)
            if data is not None:
                return self.deserialize_data(data)
        return {}


class ServerSideSessionConfig(BaseBackendConfig):
    """Base configuration for server side backends."""

    session_id_bytes: int = 32
    """Number of bytes used to generate a random session-ID."""
    storage: StorageBackend
    _backend_class: Type[ServerSideBackend] = ServerSideBackend
