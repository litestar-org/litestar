# pyright: reportInvalidTypeForm=false
from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Generic

import anyio
from httpx import AsyncClient

from litestar.testing.life_span_handler import LifeSpanHandler
from litestar.testing.transport import ConnectionUpgradeExceptionError, TestClientTransport
from litestar.testing.websocket_test_session import AsyncWebSocketTestSession
from litestar.utils._exceptions import _collapse_exception_group

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from types import TracebackType

    from httpx._client import UseClientDefault
    from httpx._types import (
        AuthTypes,
        CookieTypes,
        HeaderTypes,
        QueryParamTypes,
    )
    from typing_extensions import Self

    from litestar.middleware.session.base import BaseBackendConfig, BaseSessionBackend

from typing import TYPE_CHECKING, Any, TypeVar
from warnings import warn

from httpx._client import USE_CLIENT_DEFAULT, UseClientDefault

from litestar.testing.client._base import _get_session_data, _prepare_ws_connect_request, _set_session_data
from litestar.types import ASGIApp

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from httpx._types import (
        CookieTypes,
        HeaderTypes,
        QueryParamTypes,
    )

T = TypeVar("T", bound=ASGIApp)


class AsyncTestClient(AsyncClient, Generic[T]):
    def __init__(
        self,
        app: T,
        base_url: str = "http://testserver.local",
        raise_server_exceptions: bool = False,
        root_path: str = "",
        timeout: float | None = None,
        cookies: CookieTypes | None = None,
        session_config: BaseBackendConfig | None = None,
    ) -> None:
        """An Async client implementation providing a context manager for testing applications asynchronously.

        Args:
            app: The instance of :class:`Litestar <litestar.app.Litestar>` under test.
            base_url: URL scheme and domain for test request paths, e.g. ``http://testserver``.
            raise_server_exceptions: Flag for the underlying test client to raise server exceptions instead of
                wrapping them in an HTTP response.
            root_path: Path prefix for requests.
            timeout: Request timeout
            cookies: Cookies to set on the client.
            session_config: Session backend configuration
        """
        if "." not in base_url:
            warn(
                f"The base_url {base_url!r} might cause issues. Try adding a domain name such as .local: "
                f"'{base_url}.local'",
                UserWarning,
                stacklevel=1,
            )

        self.app = app

        self._session_backend: BaseSessionBackend | None = None
        if session_config:
            self._session_backend = session_config._backend_class(config=session_config)

        self.exit_stack = contextlib.AsyncExitStack()

        super().__init__(
            base_url=base_url,
            headers={"user-agent": "testclient"},
            follow_redirects=True,
            cookies=cookies,
            transport=TestClientTransport(
                client=self,
                raise_server_exceptions=raise_server_exceptions,
                root_path=root_path,
            ),
            timeout=timeout,
        )
        # warn on usafe if client not initialized

    async def __aenter__(self) -> Self:
        self._tg = await self.exit_stack.enter_async_context(anyio.create_task_group())
        lifespan_handler = LifeSpanHandler(app=self.app)
        await self.exit_stack.enter_async_context(lifespan_handler)
        await super().__aenter__()
        self.exit_stack.push_async_exit(super().__aexit__)

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        try:
            await self.exit_stack.__aexit__(exc_type, exc_value, traceback)
        except Exception as exc:
            exc = _collapse_exception_group(exc)
            raise exc

    async def websocket_connect(
        self,
        url: str,
        subprotocols: Sequence[str] | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: float | None = None,
        extensions: Mapping[str, Any] | None = None,
    ) -> AsyncWebSocketTestSession:
        """Sends a GET request to establish a websocket connection.

        Args:
            url: Request URL.
            subprotocols: Websocket subprotocols.
            params: Query parameters.
            headers: Request headers.
            cookies: Request cookies.
            auth: Auth headers.
            follow_redirects: Whether to follow redirects.
            timeout: Request timeout.
            extensions: Dictionary of ASGI extensions.

        Returns:
            A `WebSocketTestSession <litestar.testing.WebSocketTestSession>` instance.
        """
        try:
            await self.send(
                _prepare_ws_connect_request(
                    client=self,
                    url=url,
                    subprotocols=subprotocols,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    extensions=extensions,
                    timeout=timeout,
                ),
                auth=auth,
                follow_redirects=follow_redirects,
            )
        except ConnectionUpgradeExceptionError as exc:
            return AsyncWebSocketTestSession(
                app=self.app,
                scope=exc.scope,
                connect_timeout=timeout,
                tg=self._tg,
            )

        raise RuntimeError("Expected WebSocket upgrade")  # pragma: no cover

    async def get_session_data(self) -> dict[str, Any]:
        """Get session data.

        Returns:
            A dictionary containing session data.

        Examples:
            .. code-block:: python

                from litestar import Litestar, post
                from litestar.middleware.session.memory_backend import MemoryBackendConfig

                session_config = MemoryBackendConfig()


                @post(path="/test")
                def set_session_data(request: Request) -> None:
                    request.session["foo"] == "bar"


                app = Litestar(
                    route_handlers=[set_session_data], middleware=[session_config.middleware]
                )

                async with AsyncTestClient(app=app, session_config=session_config) as client:
                    await client.post("/test")
                    assert await client.get_session_data() == {"foo": "bar"}

        """
        return await _get_session_data(self)

    async def set_session_data(self, data: dict[str, Any]) -> None:
        """Set session data.

        Args:
            data: Session data

        Returns:
            None

        Examples:
            .. code-block:: python

                from litestar import Litestar, get
                from litestar.middleware.session.memory_backend import MemoryBackendConfig

                session_config = MemoryBackendConfig()


                @get(path="/test")
                def get_session_data(request: Request) -> Dict[str, Any]:
                    return request.session


                app = Litestar(
                    route_handlers=[get_session_data], middleware=[session_config.middleware]
                )

                async with AsyncTestClient(app=app, session_config=session_config) as client:
                    await client.set_session_data({"foo": "bar"})
                    assert await client.get("/test").json() == {"foo": "bar"}

        """
        return await _set_session_data(self, data)
