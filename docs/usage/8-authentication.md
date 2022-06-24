# Authentication

Starlite is agnostic as to what kind of authentication mechanism(s) an app should use - you can use cookies, JWT tokens,
OpenID connect depending on your use-case. It also does not implement any of these mechanisms for you. What it does is
offer an opinion as to where authentication should occur, namely - as part of your middleware stack. This is in
accordance with Starlette and many other frameworks (e.g. Django, NestJS etc.).

## Authentication Middleware

Starlite exports a class called `AbstractAuthenticationMiddleware`, which, as its name implies, is an Abstract Base
Class (ABC) that implements the [middleware protocol](7-middleware.md#the-middleware-protocol). To add authentication to
your app simply subclass `AbstractAuthenticationMiddleware` and implement the method `authenticate_request`, which has
the following signature:

```python
from starlite import AuthenticationResult, Request


async def authenticate_request(request: Request) -> AuthenticationResult:
    ...
```

### Example: Create a JWT Authentication Middleware

For example, lets say we wanted to implement a JWT token based authentication. We start off by creating a user model. It
can be implemented using pydantic, and ODM, ORM etc. For the sake of the example here lets say its a pydantic model:

```python
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
```

We will also need some utility methods to encode and decode tokens. To this end we will use
the [python-jose](https://github.com/mpdavis/python-jose) library. We will also create a pydantic model representing a
JWT Token:

```python title="my_app/security/jwt.py"
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
    Helper function that decodes a jwt token and returns the value stored under the 'sub' key

    If the token is invalid or expired (i.e. the value stored under the exp key is in the past) an exception is raised
    """
    try:
        payload = jwt.decode(token=encoded_token, key=settings.JWT_SECRET, algorithms=[ALGORITHM])
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
```

We can now create our authentication middleware:

```python title="my_app/security/authentication_middleware.py"
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from starlette.requests import HTTPConnection
from starlite import AbstractAuthenticationMiddleware, AuthenticationResult, NotAuthorizedException

from app.db.models import User
from app.security.jwt import decode_jwt_token

API_KEY_HEADER = "X-API-KEY"


class JWTAuthenticationMiddleware(AbstractAuthenticationMiddleware):
    async def authenticate_request(self, request: HTTPConnection) -> AuthenticationResult:
        """
        Given a request, parse the request api key stored in the header and retrieve the user correlating to the token from the DB

        """

        # retrieve the auth header
        auth_header = request.headers.get(API_KEY_HEADER)
        if not auth_header:
            raise NotAuthorizedException()

        # decode the token, the result is a 'Token' model instance
        token = decode_jwt_token(encoded_token=auth_header)

        engine = cast(AsyncEngine, request.app.state.postgres_connection)
        async with AsyncSession(engine) as async_session:
            async with async_session.begin():
                user = await async_session.execute(select(User).where(User.id == token.sub))
        if not user:
            raise NotAuthorizedException()
        return AuthenticationResult(user=user, auth=token)
```

Finally, we need to pass our middleware to the Starlite constructor:

```python title="my_app/main.py"
from starlite import Starlite

from my_app.security.authentication_middleware import JWTAuthenticationMiddleware


app = Starlite(request_handlers=[...], middleware=[JWTAuthenticationMiddleware])
```

That's it. The `JWTAuthenticationMiddleware` will now run for every request.

### Authentication Result

The method `authenticate_request` specified by `AbstractAuthenticationMiddleware` expects the return value to be an
instance of `AuthenticationResult`. This is a pydantic model that has two attributes:

1. `user`: a non-optional value representing a user. It's typed as `Any` so it receives any value, including `None`.
2. `auth`: an optional value representing the authentication scheme. Defaults to `None`.

These values are then set as part of the "scope" dictionary, and they are made available as `Request.user`
and `Request.auth` respectively, for HTTP route handlers, and `WebSocket.user` and `WebSocket.auth` for websocket route handlers.

Building on the previous example, we would be able to access these in an http route handler in the following way:

```python
from starlite import Request, get

from my_app.db.models import User
from my_app.security.jwt import Token


@get("/")
def my_route_handler(request: Request[User, Token]) -> None:
    user = request.user  # correctly typed as User
    auth = request.auth  # correctly typed as Token
    ...
```

Or for a websocket route:

```python
from starlite import WebSocket, websocket

from my_app.db.models import User
from my_app.security.jwt import Token


@websocket("/")
async def my_route_handler(socket: WebSocket[User, Token]) -> None:
    user = socket.user  # correctly typed as User
    auth = socket.auth  # correctly typed as Token
    ...
```

And of course use the same kind of mechanism for dependencies:

```python
from typing import Any

from starlite import Request, Provide, Router

from my_app.db.models import User
from my_app.security.jwt import Token


async def my_dependency(request: Request[User, Token]) -> Any:
    user = request.user  # correctly typed as User
    auth = request.auth  # correctly typed as Token
    ...


my_router = Router(
    path="sub-path/", dependencies={"some_dependency": Provide(my_dependency)}
)
```
