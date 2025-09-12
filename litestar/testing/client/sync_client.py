from __future__ import annotations

import contextlib
from contextlib import ExitStack
from typing import TYPE_CHECKING, Any, Generic, TypeVar
from warnings import warn

import anyio.from_thread
import httpx
from httpx import USE_CLIENT_DEFAULT, Client

from litestar import Litestar
from litestar.testing.client._base import (
    _prepare_ws_connect_request,
    _wrap_app_to_add_state,
    _get_session_data,
    _set_session_data,
)
from litestar.testing.life_span_handler import LifeSpanHandler
from litestar.testing.transport import ConnectionUpgradeExceptionError, SyncTestClientTransport
from litestar.testing.websocket_test_session import WebSocketTestSession

from litestar.types import AnyIOBackend, ASGIApp

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from httpx._client import UseClientDefault
    from httpx._types import (
        AuthTypes,
        CookieTypes,
        HeaderTypes,
        QueryParamTypes,
        TimeoutTypes,
    )
    from typing_extensions import Self

    from litestar.middleware.session.base import BaseBackendConfig, BaseSessionBackend


T = TypeVar("T", bound=ASGIApp)


class TestClient(Client, Generic[T]):
    __test__ = False

    def __init__(
        self,
        app: T,
        base_url: str = "http://testserver.local",
        raise_server_exceptions: bool = True,
        root_path: str = "",
        timeout: float | None = None,
        cookies: CookieTypes | None = None,
        backend: AnyIOBackend = "asyncio",
        backend_options: dict[str, Any] | None = None,
        session_config: BaseBackendConfig | None = None,
        disable_lifespan: bool = False,
    ) -> None:
        """A client implementation providing a context manager for testing applications.

        Args:
            app: The instance of :class:`Litestar <litestar.app.Litestar>` under test.
            base_url: URL scheme and domain for test request paths, e.g. ``http://testserver``.
            raise_server_exceptions: Flag for the underlying test client to raise server exceptions instead of
                wrapping them in an HTTP response.
            root_path: Path prefix for requests.
            timeout: Request timeout
            cookies: Cookies to set on the client.
            backend: The async backend to use, options are "asyncio" or "trio".
            backend_options: ``anyio`` options.
        """
        if "." not in base_url:
            warn(
                f"The base_url {base_url!r} might cause issues. Try adding a domain name such as .local: "
                f"'{base_url}.local'",
                UserWarning,
                stacklevel=1,
            )

        # if not isinstance(app, Litestar):
        #     app = _wrap_app_to_add_state(app)

        self._startup_done = False
        self._session_backend: BaseSessionBackend | None = None
        if session_config:
            self._session_backend = session_config._backend_class(config=session_config)

        self.app = app
        self.exit_stack = contextlib.ExitStack()
        self.blocking_portal = self.exit_stack.enter_context(
            anyio.from_thread.start_blocking_portal(
                backend=backend,
                backend_options=backend_options,
                name="test_client",
            )
        )
        self._disable_lifespan = disable_lifespan

        super().__init__(
            base_url=base_url,
            headers={"user-agent": "testclient"},
            follow_redirects=True,
            cookies=cookies,
            transport=SyncTestClientTransport(
                client=self,
                raise_server_exceptions=raise_server_exceptions,
                root_path=root_path,
            ),
            timeout=timeout,
        )
        # warn on usafe if client not initialized

    def __enter__(self) -> Self:
        if not self._disable_lifespan:
            lifespan = self.exit_stack.enter_context(
                self.blocking_portal.wrap_async_context_manager(LifeSpanHandler(self.app))
            )

            def wait_shutdown() -> None:
                self.blocking_portal.call(lifespan.wait_shutdown)

            self.exit_stack.callback(wait_shutdown)

        self._startup_done = True
        return self

    def __exit__(self, *args: Any) -> None:
        self.exit_stack.close()
        super().__exit__(*args)

    def websocket_connect(
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
    ) -> WebSocketTestSession:
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
            self.send(
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
            return WebSocketTestSession(
                client=self,
                scope=exc.scope,
                portal=self.blocking_portal,
                connect_timeout=timeout,
            )

        raise RuntimeError("Expected WebSocket upgrade")  # pragma: no cover

    def get_session_data(self) -> dict[str, Any]:
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
        return self.blocking_portal.call(_get_session_data, self)

    def set_session_data(self, data: dict[str, Any]) -> None:
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
        return self.blocking_portal.call(_set_session_data, self, data)
