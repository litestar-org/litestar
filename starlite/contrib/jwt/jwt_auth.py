from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Generic, Literal, Optional, Type, Union

from pydantic_openapi_schema.v3_1_0 import (
    Components,
    OAuthFlow,
    OAuthFlows,
    SecurityRequirement,
    SecurityScheme,
)

from starlite import Cookie, DefineMiddleware, Response
from starlite.contrib.jwt.jwt_token import Token
from starlite.contrib.jwt.middleware import (
    JWTAuthenticationMiddleware,
    JWTCookieAuthenticationMiddleware,
)
from starlite.enums import MediaType
from starlite.security.base import AbstractSecurityConfig, UserType
from starlite.status_codes import HTTP_201_CREATED


class JWTAuth(Generic[UserType], AbstractSecurityConfig[UserType, Token]):
    """JWT Authentication Configuration.

    This class is the main entry point to the library, and it includes methods to create the middleware, provide login
    functionality, and create OpenAPI documentation.
    """

    algorithm: str = "HS256"
    """Algorithm to use for JWT hashing."""
    auth_header: str = "Authorization"
    """Request header key from which to retrieve the token.

    E.g. 'Authorization' or 'X-Api-Key'.
    """
    default_token_expiration: timedelta = timedelta(days=1)
    """The default value for token expiration."""
    token_secret: str
    """Key with which to generate the token hash.

    Notes:
        - This value should be kept as a secret and the standard practice is to inject it into the environment.
    """
    openapi_security_scheme_name: str = "BearerToken"
    """The value to use for the OpenAPI security scheme and security requirements."""
    description: str = "JWT api-key authentication and authorization."
    """Description for the OpenAPI security scheme."""
    authentication_middleware_class: Type[JWTAuthenticationMiddleware] = JWTAuthenticationMiddleware
    """The authentication middleware class to use.

    Must inherit from [JWTAuthenticationMiddleware][starlite.contrib.jwt.JWTAuthenticationMiddleware]
    """

    @property
    def openapi_components(self) -> Components:
        """Create OpenAPI documentation for the JWT auth schema used.

        Returns:
            An [Components][pydantic_openapi_schema.v3_1_0.components.Components] instance.
        """
        return Components(
            securitySchemes={
                self.openapi_security_scheme_name: SecurityScheme(
                    type="http",
                    scheme="Bearer",
                    name=self.auth_header,
                    bearerFormat="JWT",
                    description=self.description,
                )
            }
        )

    @property
    def security_requirement(self) -> SecurityRequirement:
        """Return OpenAPI 3.1.

        [SecurityRequirement][pydantic_openapi_schema.v3_1_0.security_requirement.SecurityRequirement]

        Returns:
            An OpenAPI 3.1 [SecurityRequirement][pydantic_openapi_schema.v3_1_0.security_requirement.SecurityRequirement] dictionary.
        """
        return {self.openapi_security_scheme_name: []}

    @property
    def middleware(self) -> DefineMiddleware:
        """Create `JWTAuthenticationMiddleware` wrapped in Starlite's `DefineMiddleware`.

        Returns:
            An instance of [DefineMiddleware][starlite.middleware.base.DefineMiddleware].
        """
        return DefineMiddleware(
            self.authentication_middleware_class,
            algorithm=self.algorithm,
            auth_header=self.auth_header,
            exclude=self.exclude,
            exclude_opt_key=self.exclude_opt_key,
            retrieve_user_handler=self.retrieve_user_handler,
            scopes=self.scopes,
            token_secret=self.token_secret,
        )

    def login(
        self,
        identifier: str,
        *,
        response_body: Optional[Any] = None,
        response_media_type: Union[str, MediaType] = MediaType.JSON,
        response_status_code: int = HTTP_201_CREATED,
        token_expiration: Optional[timedelta] = None,
        token_issuer: Optional[str] = None,
        token_audience: Optional[str] = None,
        token_unique_jwt_id: Optional[str] = None,
    ) -> Response[Any]:
        """Create a response with a JWT header. Calls the 'JWTAuth.store_token_handler' to persist the token 'sub'.

        Args:
            identifier: Unique identifier of the token subject. Usually this is a user ID or equivalent kind of value.
            response_body: An optional response body to send.
            response_media_type: An optional 'Content-Type'. Defaults to 'application/json'.
            response_status_code: An optional status code for the response. Defaults to '201 Created'.
            token_expiration: An optional timedelta for the token expiration.
            token_issuer: An optional value of the token 'iss' field.
            token_audience: An optional value for the token 'aud' field.
            token_unique_jwt_id: An optional value for the token 'jti' field.

        Returns:
            A [Response][starlite.response.Response] instance.
        """
        encoded_token = self.create_token(
            identifier=identifier,
            token_expiration=token_expiration,
            token_issuer=token_issuer,
            token_audience=token_audience,
            token_unique_jwt_id=token_unique_jwt_id,
        )
        return Response(
            content=response_body,
            headers={self.auth_header: self.format_auth_header(encoded_token)},
            media_type=response_media_type,
            status_code=response_status_code,
        )

    def create_token(
        self,
        identifier: str,
        token_expiration: Optional[timedelta] = None,
        token_issuer: Optional[str] = None,
        token_audience: Optional[str] = None,
        token_unique_jwt_id: Optional[str] = None,
    ) -> str:
        """Create a Token instance from the passed in parameters, persists and returns it.

        Args:
            identifier: Unique identifier of the token subject. Usually this is a user ID or equivalent kind of value.
            token_expiration: An optional timedelta for the token expiration.
            token_issuer: An optional value of the token 'iss' field.
            token_audience: An optional value for the token 'aud' field.
            token_unique_jwt_id: An optional value for the token 'jti' field.

        Returns:
            The created token.
        """
        token = Token(
            sub=identifier,
            exp=(datetime.now(timezone.utc) + (token_expiration or self.default_token_expiration)),
            iss=token_issuer,
            aud=token_audience,
            jti=token_unique_jwt_id,
        )
        return token.encode(secret=self.token_secret, algorithm=self.algorithm)

    def format_auth_header(self, encoded_token: str) -> str:
        """Format a token according to the specified OpenAPI scheme.

        Args:
            encoded_token: An encoded JWT token

        Returns:
            The encoded token formatted for the HTTP headers
        """
        security = self.openapi_components.securitySchemes.get(self.openapi_security_scheme_name, None)  # type: ignore
        return f"{security.scheme} {encoded_token}" if isinstance(security, SecurityScheme) else encoded_token


