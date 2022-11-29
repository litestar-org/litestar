from os import environ
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from starlite import (
    ASGIConnection,
    OpenAPIConfig,
    Request,
    Response,
    Starlite,
    get,
    post,
)
from starlite.contrib.jwt import JWTCookieAuth, Token


# Let's assume we have a User model that is a pydantic model.
# This though is not required - we need some sort of user class -
# but it can be any arbitrary value, e.g. an SQLAlchemy model, a representation of a MongoDB  etc.
class User(BaseModel):
    id: UUID
    name: str
    email: EmailStr


# The JWTAuth package requires a retrieve handler callable that receives the JWT token model and the ASGI connection
# and returns the 'User' instance correlating to it.
#
# Notes:
# - 'User' can be any arbitrary value you decide upon.
# - The callable can be either sync or async - both will work.
async def retrieve_user_handler(token: Token, connection: ASGIConnection[Any, Any, Any]) -> Optional[User]:
    # logic here to retrieve the user instance
    cached_value = await connection.cache.get(token.sub)
    if cached_value:
        return User(**cached_value)
    return None


jwt_cookie_auth = JWTCookieAuth[User](
    retrieve_user_handler=retrieve_user_handler,
    token_secret=environ.get("JWT_SECRET", "abcd123"),
    # we are specifying which endpoints should be excluded from authentication. In this case the login endpoint
    # and our openAPI docs.
    exclude=["/login", "/schema"],
    # Tip: We can optionally supply cookie options to the configuration.  Here is an example of enabling the secure cookie option
    # auth_cookie_options=CookieOptions(secure=True),
)


# Given an instance of 'JWTCookieAuth' we can create a login handler function:
@post("/login")
async def login_handler(request: "Request[Any, Any]", data: User) -> Response[User]:
    await request.cache.set(str(data.id), data.dict())
    response = jwt_cookie_auth.login(identifier=str(data.id), response_body=data)

    # you can do whatever you want to update the response instance here
    # e.g. response.set_cookie(...)

    return response


# We also have some other routes, for example:
@get("/some-path")
def some_route_handler(request: Request[User, Token]) -> Any:
    # request.user is set to the instance of user returned by the middleware
    assert isinstance(request.user, User)
    # request.auth is the instance of 'starlite_jwt.Token' created from the data encoded in the auth header
    assert isinstance(request.auth, Token)
    # do stuff ...


# We create our OpenAPIConfig as usual - the JWT security scheme will be injected into it.
openapi_config = OpenAPIConfig(
    title="My API",
    version="1.0.0",
)

# We initialize the app instance and pass the jwt_cookie_auth 'on_app_init' handler to the constructor.
# The hook handler will inject the JWT middleware and openapi configuration into the app.
app = Starlite(
    route_handlers=[login_handler, some_route_handler],
    on_app_init=[jwt_cookie_auth.on_app_init],
    openapi_config=openapi_config,
)
