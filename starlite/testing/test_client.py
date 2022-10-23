from typing import TYPE_CHECKING, Any, Dict, Optional, Union, cast

from starlite.app import Starlite
from starlite.exceptions import MissingDependencyException
from starlite.middleware.session import SessionMiddleware

if TYPE_CHECKING:
    from typing_extensions import Literal

    from starlite.middleware.session import SessionCookieConfig
    from starlite.types import ASGIApp

try:
    from starlette.testclient import TestClient as StarletteTestClient
except ImportError as e:
    raise MissingDependencyException(
        "To use starlite.testing, install starlite with 'testing' extra, e.g. `pip install starlite[testing]`"
    ) from e


class TestClient(StarletteTestClient):
    app: Starlite  # type: ignore[assignment]
    """
        Starlite application instance under test.
    """

    def __init__(
        self,
        app: Union[Starlite, "ASGIApp"],
        base_url: str = "http://testserver",
        raise_server_exceptions: bool = True,
        root_path: str = "",
        backend: "Literal['asyncio', 'trio' ]" = "asyncio",
        backend_options: Optional[Dict[str, Any]] = None,
        session_config: Optional["SessionCookieConfig"] = None,
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
        """
        self.session = SessionMiddleware(app=app, config=session_config) if session_config else None
        super().__init__(
            app=app,  # type: ignore[arg-type]
            base_url=base_url,
            raise_server_exceptions=raise_server_exceptions,
            root_path=root_path,
            backend=backend,
            backend_options=backend_options,
        )

    def __enter__(self) -> "TestClient":
        """Starlette's `TestClient.__enter__()` return value is strongly typed
        to return their own `TestClient`, i.e., not-generic to support
        subclassing.

        We override here to provide a nicer typing experience for our user

        Returns:
            TestClient
        """
        return cast("TestClient", super().__enter__())

    def create_session_cookies(self, session_data: Dict[str, Any]) -> Dict[str, str]:
        """Creates raw session cookies that are loaded into the session by the
        Session Middleware. It creates cookies the same way as if they are
        coming from the browser. Your tests must set up session middleware to
        load raw session cookies into the session.

        Args:
            session_data: Dictionary to create raw session cookies from.

        Returns:
            A dictionary with cookie name as key and cookie value as value.

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
        if self.session is None:
            return {}
        encoded_data = self.session.dump_data(data=session_data)
        return {f"{self.session.config.key}-{i}": chunk.decode("utf-8") for i, chunk in enumerate(encoded_data)}

    def get_session_from_cookies(self) -> Dict[str, Any]:
        """Raw session cookies are a serialized image of session which are
        created by session middleware and sent with the response. To assert
        data in session, this method deserializes the raw session cookies and
        creates session from them.

        Returns:
            A dictionary containing session data.

        Examples:

            ```python
            def test_something(self, test_client: TestClient) -> None:
                test_client.get(url="/my_route")
                session = test_client.get_session_from_cookies()
                assert "user" in session
            ```
        """
        if self.session is None:
            return {}
        raw_data = [self.cookies[key].encode("utf-8") for key in self.cookies if self.session.config.key in key]
        return self.session.load_data(data=raw_data)
