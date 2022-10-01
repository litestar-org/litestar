from typing import TYPE_CHECKING, Optional, Union, cast

from sqlalchemy.ext.asyncio import AsyncSession

from starlite.middleware.base import MiddlewareProtocol

if TYPE_CHECKING:

    from sqlalchemy.orm import Session

    from starlite.types import ASGIApp, Message, Receive, Scope, Send


class SQLAlchemySessionMiddleware(MiddlewareProtocol):
    __slots__ = ("session_scope_key", "engine_app_state_key", "session_class", "kwargs")

    def __init__(
        self,
        app: "ASGIApp",
        session_scope_key: str,
    ):
        """

        Args:
            app: The 'next' ASGI app to call.
            session_scope_key: Key under which a session is potentially stored.
        """
        self.app = app
        self.session_scope_key = session_scope_key

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        async def send_wrapper(message: "Message") -> None:
            session = cast("Optional[Union[Session, AsyncSession]]", scope.get(self.session_scope_key))
            if session and message["type"] in {
                "http.response.start",
                "http.disconnect",
                "websocket.disconnect",
                "websocket.close",
            }:
                if isinstance(session, AsyncSession):
                    await session.close()
                else:
                    session.close()
                del scope[self.session_scope_key]  # type: ignore
            await send(message)

        await self.app(scope, receive, send_wrapper)
