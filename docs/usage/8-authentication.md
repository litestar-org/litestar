# Authentication

Starlite is agnostic as to what kind of authentication mechanism(s) an app should use - you can use cookies, JWT tokens,
OpenID connect and so on and so forth depending on your use-case. It also does not implement any of these mechanisms for
you. What it does is offer an opinion as to where authentication should occur, namely - as part of your middleware
stack. This is in accordance with Starlette and many other frameworks (e.g. Django, NestJS etc.).

## AbstractAuthenticationMiddleware

Starlite exports a class called `AbstractAuthenticationMiddleware`, which as its name implies is an Abstract Base
Class (ABC) that implements the [middleware protocol](7-middleware.md#the-middleware-protocol). To add authentication to
your app simply subclass `AbstractAuthenticationMiddleware` and implement the method `authenticate_request`, which has
the following signature:

```python
from starlite import AuthenticationResult, Request


async def authenticate_request(request: Request) -> AuthenticationResult:
    ...
```

### Example: JWTAuthenticationMiddleware

For example, lets say we wanted to implement a JWT token based authentication. We created two pydantic models, one for
the user which we persist into some sort of DB, and another for the token data:

```python title="my_app/models.py"
from datetime import datetime

from pydantic import BaseModel, UUID4


class User(BaseModel):
    id: UUID4
    # ... lots of other fields


class Token(BaseModel):
    exp: datetime
    iat: datetime
    sub: UUID4
```

!!! note In the real world `User` would be a database model and would be persisted using a 3rd party library. The
current example just assumes this is happening magically.

We will now need some utility methods to encode and decode tokens. We will use
the [python-jose](https://github.com/mpdavis/python-jose) library, which is an excellent choice.

```python title="my_app/utils/jwt.py"
from datetime import datetime, timedelta
from os import environ

from jose import JWTError, jwt
from starlite import NotAuthorizedException, ValidationException

from my_app.models import Token, User


DEFAULT_TIME_DELTA = timedelta(days=1)


def decode_jwt_token(encoded_token: str, secret: str) -> Token:
    """
    Helper function that decodes a jwt token and returns the value stored under the 'sub' key

    If the token is invalid or expired (i.e. the value stored under the exp key is in the past) an exception is raised
    """
    try:
        payload = jwt.decode(token=encoded_token, key=secret, algorithms=["HS256"])
        return Token(**payload)
    except JWTError as e:
        raise NotAuthorizedException("Invalid token") from e


## not used in the example, but required for real life implementations and testing
def encode_jwt_token(user_id: str, secret: str, expiration: timedelta = DEFAULT_TIME_DELTA) -> str:
    """Helper function that encodes a JWT token with expiration and a given user_id"""
    payload = JWTToken(
        exp=datetime.now() + expiration,
        iat=datetime.now(),
        sub=user_id,
    )
    return jwt.encode(payload, secret, algorithm="HS256")


def get_jwt_secret() -> str:
    """A getter that retrieves the JWT secret passed as an environment variable"""
    secret = environ.get("JWT_SECRET")
    if not secret:
        raise ValidationException("Missing required ENV variable 'JWT_SECRET'")
    return secret
```

We can now create our authentication middleware:

```python title="my_app/middleware/auth.py"
from starlite import AbstractAuthenticationMiddleware, AuthenticationResult, NotAuthorizedException, Request

from my_app.utils.jwt import decode_jwt_token, get_jwt_secret
from my_app.persistence import get_connection
from my_app.models import User

API_KEY_HEADER = "X-API-KEY"


class JWTAuthenticationMiddleware(AbstractAuthenticationMiddleware):
    def authenticate_request(self, request: Request) -> AuthenticationResult:
        """Given a request, parse the request api key stored in the header and retrieve the user"""
        # retrieve the auth header
        auth_header = request.headers.get(API_KEY_HEADER)
        if not auth_header:
            raise NotAuthorizedException()
        # retrieve the secret from environment
        secret = get_jwt_secret()
        # decode the token
        token = decode_jwt_token(encoded_token=auth_header, secret=secret)

        # retrieve the user from the database using the id that is stored as the sub value
        # pseudo-code below is similar to the syntax used by the ODMantic and SQLModel libraries
        user = await get_connection().find(User, User.id == token.sub)
        if not user:
            raise NotAuthorizedException()
        return AuthenticationResult(user=user, auth=token)
```

Finally, we need to pass it to the Starlite constructor:

```python title="my_app/main.py"
from starlite import Starlite

from my_app.middleware.auth import JWTAuthenticationMiddleware


app = Starlite(request_handlers=[...], middleware=[JWTAuthenticationMiddleware])
```

### Authentication Result

`AuthenticationResult`, which is the return value of `authenticate_request` is a pydantic model that has two attributes:

1. `user`: a non-optional value representing a user. It's typed as `Any` so it receives any value, including `None`.
2. `auth`: an optional value representing the authentication scheme. Defaults to `None`.

These values are then set as part of the "scope" dictionary, and they are made available as `Request.user`
and `Request.auth` respectively.

Building on the previous example, we would be able to access these in a route handler function or a dependency to be
injected in the following way:

```python
from starlite import Request

from my_app.models import User, Token


def my_endpoint(request: Request[User, Token]) -> None:
    user = request.user  # correctly typed as User
    auth = request.auth  # correctly typed as Token
    ...
```
