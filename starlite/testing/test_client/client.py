import warnings
from contextlib import ExitStack, contextmanager
from http.cookiejar import CookieJar
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    Generic,
    Optional,
    Sequence,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import urljoin

from anyio.from_thread import BlockingPortal, start_blocking_portal
from httpx import USE_CLIENT_DEFAULT, Client, Cookies, Request, Response

from starlite import ASGIConnection, HttpMethod, ImproperlyConfiguredException
from starlite.datastructures import MutableScopeHeaders
from starlite.testing.test_client.life_span_handler import LifeSpanHandler
from starlite.testing.test_client.transport import (
    ConnectionUpgradeException,
    TestClientTransport,
)
from starlite.types import AnyIOBackend, ASGIApp, HTTPResponseStartEvent
from starlite.utils import deprecated

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
    from starlite.middleware.session.cookie_backend import CookieBackend
    from starlite.testing.test_client.websocket_test_session import WebSocketTestSession


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


class TestClient(Client, Generic[T]):
    __test__ = False
    blocking_portal: "BlockingPortal"
    lifespan_handler: LifeSpanHandler
    exit_stack: "ExitStack"

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
    ) -> None:
        """A client implementation providing a context manager for testing applications.

        Args:
            app: The instance of [Starlite][starlite.app.Starlite] under test.
            base_url: URL scheme and domain for test request paths, e.g. 'http://testserver'.
            raise_server_exceptions: Flag for the underlying test client to raise server exceptions instead of
                wrapping them in an HTTP response.
            root_path: Path prefix for requests.
            backend: The async backend to use, options are "asyncio" or "trio".
            backend_options: 'anyio' options.
            session_config: Configuration for Session Middleware class to create raw session cookies for request to the
                route handlers.
            cookies: Cookies to set on the client.
        """
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
            transport=TestClientTransport(
                client=self,
                raise_server_exceptions=raise_server_exceptions,
                root_path=root_path,
            ),
        )

    @property
    @deprecated("1.34.0", alternative="session_backend", pending=True, kind="property")
    def session(self) -> "CookieBackend":
        from starlite.middleware.session.cookie_backend import CookieBackend

        if not isinstance(self.session_backend, CookieBackend):
            raise ImproperlyConfiguredException(
                f"Invalid session backend: {type(self._session_backend)!r}. Expected 'CookieBackend'"
            )
        return self.session_backend

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

    def __enter__(self) -> "TestClient[T]":
        with ExitStack() as stack:
            self.blocking_portal = portal = stack.enter_context(self.portal())
            self.lifespan_handler = LifeSpanHandler(client=self)

            @stack.callback
            def reset_portal() -> None:
                delattr(self, "blocking_portal")

            @stack.callback
            def wait_shutdown() -> None:
                portal.call(self.lifespan_handler.wait_shutdown)

            self.exit_stack = stack.pop_all()

        return self

    def __exit__(self, *args: Any) -> None:
        self.exit_stack.close()

    def request(
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
        return super().request(
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

    def get(
        self,
        url: "URLTypes",
        *,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Sends a GET request.

        Args:
            url: URL or path for the request.
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
        return super().get(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def options(
        self,
        url: "URLTypes",
        *,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Sends an OPTIONS request.

        Args:
            url: URL or path for the request.
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
        return super().options(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def head(
        self,
        url: "URLTypes",
        *,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Sends a HEAD request.

        Args:
            url: URL or path for the request.
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
        return super().head(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def post(
        self,
        url: "URLTypes",
        *,
        content: Optional["RequestContent"] = None,
        data: Optional["RequestData"] = None,
        files: Optional["RequestFiles"] = None,
        json: Optional[Any] = None,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Sends a POST request.

        Args:
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
        return super().post(
            url,
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

    def put(
        self,
        url: "URLTypes",
        *,
        content: Optional["RequestContent"] = None,
        data: Optional["RequestData"] = None,
        files: Optional["RequestFiles"] = None,
        json: Optional[Any] = None,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Sends a PUT request.

        Args:
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
        return super().put(
            url,
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

    def patch(
        self,
        url: "URLTypes",
        *,
        content: Optional["RequestContent"] = None,
        data: Optional["RequestData"] = None,
        files: Optional["RequestFiles"] = None,
        json: Optional[Any] = None,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Sends a PATCH request.

        Args:
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
        return super().patch(
            url,
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

    def delete(
        self,
        url: "URLTypes",
        *,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Sends a DELETE request.

        Args:
            url: URL or path for the request.
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
        return super().delete(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def websocket_connect(
        self,
        url: str,
        subprotocols: Optional[Sequence[str]] = None,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> "WebSocketTestSession":
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
            An [WebSocketTestSession][starlite.testing.test_client.WebSocketTestSession] instance.
        """
        url = urljoin("ws://testserver", url)
        default_headers: Dict[str, str] = {}
        default_headers.setdefault("connection", "upgrade")
        default_headers.setdefault("sec-websocket-key", "testserver==")
        default_headers.setdefault("sec-websocket-version", "13")
        if subprotocols is not None:
            default_headers.setdefault("sec-websocket-protocol", ", ".join(subprotocols))
        try:
            super().request(
                "GET",
                url,
                headers={**dict(headers or {}), **default_headers},  # type: ignore
                params=params,
                cookies=cookies,
                auth=auth,
                follow_redirects=follow_redirects,
                timeout=timeout,
                extensions=extensions,
            )
        except ConnectionUpgradeException as exc:
            return exc.session
        else:
            raise RuntimeError("Expected WebSocket upgrade")  # pragma: no cover

    @deprecated("1.34.0", alternative="set_session_data", pending=True)
    def create_session_cookies(self, session_data: Dict[str, Any]) -> Dict[str, str]:
        """Creates raw session cookies that are loaded into the session by the Session Middleware. It creates cookies
        the same way as if they are coming from the browser. Your tests must set up session middleware to load raw
        session cookies into the session.

        Args:
            session_data: Dictionary to create raw session cookies from.

        Returns:
            A dictionary with cookie name as key and cookie value as value.

        Notes:
            - Deprecated. Use the explicit `TestClient.set_session_data` method

        Examples:

            ```python
            import pytest
            from starlite.testing import TestClient

            from my_app.main import app, session_cookie_config_instance


            class TestClass:
                @pytest.fixture()
                def test_client(self) -> TestClient:
                    with TestClient(
                        app=app, session_config=session_cookie_config_instance
                    ) as client:
                        yield client

                def test_something(self, test_client: TestClient) -> None:
                    cookies = test_client.create_session_cookies(session_data={"user": "test_user"})
                    # Set raw session cookies to the "cookies" attribute of test_client instance.
                    test_client.cookies = cookies
                    test_client.get(url="/my_route")
            ```
        """
        if self._session_backend is None:
            return {}
        return self._create_session_cookies(self.session, session_data)

    @deprecated("1.34.0", alternative="get_session_data", pending=True)
    def get_session_from_cookies(self) -> Dict[str, Any]:
        """Raw session cookies are a serialized image of session which are created by session middleware and sent with
        the response. To assert data in session, this method deserializes the raw session cookies and creates session
        from them.

        Returns:
            A dictionary containing session data.

        Notes:
            - Deprecated. Use the explicit `TestClient.get_session_data` method

        Examples:

            ```python
            def test_something(self, test_client: TestClient) -> None:
                test_client.get(url="/my_route")
                session = test_client.get_session_from_cookies()
                assert "user" in session
            ```
        """
        if self._session_backend is None:
            return {}
        return self.get_session_data()

    @staticmethod
    def _create_session_cookies(backend: "CookieBackend", data: Dict[str, Any]) -> Dict[str, str]:
        encoded_data = backend.dump_data(data=data)
        return {cookie.key: cast("str", cookie.value) for cookie in backend._create_session_cookies(encoded_data)}

    async def _set_session_data_async(self, data: Dict[str, Any]) -> None:
        # TODO: Expose this in the async client
        mutable_headers = MutableScopeHeaders()
        await self.session_backend.store_in_message(
            scope_session=data,
            message=fake_http_send_message(mutable_headers),
            connection=fake_asgi_connection(
                app=self.app,
                cookies=dict(self.cookies),
            ),
        )
        response = Response(200, request=Request("GET", self.base_url), headers=mutable_headers.headers)

        cookies = Cookies(CookieJar())
        cookies.extract_cookies(response)
        self.cookies.update(cookies)

    async def _get_session_data_async(self) -> Dict[str, Any]:
        # TODO: Expose this in the async client
        return await self.session_backend.load_from_connection(
            connection=fake_asgi_connection(
                app=self.app,
                cookies=dict(self.cookies),
            ),
        )

    def set_session_data(self, data: Dict[str, Any]) -> None:
        """Set session data.

        Args:
            data: Session data

        Returns:
            None

        Examples:
            ```python
            from starlite import Starlite, get
            from starlite.middleware.session.memory_backend import MemoryBackendConfig

            session_config = MemoryBackendConfig()


            @get(path="/test")
            def get_session_data(request: Request) -> Dict[str, Any]:
                return request.session


            app = Starlite(
                route_handlers=[get_session_data], middleware=[session_config.middleware]
            )

            with TestClient(app=app, session_config=session_config) as client:
                client.set_session_data({"foo": "bar"})
                assert client.get("/test").json() == {"foo": "bar"}
            ```
        """
        with self.portal() as portal:
            portal.call(self._set_session_data_async, data)

    def get_session_data(self) -> Dict[str, Any]:
        """Get session data.

        Returns:
            A dictionary containing session data.

        Examples:
            ```python
            from starlite import Starlite, post
            from starlite.middleware.session.memory_backend import MemoryBackendConfig

            session_config = MemoryBackendConfig()


            @post(path="/test")
            def set_session_data(request: Request) -> None:
                request.session["foo"] == "bar"


            app = Starlite(
                route_handlers=[set_session_data], middleware=[session_config.middleware]
            )

            with TestClient(app=app, session_config=session_config) as client:
                client.post("/test")
                assert client.get_session_data() == {"foo": "bar"}
            ```
        """
        with self.portal() as portal:
            return portal.call(self._get_session_data_async)
