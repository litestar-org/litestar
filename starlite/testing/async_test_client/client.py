import warnings
from contextlib import AsyncExitStack, contextmanager
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    Generic,
    Optional,
    TypeVar,
    Union,
)

from anyio.from_thread import BlockingPortal, start_blocking_portal

from starlite import ASGIConnection, HttpMethod, ImproperlyConfiguredException
from starlite.datastructures import MutableScopeHeaders  # noqa: TC001
from starlite.exceptions import MissingDependencyException
from starlite.testing.async_test_client.life_span_handler import LifeSpanHandler
from starlite.testing.async_test_client.transport import AsyncTestClientTransport
from starlite.types import AnyIOBackend, ASGIApp, HTTPResponseStartEvent

try:
    from httpx import USE_CLIENT_DEFAULT, AsyncClient, Response
except ImportError as e:
    raise MissingDependencyException(
        "To use starlite.testing, install starlite with 'testing' extra, e.g. `pip install starlite[testing]`"
    ) from e


if TYPE_CHECKING:
    from httpx._client import UseClientDefault
    from httpx._types import (
        AuthTypes,
        CookieTypes,
        HeaderTypes,
        QueryParamTypes,
        RequestContent,
        RequestData,
        RequestFiles,
        TimeoutTypes,
        URLTypes,
    )

    from starlite.middleware.session.base import BaseBackendConfig, BaseSessionBackend


T = TypeVar("T", bound=ASGIApp)


def fake_http_send_message(headers: MutableScopeHeaders) -> HTTPResponseStartEvent:
    headers.setdefault("content-type", "application/text")
    return HTTPResponseStartEvent(type="http.response.start", status=200, headers=headers.headers)


def fake_asgi_connection(app: ASGIApp, cookies: Dict[str, str]) -> ASGIConnection[Any, Any, Any]:
    scope = {
        "type": "http",
        "path": "/",
        "raw_path": b"/",
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "method": "GET",
        "http_version": "1.1",
        "extensions": {"http.response.template": {}},
        "app": app,
        "state": {},
        "path_params": {},
        "route_handler": None,
        "_cookies": cookies,
    }
    return ASGIConnection[Any, Any, Any](
        scope=scope,  # type: ignore[arg-type]
    )


class AsyncTestClient(AsyncClient, Generic[T]):
    __test__ = False
    lifespan_handler: LifeSpanHandler
    exit_stack: "AsyncExitStack"

    def __init__(
        self,
        app: T,
        base_url: str = "http://testserver.local",
        raise_server_exceptions: bool = True,
        root_path: str = "",
        backend: AnyIOBackend = "asyncio",
        backend_options: Optional[Dict[str, Any]] = None,
        session_config: Optional["BaseBackendConfig"] = None,
        cookies: Optional["CookieTypes"] = None,
    ):
        if "." not in base_url:
            warnings.warn(
                f"The base_url {base_url!r} might cause issues. Try adding a domain name such as .local: "
                f"'{base_url}.local'",
                UserWarning,
            )
        self._session_backend: Optional["BaseSessionBackend"] = None
        if session_config:
            self._session_backend = session_config._backend_class(config=session_config)
        self.app = app
        self.backend = backend
        self.backend_options = backend_options
        super().__init__(
            app=self.app,
            base_url=base_url,
            headers={"user-agent": "testclient"},
            follow_redirects=True,
            cookies=cookies,
            transport=AsyncTestClientTransport(
                client=self,
                raise_server_exceptions=raise_server_exceptions,
                root_path=root_path,
            ),
        )

    @property
    def session_backend(self) -> "BaseSessionBackend":
        if not self._session_backend:
            raise ImproperlyConfiguredException(
                "Session has not been initialized for this TestClient instance. You can"
                "do so by passing a configuration object to TestClient: TestClient(app=app, session_config=...)"
            )
        return self._session_backend

    @contextmanager
    def portal(self) -> Generator["BlockingPortal", None, None]:
        """Get a BlockingPortal.

        Returns:
            A contextmanager for a BlockingPortal.
        """
        if hasattr(self, "blocking_portal"):
            yield self.blocking_portal
        else:
            with start_blocking_portal(backend=self.backend, backend_options=self.backend_options) as portal:
                yield portal

    async def __aenter__(self) -> "AsyncTestClient[T]":
        async with AsyncExitStack() as stack:
            self.lifespan_handler = LifeSpanHandler(client=self)

            @stack.callback
            def reset_portal() -> None:
                delattr(self, "blocking_portal")

            @stack.push_async_callback
            async def wait_shutdown() -> None:
                await self.lifespan_handler.wait_shutdown()

            self.exit_stack = stack.pop_all()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.exit_stack.aclose()

    async def request(
        self,
        method: str,
        url: "URLTypes",
        *,
        content: Optional["RequestContent"] = None,
        data: Optional["RequestData"] = None,
        files: Optional["RequestFiles"] = None,
        json: Optional[Any] = None,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Optional[Union["AuthTypes", "UseClientDefault"]] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Sends a request.

        Args:
            method: An HTTP method.
            url: URL or path for the request.
            content: Request content.
            data: Form encoded data.
            files: Multipart files to send.
            json: JSON data to send.
            params: Query parameters.
            headers: Request headers.
            cookies: Request cookies.
            auth: Auth headers.
            follow_redirects: Whether to follow redirects.
            timeout: Request timeout.
            extensions: Dictionary of ASGI extensions.

        Returns:
            An HTTPX Response.
        """
        return await super().request(
            url=self.base_url.join(url),
            method=method.value if isinstance(method, HttpMethod) else method,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )
