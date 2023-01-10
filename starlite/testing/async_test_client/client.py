from contextlib import AsyncExitStack
from http.cookiejar import CookieJar
from typing import TYPE_CHECKING, Any, Dict, Generic, Mapping, Optional, TypeVar, Union

from starlite import HttpMethod
from starlite.datastructures import MutableScopeHeaders
from starlite.exceptions import MissingDependencyException
from starlite.testing.base.client_base import (
    BaseTestClient,
    fake_asgi_connection,
    fake_http_send_message,
)
from starlite.testing.life_span_handler import LifeSpanHandler

# from starlite.testing.async_test_client.transport import AsyncTestClientTransport
from starlite.testing.transport import TestClientTransport
from starlite.types import AnyIOBackend, ASGIApp

try:
    from httpx import USE_CLIENT_DEFAULT, AsyncClient, Cookies, Request, Response
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

    from starlite.middleware.session.base import BaseBackendConfig


T = TypeVar("T", bound=ASGIApp)


class AsyncTestClient(AsyncClient, BaseTestClient, Generic[T]):
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
        BaseTestClient.__init__(
            self,
            app=app,
            base_url=base_url,
            backend=backend,
            backend_options=backend_options,
            session_config=session_config,
        )
        AsyncClient.__init__(
            self,
            app=app,
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

    async def __aenter__(self) -> "AsyncTestClient[T]":
        async with AsyncExitStack() as stack:
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
        extensions: Optional[Mapping[str, Any]] = None,
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
        return await AsyncClient.request(
            self,
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

    async def get(  # type: ignore [override]
        self,
        url: "URLTypes",
        *,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Mapping[str, Any]] = None,
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
        return await AsyncClient.get(
            self,
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def options(
        self,
        url: "URLTypes",
        *,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Mapping[str, Any]] = None,
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
        return await AsyncClient.options(
            self,
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def head(
        self,
        url: "URLTypes",
        *,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Mapping[str, Any]] = None,
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
        return await AsyncClient.head(
            self,
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def post(
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
        extensions: Optional[Mapping[str, Any]] = None,
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
        return await AsyncClient.post(
            self,
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

    async def put(
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
        extensions: Optional[Mapping[str, Any]] = None,
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
        return await AsyncClient.put(
            self,
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

    async def patch(
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
        extensions: Optional[Mapping[str, Any]] = None,
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
        return await AsyncClient.patch(
            self,
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

    async def delete(
        self,
        url: "URLTypes",
        *,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Mapping[str, Any]] = None,
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
        return await AsyncClient.delete(
            self,
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def set_session_data_async(self, data: Dict[str, Any]) -> None:
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

    async def get_session_data_async(self) -> Dict[str, Any]:
        return await self.session_backend.load_from_connection(
            connection=fake_asgi_connection(
                app=self.app,
                cookies=dict(self.cookies),
            ),
        )
