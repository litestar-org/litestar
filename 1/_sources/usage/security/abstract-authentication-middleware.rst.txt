AbstractAuthenticationMiddleware
================================

Starlite exports :class:`AbstractAuthenticationMiddleware <.middleware.authentication.AbstractAuthenticationMiddleware>`,
which is an Abstract Base Class (ABC) that implements the :class:`MiddlewareProtocol <.middleware.base.MiddlewareProtocol>`.
To add authentication to your app using this class as a basis, subclass it and implement the abstract method
:meth:`authenticate_request <.middleware.authentication.AbstractAuthenticationMiddleware.authenticate_request>`:

.. code-block:: python

   from starlite import (
       AbstractAuthenticationMiddleware,
       AuthenticationResult,
       ASGIConnection,
   )


   class MyAuthenticationMiddleware(AbstractAuthenticationMiddleware):
       async def authenticate_request(
           self, connection: ASGIConnection
       ) -> AuthenticationResult:
           # do something here.
           ...

As you can see, ``authenticate_request`` is an async function that receives a connection instance and is supposed to return
an :class:`AuthenticationResult <.middleware.authentication.AuthenticationResult>` instance, which is a pydantic model
that has two attributes:

1. ``user``: a non-optional value representing a user. It's typed as ``Any`` so it receives any value, including ``None``.
2. ``auth``: an optional value representing the authentication scheme. Defaults to ``None``.

These values are then set as part of the "scope" dictionary, and they are made available as
:attr:`Request.user <.connection.request.Request.user>`
and :attr:`Request.auth <.connection.request.Request.auth>` respectively, for HTTP route handlers, and
:attr:`WebSocket.user <.connection.websocket.WebSocket.user>` and
:attr:`WebSocket.auth <.connection.websocket.WebSocket.auth>` for websocket route handlers.

Example: Implementing a JWTAuthenticationMiddleware
---------------------------------------------------

Since the above is quite hard to grasp in the abstract, lets see an example.

We start off by creating a user model. It can be implemented using pydantic, and ODM, ORM etc. For the sake of the
example here lets say it's a pydantic model:

.. code-block:: python
    :caption: my_app/db/models.py

    import uuid

    from sqlalchemy import Column
    from sqlalchemy.dialects.postgresql import UUID
    from sqlalchemy.orm import declarative_base

    Base = declarative_base()


    class User(Base):
        id: uuid.UUID | None = Column(
            UUID(as_uuid=True), default=uuid.uuid4, primary_key=True
        )
        # ... other fields follow, but we only require id for this example



We will also need some utility methods to encode and decode tokens. To this end we will use
the `python-jose <https://github.com/mpdavis/python-jose>`_ library. We will also create a pydantic model representing a
JWT Token:

    .. code-block:: python
        :caption: my_app/security/jwt.py

        from datetime import datetime, timedelta
        from uuid import UUID

        from jose import JWTError, jwt
        from pydantic import BaseModel, UUID4
        from starlite.exceptions import NotAuthorizedException

        from app.config import settings

        DEFAULT_TIME_DELTA = timedelta(days=1)
        ALGORITHM = "HS256"


        class Token(BaseModel):
            exp: datetime
            iat: datetime
            sub: UUID4


        def decode_jwt_token(encoded_token: str) -> Token:
            """
            Helper function that decodes a jwt token and returns the value stored under the ``sub`` key

            If the token is invalid or expired (i.e. the value stored under the exp key is in the past) an exception is raised
            """
            try:
                payload = jwt.decode(
                    token=encoded_token, key=settings.JWT_SECRET, algorithms=[ALGORITHM]
                )
                return Token(**payload)
            except JWTError as e:
                raise NotAuthorizedException("Invalid token") from e


        def encode_jwt_token(user_id: UUID, expiration: timedelta = DEFAULT_TIME_DELTA) -> str:
            """Helper function that encodes a JWT token with expiration and a given user_id"""
            token = Token(
                exp=datetime.now() + expiration,
                iat=datetime.now(),
                sub=user_id,
            )
            return jwt.encode(token.dict(), settings.JWT_SECRET, algorithm=ALGORITHM)

We can now create our authentication middleware:

