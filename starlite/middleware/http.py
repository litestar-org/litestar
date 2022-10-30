"""The code in this file was adapted from https://github.com/encode/starlette/b
lob/master/starlette/middleware/base.py.

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

from abc import ABC, abstractmethod
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
from starlite.middleware.base import AbstractMiddleware
from starlite.response import Response, StreamingResponse
from starlite.utils import AsyncCallable

DispatchFunction = Callable[
    ["Request[Any, Any]", Callable[["Request[Any, Any]"], Awaitable["Response[Any]"]]],
    "Response[Any]",
]

if TYPE_CHECKING:
    from anyio.abc import TaskGroup

    from starlite.types import ASGIApp, Message, Receive, ReceiveMessage, Scope, Send
    from starlite.types.asgi_types import HTTPDisconnectEvent


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


def _create_body_stream(
    receive_stream: "MemoryObjectReceiveStream[Message]", exception_context: _ExceptionContext
) -> AsyncGenerator[bytes, None]:
    async def body_stream() -> AsyncGenerator[bytes, None]:
        async with receive_stream:
            async for message in receive_stream:
                if message["type"] == "http.response.body":
                    body = message.get("body", b"")
                    if body:
                        yield body
                    if not message.get("more_body", False):
                        break
                elif message["type"] == "http.disconnect":
                    break

        if isinstance(exception_context["exc"], Exception):
            raise exception_context["exc"]

    return body_stream()


def _create_call_next(
    app: "ASGIApp", response_sent: Event, task_group: "TaskGroup", receive: "Receive"
) -> Callable[["Request[Any, Any]"], Awaitable["Response"]]:
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
            raise RuntimeError("No response returned.") from e

        response = StreamingResponse(
            status_code=message["status"],
            content=_create_body_stream(receive_stream=receive_stream, exception_context=exception_context),
        )
        response.headers = {k.decode(response.encoding): v.decode(response.encoding) for k, v in message["headers"]}
        return response

    return call_next


class BaseHTTPMiddleware(AbstractMiddleware, ABC):
    __slots__ = ("dispatch_handler",)

    def __init__(
        self,
        app: "ASGIApp",
        dispatch: Optional[DispatchFunction] = None,
        exclude: Optional[Union[str, List[str]]] = None,
        exclude_opt_key: Optional[str] = None,
    ) -> None:
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
            await response(scope, receive, send)
            response_sent.set()

    @abstractmethod
    async def dispatch(
        self, request: "Request[Any, Any]", call_next: Callable[["Request[Any, Any]"], Awaitable["Response[Any]"]]
    ) -> "Response[Any]":
        """

        Args:
            request:
            call_next:

        Returns:

        """
        raise NotImplementedError("this method must be implemented by subclasses.")
