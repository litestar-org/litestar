from io import BytesIO
from typing import TYPE_CHECKING, Any, Dict, cast

from anyio import Event
from httpx import BaseTransport, ByteStream, Request, Response

from starlite.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from starlite.testing.base.transport_base import (
    BaseClientTransport,
    ConnectionUpgradeException,
    SendReceiveContext,
)
from starlite.testing.sync_test_client.websocket_test_session import (
    WebSocketTestSession,
)

if TYPE_CHECKING:
    from starlite.testing.sync_test_client.client import TestClient
    from starlite.types import WebSocketScope


class TestClientTransport(BaseTransport, BaseClientTransport):
    def __init__(
        self,
        client: "TestClient",
        raise_server_exceptions: bool = True,
        root_path: str = "",
    ) -> None:
        BaseClientTransport.__init__(
            self, client=client, raise_server_exceptions=raise_server_exceptions, root_path=root_path
        )

    def handle_request(self, request: "Request") -> "Response":
        scope = self.parse_request(request=request)
        if scope["type"] == "websocket":
            scope.update(
                subprotocols=[value.strip() for value in request.headers.get("sec-websocket-protocol", "").split(",")]
            )
            session = WebSocketTestSession(client=self.client, scope=cast("WebSocketScope", scope))  # type: ignore [arg-type]
            raise ConnectionUpgradeException(session)

        scope.update(method=request.method, http_version="1.1", extensions={"http.response.template": {}})

        raw_kwargs: Dict[str, Any] = {"stream": BytesIO()}

        try:
            with self.client.portal() as portal:
                response_complete = portal.call(Event)
                context: SendReceiveContext = {
                    "response_complete": response_complete,
                    "request_complete": False,
                    "raw_kwargs": raw_kwargs,
                    "response_started": False,
                    "template": None,
                    "context": None,
                }
                portal.call(
                    self.client.app,  # type: ignore [arg-type]
                    scope,
                    self.create_receive(request=request, context=context),
                    self.create_send(request=request, context=context),
                )
        except BaseException as exc:  # pragma: no cover # pylint: disable=W0703
            if self.raise_server_exceptions:
                raise exc
            return Response(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, headers=[], stream=ByteStream(b""), request=request
            )
        else:
            if not context["response_started"]:  # pragma: no cover
                if self.raise_server_exceptions:  # noqa: SIM102
                    if not context["response_started"]:
                        raise AssertionError("TestClient did not receive any response.")
                return Response(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR, headers=[], stream=ByteStream(b""), request=request
                )

            stream = ByteStream(raw_kwargs.pop("stream", BytesIO()).read())
            response = Response(**raw_kwargs, stream=stream, request=request)
            setattr(response, "template", context["template"])  # noqa: B010
            setattr(response, "context", context["context"])  # noqa: B010
            return response
