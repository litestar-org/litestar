from typing import TYPE_CHECKING, Any, Type, Union

from starlite.middleware.base import MiddlewareProtocol

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session

    from starlite.types import ASGIApp, Receive, Scope, Send


class SQLAlchemySessionMiddleware(MiddlewareProtocol):
    __slots__ = ("session_scope_key", "engine_app_state_key", "session_class", "kwargs")

    def __init__(
        self,
        app: "ASGIApp",
        engine_app_state_key: str,
        session_scope_key: str,
        session_class: Union[Type["Session"], Type["AsyncSession"]],
        **kwargs: Any
    ):
        """

        Args:
            app: The 'next' ASGI app to call.
            engine_app_state_key: Key from which to retrieve the DB engine.
            session_scope_key: Key under which to store the DB session created for the request.
            session_class: SQLAlchemy Session class to use.
            **kwargs: Any configuration to pass to the session class.
        """
        self.app = app
        self.session_scope_key = session_scope_key
        self.engine_app_state_key = engine_app_state_key
        self.session_class = session_class
        self.kwargs = kwargs

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        engine = scope["app"].state[self.engine_app_state_key]
        scope[self.session_scope_key] = self.session_class(engine, **self.kwargs)  # type: ignore
        await self.app(scope, receive, send)