class JWTCookieAuth(Generic[UserType], JWTAuth[UserType]):
    """JWT Cookie Authentication Configuration.

    This class is an alternate entry point to the library, and it includes all the functionality of the `JWTAuth` class
    and adds support for passing JWT tokens `HttpOnly` cookies.
    """

    key: str = "token"
    """Key for the cookie."""
    path: str = "/"
    """Path fragment that must exist in the request url for the cookie to be valid.

    Defaults to '/'.
    """
    domain: Optional[str] = None
    """Domain for which the cookie is valid."""
    secure: Optional[bool] = None
    """Https is required for the cookie."""
    samesite: Literal["lax", "strict", "none"] = "lax"
    """Controls whether or not a cookie is sent with cross-site requests.

    Defaults to 'lax'.
    """
    description: str = "JWT cookie-based authentication and authorization."
    """Description for the OpenAPI security scheme."""
    authentication_middleware_class: Type[JWTCookieAuthenticationMiddleware] = JWTCookieAuthenticationMiddleware
    """The authentication middleware class to use.

    Must inherit from [JWTCookieAuthenticationMiddleware][starlite.contrib.jwt.JWTCookieAuthenticationMiddleware]
    """

    @property
    def openapi_components(self) -> Components:
        """Create OpenAPI documentation for the JWT Cookie auth scheme.

        Returns:
            An [Components][pydantic_openapi_schema.v3_1_0.components.Components] instance.
        """
        return Components(
            securitySchemes={
                self.openapi_security_scheme_name: SecurityScheme(
                    type="http",
                    scheme="Bearer",
                    name=self.key,
                    security_scheme_in="cookie",
                    bearerFormat="JWT",
                    description=self.description,
                )
            }
        )

    @property
    def middleware(self) -> DefineMiddleware:
        """Create `JWTCookieAuthenticationMiddleware` wrapped in Starlite's `DefineMiddleware`.

        Returns:
            An instance of [DefineMiddleware][starlite.middleware.base.DefineMiddleware].
        """
        return DefineMiddleware(
            self.authentication_middleware_class,
            algorithm=self.algorithm,
            auth_cookie_key=self.key,
            auth_header=self.auth_header,
            exclude=self.exclude,
            exclude_opt_key=self.exclude_opt_key,
            retrieve_user_handler=self.retrieve_user_handler,
            scopes=self.scopes,
            token_secret=self.token_secret,
        )

    def login(
        self,
        identifier: str,
        *,
        response_body: Optional[Any] = None,
        response_media_type: Union[str, MediaType] = MediaType.JSON,
        response_status_code: int = HTTP_201_CREATED,
        token_expiration: Optional[timedelta] = None,
        token_issuer: Optional[str] = None,
        token_audience: Optional[str] = None,
        token_unique_jwt_id: Optional[str] = None,
    ) -> Response[Any]:
        """Create a response with a JWT header. Calls the 'JWTAuth.store_token_handler' to persist the token 'sub'.

        Args:
            identifier: Unique identifier of the token subject. Usually this is a user ID or equivalent kind of value.
            response_body: An optional response body to send.
            response_media_type: An optional 'Content-Type'. Defaults to 'application/json'.
            response_status_code: An optional status code for the response. Defaults to '201 Created'.
            token_expiration: An optional timedelta for the token expiration.
            token_issuer: An optional value of the token 'iss' field.
            token_audience: An optional value for the token 'aud' field.
            token_unique_jwt_id: An optional value for the token 'jti' field.

        Returns:
            A [Response][starlite.response.Response] instance.
        """
        encoded_token = self.create_token(
            identifier=identifier,
            token_expiration=token_expiration,
            token_issuer=token_issuer,
            token_audience=token_audience,
            token_unique_jwt_id=token_unique_jwt_id,
        )
        cookie = Cookie(
            key=self.key,
            path=self.path,
            httponly=True,
            value=self.format_auth_header(encoded_token),
            expires=int((datetime.now(timezone.utc) + (token_expiration or self.default_token_expiration)).timestamp()),
            secure=self.secure,
            samesite=self.samesite,
        )
        return Response(
            content=response_body,
            headers={self.auth_header: self.format_auth_header(encoded_token)},
            cookies=[cookie],
            media_type=response_media_type,
            status_code=response_status_code,
        )


