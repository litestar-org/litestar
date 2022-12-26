from types import GeneratorType
from typing import TYPE_CHECKING, Any, Dict, Optional, Union, cast
from urllib.parse import unquote

from anyio import Event
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from httpx import Request

    from starlite.testing.async_test_client.client import AsyncTestClient
    from starlite.testing.sync_test_client.client import TestClient
    from starlite.testing.sync_test_client.websocket_test_session import (
        WebSocketTestSession,
    )
    from starlite.types import (
        HTTPDisconnectEvent,
        HTTPRequestEvent,
        Message,
        Receive,
        ReceiveMessage,
        Send,
    )


class ConnectionUpgradeException(Exception):
    def __init__(self, session: "WebSocketTestSession") -> None:
        self.session = session


class SendReceiveContext(TypedDict):
    request_complete: bool
    response_complete: Event
    raw_kwargs: Dict[str, Any]
    response_started: bool
    template: Optional[str]
    context: Optional[Any]


class BaseClientTransport:
    def __init__(
        self,
        client: Union["TestClient", "AsyncTestClient"],
        raise_server_exceptions: bool = True,
        root_path: str = "",
    ) -> None:
        self.client = client
        self.raise_server_exceptions = raise_server_exceptions
        self.root_path = root_path

    @staticmethod
    def create_receive(request: "Request", context: SendReceiveContext) -> "Receive":
        async def receive() -> "ReceiveMessage":
            if context["request_complete"]:
                if not context["response_complete"].is_set():
                    await context["response_complete"].wait()
                disconnect_event: "HTTPDisconnectEvent" = {"type": "http.disconnect"}
                return disconnect_event

            body = cast("Union[bytes, str, GeneratorType]", (request.read() or b""))
            request_event: "HTTPRequestEvent" = {"type": "http.request", "body": b"", "more_body": False}
            if isinstance(body, GeneratorType):  # pragma: no cover
                try:
                    chunk = body.send(None)
                    request_event["body"] = chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
                    request_event["more_body"] = True
                except StopIteration:
                    context["request_complete"] = True
            else:
                context["request_complete"] = True
                request_event["body"] = body if isinstance(body, bytes) else body.encode("utf-8")
            return request_event

        return receive

    @staticmethod
    def create_send(request: "Request", context: SendReceiveContext) -> "Send":
        async def send(message: "Message") -> None:
            if message["type"] == "http.response.start":
                if context["response_started"]:
                    raise AssertionError('Received multiple "http.response.start" messages.')
                context["raw_kwargs"]["status_code"] = message["status"]
                context["raw_kwargs"]["headers"] = [
                    (k.decode("utf-8"), v.decode("utf-8")) for k, v in message.get("headers", [])
                ]
                context["response_started"] = True
            elif message["type"] == "http.response.body":
                if not context["response_started"]:
                    raise AssertionError('Received "http.response.body" without "http.response.start".')
                if context["response_complete"].is_set():
                    raise AssertionError('Received "http.response.body" after response completed.')
                body = message.get("body", b"")
                more_body = message.get("more_body", False)
                if request.method != "HEAD":
                    context["raw_kwargs"]["stream"].write(body)
                if not more_body:
                    context["raw_kwargs"]["stream"].seek(0)
                    context["response_complete"].set()
            elif message["type"] == "http.response.template":  # type: ignore[comparison-overlap] # pragma: no cover
                context["template"] = message["template"]  # type: ignore[unreachable]
                context["context"] = message["context"]

        return send

    def parse_request(self, request: "Request") -> Dict[str, Any]:
        scheme = request.url.scheme
        netloc = unquote(request.url.netloc.decode(encoding="ascii"))
        path = request.url.path
        raw_path = request.url.raw_path
        query = request.url.query.decode(encoding="ascii")
        default_port = 433 if scheme in {"https", "wss"} else 80

        if ":" in netloc:
            host, port_string = netloc.split(":", 1)
            port = int(port_string)
        else:
            host = netloc
            port = default_port

        host_header = request.headers.pop("host", host if port == default_port else f"{host}:{port}")

        headers = [(k.lower().encode(), v.encode()) for k, v in (("host", host_header), *request.headers.items())]

        return {
            "type": "websocket" if scheme in {"ws", "wss"} else "http",
            "path": unquote(path),
            "raw_path": raw_path,
            "root_path": self.root_path,
            "scheme": scheme,
            "query_string": query.encode(),
            "headers": headers,
            "client": ("testclient", 50000),
            "server": (host, port),
        }
