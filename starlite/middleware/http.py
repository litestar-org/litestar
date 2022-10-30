"""This file includes code that has been adapted from
https://github.com/encode/starlette/b lob/master/starlette/middleware/base.py.

Copyright © 2018, [Encode OSS Ltd](https://www.encode.io/).
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    List,
    Optional,
    Union,
    cast,
)

from anyio import (
    BrokenResourceError,
    EndOfStream,
    Event,
    create_memory_object_stream,
    create_task_group,
)
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from typing_extensions import TypedDict

from starlite.connection import Request
from starlite.enums import ScopeType
from starlite.exceptions import InternalServerException
from starlite.middleware.base import AbstractMiddleware, DefineMiddleware
from starlite.response import Response, StreamingResponse
from starlite.utils import AsyncCallable

if TYPE_CHECKING:
    from anyio.abc import TaskGroup

    from starlite.types import ASGIApp, Message, Receive, ReceiveMessage, Scope, Send
    from starlite.types.asgi_types import HTTPDisconnectEvent


CallNext = Callable[["Request[Any, Any]"], Awaitable["Response[Any]"]]
DispatchCallable = Callable[["Request[Any, Any]", CallNext], Awaitable["Response[Any]"]]


class _ExceptionContext(TypedDict):
    exc: Optional[Exception]


def _create_receive(response_sent: "Event", receive: "Receive") -> "Receive":
    async def wrapped_receive() -> "ReceiveMessage":
        if not response_sent.is_set():
            async with create_task_group() as task_group:

                async def cancel_on_wait() -> None:
                    await response_sent.wait()
                    task_group.cancel_scope.cancel()

                task_group.start_soon(cancel_on_wait)

                return await receive()

        return cast("HTTPDisconnectEvent", {"type": "http.disconnect"})

    return wrapped_receive


def _create_send(send_stream: "MemoryObjectSendStream[Message]") -> "Send":
    async def wrapped_send(message: "Message") -> None:
        try:
            await send_stream.send(message)
        except BrokenResourceError:
            # receive_stream has been closed, i.e. response_sent has been set.
            return

    return wrapped_send


async def _call_next_app(
    app: "ASGIApp",
    exception_content: _ExceptionContext,
    receive: "Receive",
    response_sent: "Event",
    scope: "Scope",
    send_stream: "MemoryObjectSendStream[Message]",
) -> None:
    try:
        await app(
            scope,
            _create_receive(response_sent=response_sent, receive=receive),
            _create_send(send_stream=send_stream),
        )
    except Exception as exc:  # pylint: disable=broad-except
        exception_content["exc"] = exc
    finally:
        send_stream.close()


def _create_body_stream(receive_stream: "MemoryObjectReceiveStream[Message]") -> AsyncGenerator[bytes, None]:
    async def body_stream() -> AsyncGenerator[bytes, None]:
        async with receive_stream:
            async for message in receive_stream:
                if message["type"] == "http.response.body":
                    body = message.get("body", b"")
                    if body:
                        yield body
                    if not message.get("more_body", False):
                        break

    return body_stream()


def _create_call_next(app: "ASGIApp", response_sent: Event, task_group: "TaskGroup", receive: "Receive") -> CallNext:
    async def call_next(request: "Request[Any, Any]") -> Response:
        exception_context: "_ExceptionContext" = {"exc": None}
        send_stream, receive_stream = create_memory_object_stream()

        async def close_receive_stream_on_response_sent() -> None:
            await response_sent.wait()
            receive_stream.close()

        task_group.start_soon(close_receive_stream_on_response_sent)
        task_group.start_soon(
            _call_next_app, app, exception_context, receive, response_sent, request.scope, send_stream
        )

        try:
            message = await receive_stream.receive()
        except EndOfStream as e:
            if isinstance(exception_context["exc"], Exception):
                raise exception_context["exc"] from e  # pylint: disable=raising-bad-type
            raise InternalServerException(detail="No response returned.") from e

        response = StreamingResponse(
            status_code=message["status"],
            content=_create_body_stream(receive_stream=receive_stream),
        )
        response.headers = {k.decode(response.encoding): v.decode(response.encoding) for k, v in message["headers"]}
        return response

    return call_next


class BaseHTTPMiddleware(AbstractMiddleware):
    __slots__ = ("dispatch_handler",)

    def __init__(
        self,
        app: "ASGIApp",
        dispatch: Optional[DispatchCallable] = None,
        exclude: Optional[Union[str, List[str]]] = None,
        exclude_opt_key: Optional[str] = None,
    ) -> None:
        """This class is a utility class for creating easy to use middleware
        that runs on HTTP requests (that is, not requests with the scope type
        'websocket'). Its derived from the Starlette class of the same name and
        is compatible with it.

        Notes:
             - In order to provide the "expressJS" like interface of the dispatch function, this middleware does some rather
              complex work. While the user is not exposed to this, this creates certain limitations:
                1. this middleware is incompatible with contextvars.
                2. background tasks will not be executed on the response for any handler function for which this
                    middleware is defined.
                3. this middleware does impact performance.

              You should therefore evaluate the ease of use it offers vis-a-vis the downsides for your use case.

        Args:
            app: The 'next' ASGI app to call.
            dispatch: An optional [DispatchCallable][starlite.middleware.http.DispatchCallable]. If provided it will
                supersede the class `dispatch` method.
            exclude: A pattern or list of patterns to match against a request's path.
                If a match is found, the middleware will be skipped. .
            exclude_opt_key: An identifier that is set in the route handler
                'opt' key which allows skipping the middleware.
        """
        super().__init__(app=app, exclude=exclude, exclude_opt_key=exclude_opt_key, scopes={ScopeType.HTTP})
        self.dispatch_handler = AsyncCallable(dispatch) if dispatch else None

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        response_sent = Event()

        async with create_task_group() as task_group:
            request = Request[Any, Any](scope, receive=receive)
            dispatch = self.dispatch_handler or self.dispatch
            call_next = _create_call_next(
                app=self.app, response_sent=response_sent, task_group=task_group, receive=receive
            )
            response = await dispatch(request, call_next)
            await response(scope, receive, send)  # pyright: ignore
            response_sent.set()

    async def dispatch(self, request: "Request[Any, Any]", call_next: CallNext) -> "Response[Any]":
        """

        Args:
            request: A [Request][starlite.connection.Request] instance.
            call_next: A callable that receives a [Request][starlite.connection.Request]
                and returns a [Response][starlite.response.Response].

        Returns:
            A [Response][starlite.response.Response] instance.
        """
        raise NotImplementedError("this method must be implemented by subclasses.")  # pragma: no cover


def http_middleware(
    exclude: Optional[Union[str, List[str]]] = None,
    exclude_opt_key: Optional[str] = None,
) -> Callable[[DispatchCallable], DefineMiddleware]:
    """This is a decorator that can be used to define middleware by decorating
    a [DispatchCallable][starlite.middleware.http.DispatchCallable]:

    Examples:

        ```python
        from typing import Any
        from starlite import Starlite, Request, Response, CallNext, http_middleware


        @http_middleware()
        async def my_middleware(
            request: "Request[Any, Any]", call_next: "CallNext"
        ) -> "Response[Any]":
            response = await call_next(request)
            response.set_header("X-My-Header", "123")
            return response


        app = Starlite(route_handlers=[], middleware=[my_middleware])
        ```

    Args:
        exclude: A pattern or list of patterns to match against a request's path.
            If a match is found, the middleware will be skipped. .
        exclude_opt_key: An identifier that is set in the route handler
            'opt' key which allows skipping the middleware.

    Returns:
        A decorator that accepts a [DispatchCallable][starlite.middleware.http.DispatchCallable].
    """

    def decorator(
        dispatch: DispatchCallable,
    ) -> DefineMiddleware:
        """

        Args:
            dispatch: A [DispatchCallable][starlite.middleware.http.DispatchCallable]

        Returns:
            An instance of [DefineMiddleware][starlite.middleware.base.DefineMiddleware].
        """
        return DefineMiddleware(BaseHTTPMiddleware, dispatch=dispatch, exclude=exclude, exclude_opt_key=exclude_opt_key)

    return decorator