class OAuth2PasswordBearerAuth(Generic[UserType], JWTCookieAuth[UserType]):
    """OAUTH2 Schema for Password Bearer Authentication.

    This class implements an OAUTH2 authentication flow entry point to the library, and it
    includes all the functionality of the `JWTAuth` class and adds
    support for passing JWT tokens `HttpOnly` cookies.

    `token_url` is the only additional argument that is required, and it should point at your login route
    """

    token_url: str
    """The URL for retrieving a new token."""
    oauth_scopes: Optional[Dict[str, str]] = None
    """Oauth Scopes available for the token."""
    description: str = "OAUTH2 password bearer authentication and authorization."
    """Description for the OpenAPI security scheme."""

    @property
    def oauth_flow(self) -> OAuthFlow:
        """Create an OpenAPI OAuth2 flow for the password bearer authentication scheme.

        Returns:
            An [OAuthFlow][pydantic_openapi_schema.v3_1_0.oauth_flow.OAuthFlow] instance.
        """
        return OAuthFlow(
            tokenUrl=self.token_url,
            scopes=self.oauth_scopes,
        )

    @property
    def openapi_components(self) -> Components:
        """Create OpenAPI documentation for the OAUTH2 Password bearer auth scheme.

        Returns:
            An [Components][pydantic_openapi_schema.v3_1_0.components.Components] instance.
        """
        return Components(
            securitySchemes={
                self.openapi_security_scheme_name: SecurityScheme(
                    type="oauth2",
                    scheme="Bearer",
                    name=self.auth_header,
                    security_scheme_in="header",
                    flows=OAuthFlows(password=self.oauth_flow),  # pyright: reportGeneralTypeIssues=false
                    bearerFormat="JWT",
                    description=self.description,
                )
            }
        )