.. code-block:: python
    :caption: my_app/security/authentication_middleware.py

    from typing import cast, TYPE_CHECKING

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from starlite import (
        AbstractAuthenticationMiddleware,
        AuthenticationResult,
        NotAuthorizedException,
        ASGIConnection,
    )

    from app.db.models import User
    from app.security.jwt import decode_jwt_token

    if TYPE_CHECKING:
        from sqlalchemy.ext.asyncio import AsyncEngine

    API_KEY_HEADER = "X-API-KEY"


    class JWTAuthenticationMiddleware(AbstractAuthenticationMiddleware):
        async def authenticate_request(
            self, connection: ASGIConnection
        ) -> AuthenticationResult:
            """
            Given a request, parse the request api key stored in the header and retrieve the user correlating to the token from the DB
            """

            # retrieve the auth header

        auth_header = connection.headers.get(API_KEY_HEADER)
        if not auth_header:
            raise NotAuthorizedException()

        # decode the token, the result is a ``Token`` model instance
        token = decode_jwt_token(encoded_token=auth_header)

        engine = cast("AsyncEngine", connection.app.state.postgres_connection)
        async with AsyncSession(engine) as async_session:
            async with async_session.begin():
                user = await async_session.execute(select(User).where(User.id == token.sub))
        if not user:
            raise NotAuthorizedException()
        return AuthenticationResult(user=user, auth=token)


Finally, we need to pass our middleware to the Starlite constructor:

.. code-block:: python
    :caption: my_app/main.py

    from starlite import Starlite
    from starlite.middleware.base import DefineMiddleware

    from my_app.security.authentication_middleware import JWTAuthenticationMiddleware

    # you can optionally exclude certain paths from authentication.
    # the following excludes all routes mounted at or under `/schema*`
    auth_mw = DefineMiddleware(JWTAuthenticationMiddleware, exclude="schema")

    app = Starlite(request_handlers=[...], middleware=[auth_mw])

That's it. The ``JWTAuthenticationMiddleware`` will now run for every request, and we would be able to access these in a
http route handler in the following way:

.. code-block:: python

   from starlite import Request, get

   from my_app.db.models import User
   from my_app.security.jwt import Token


   @get("/")
   def my_route_handler(request: Request[User, Token]) -> None:
       user = request.user  # correctly typed as User
       auth = request.auth  # correctly typed as Token
       assert isinstance(user, User)
       assert isinstance(auth, Token)

Or for a websocket route:

.. code-block:: python

   from starlite import WebSocket, websocket

   from my_app.db.models import User
   from my_app.security.jwt import Token


   @websocket("/")
   async def my_route_handler(socket: WebSocket[User, Token]) -> None:
       user = socket.user  # correctly typed as User
       auth = socket.auth  # correctly typed as Token
       assert isinstance(user, User)
       assert isinstance(auth, Token)

And if you'd like to exclude individual routes outside those configured:

.. code-block:: python

   import anyio
   from starlite import Starlite, MediaType, NotFoundException, Response, get
   from starlite.middleware.base import DefineMiddleware

   from my_app.security.authentication_middleware import JWTAuthenticationMiddleware

   # you can optionally exclude certain paths from authentication.
   # the following excludes all routes mounted at or under `/schema*`
   # additionally,
   # you can modify the default exclude key of "exclude_from_auth", by overriding the `exclude_from_auth_key` parameter on the Authentication Middleware
   auth_mw = DefineMiddleware(JWTAuthenticationMiddleware, exclude="schema")


   @get(path="/", exclude_from_auth=True)
   async def site_index() -> Response:
       """Site index"""
       exists = await anyio.Path("index.html").exists()
       if exists:
           async with await anyio.open_file(anyio.Path("index.html")) as file:
               content = await file.read()
               return Response(content=content, status_code=200, media_type=MediaType.HTML)
       raise NotFoundException("Site index was not found")


   app = Starlite(route_handlers=[site_index], middleware=[auth_mw])

And of course use the same kind of mechanism for dependencies:

.. code-block:: python

   from typing import Any

   from starlite import Request, Provide, Router

   from my_app.db.models import User
   from my_app.security.jwt import Token


   async def my_dependency(request: Request[User, Token]) -> Any:
       user = request.user  # correctly typed as User
       auth = request.auth  # correctly typed as Token
       assert isinstance(user, User)
       assert isinstance(auth, Token)


   my_router = Router(
       path="sub-path/", dependencies={"some_dependency": Provide(my_dependency)}
   )
