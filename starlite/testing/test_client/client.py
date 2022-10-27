import warnings
from contextlib import ExitStack, contextmanager
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

from anyio import run as anyio_run
from anyio.from_thread import BlockingPortal, start_blocking_portal

from starlite import HttpMethod, ImproperlyConfiguredException
from starlite.exceptions import MissingDependencyException
from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig
from starlite.middleware.session.cookie_backend import (
    CookieBackend,
    CookieBackendConfig,
)
from starlite.testing.test_client.life_span_handler import LifeSpanHandler
from starlite.testing.test_client.transport import (
    ConnectionUpgradeException,
    TestClientTransport,
)
from starlite.types import ASGIApp

try:
    from httpx import USE_CLIENT_DEFAULT, Client, Response
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
    from typing_extensions import Literal

    from starlite.middleware.session.base import BaseBackendConfig, BaseSessionBackend
    from starlite.testing.test_client.websocket_test_session import WebSocketTestSession


T = TypeVar("T", bound=ASGIApp)
AnySessionBackend = Union[CookieBackend, ServerSideBackend]
AnySessionConfig = Union["ServerSideSessionConfig", "CookieBackendConfig"]


def raise_for_unsupported_session_backend(backend: "BaseSessionBackend") -> None:
    raise ImproperlyConfiguredException(f"Backend of type {type(backend)!r} is currently not supported")


class TestClient(Client, Generic[T]):
    __test__ = False
    blocking_portal: "BlockingPortal"
    lifespan_handler: LifeSpanHandler
    exit_stack: "ExitStack"

    def __init__(
        self,
        app: T,
        base_url: str = "http://testserver",
        raise_server_exceptions: bool = True,
        root_path: str = "",
        backend: "Literal['asyncio', 'trio' ]" = "asyncio",
        backend_options: Optional[Dict[str, Any]] = None,
        session_config: Optional["BaseBackendConfig"] = None,
        cookies: Optional["CookieTypes"] = None,
    ) -> None:
        """A client implementation providing a context manager for testing
        applications.

        Args:
            app: The instance of [Starlite][starlite.app.Starlite] under test.
            base_url: URL scheme and domain for test request paths, e.g. 'http://testserver'.
            raise_server_exceptions: Flag for underlying Starlette test client to raise server exceptions instead of
                wrapping them in an HTTP response.
            root_path: Path prefix for requests.
            backend: The async backend to use, options are "asyncio" or "trio".
            backend_options: 'anyio' options.
            session_config: Configuration for Session Middleware class to create raw session cookies for request to the
                route handlers.
            cookies: Cookies to set on the client.
        """
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
    def session(self) -> "CookieBackend":
        warnings.warn(
            "Accessing the session via this property is deprecated and will be removed in future version."
            "To access the session backend directly, use the session_backend attribute",
            PendingDeprecationWarning,
        )
        if not isinstance(self._session_backend, CookieBackend):
            raise ImproperlyConfiguredException(
                f"Invalid session backend: {type(self._session_backend)!r}. Expected 'CookieBackend'"
            )
        return self._session_backend

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

    def create_session_cookies(self, session_data: Dict[str, Any]) -> Dict[str, str]:
        """Creates raw session cookies that are loaded into the session by the
        Session Middleware. It creates cookies the same way as if they are
        coming from the browser. Your tests must set up session middleware to
        load raw session cookies into the session.

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
        warnings.warn(
            "This method is deprecated and will be removed in a future version. Use"
            "TestClient.set_session_data instead",
            PendingDeprecationWarning,
        )
        if self._session_backend is None:
            return {}
        return self._create_session_cookies(self.session, session_data)

    def get_session_from_cookies(self) -> Dict[str, Any]:
        """Raw session cookies are a serialized image of session which are
        created by session middleware and sent with the response. To assert
        data in session, this method deserializes the raw session cookies and
        creates session from them.

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
        warnings.warn(
            "This method is deprecated and will be removed in a future version. Use"
            "TestClient.get_session_data instead",
            PendingDeprecationWarning,
        )
        if self._session_backend is None:
            return {}
        return self.get_session_data()

    @staticmethod
    def _create_session_cookies(backend: CookieBackend, data: Dict[str, Any]) -> Dict[str, str]:
        encoded_data = backend.dump_data(data=data)
        return {cookie.key: cast("str", cookie.value) for cookie in backend._create_session_cookies(encoded_data)}

    async def _set_session_data_async(self, data: Dict[str, Any]) -> None:
        # TODO: Expose this in the async client

        if isinstance(self.session_backend, ServerSideBackend):
            serialized_data = self.session_backend.serlialize_data(data)
            session_id = self.cookies.setdefault(
                self.session_backend.config.key, self.session_backend.generate_session_id()
            )
            await self.session_backend.set(session_id, serialized_data)
        elif isinstance(self.session_backend, CookieBackend):
            for key, value in self._create_session_cookies(self.session_backend, data).items():
                self.cookies.set(key, value)
        else:
            raise_for_unsupported_session_backend(self.session_backend)

    async def _get_session_data_async(self) -> Dict[str, Any]:
        # TODO: Expose this in the async client

        if isinstance(self.session_backend, ServerSideBackend):
            session_id = self.cookies.get(self.session_backend.config.key)
            if session_id:
                data = await self.session_backend.get(session_id)
                return self.session_backend.deserialize_data(data)
        elif isinstance(self.session_backend, CookieBackend):
            raw_data = [
                self.cookies[key].encode("utf-8") for key in self.cookies if self.session_backend.config.key in key
            ]
            if raw_data:
                return self.session_backend.load_data(data=raw_data)
        else:
            raise_for_unsupported_session_backend(self.session_backend)
        return {}

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
        anyio_run(self._set_session_data_async, data)

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
        return anyio_run(self._get_session_data_async)
