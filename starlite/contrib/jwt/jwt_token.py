from datetime import datetime, timezone
from typing import Dict, Optional, Union, cast

from jose import JWSError, JWTError, jwt
from pydantic import (
    BaseConfig,
    BaseModel,
    Extra,
    Field,
    ValidationError,
    constr,
    validator,
)

from starlite import ImproperlyConfiguredException
from starlite.exceptions import NotAuthorizedException


def _normalize_datetime(value: datetime) -> datetime:
    """Convert the given value into UTC and strip microseconds.

    Args:
        value: A datetime instance

    Returns:
        A datetime instance
    """
    if value.tzinfo is not None:
        value.astimezone(timezone.utc)
    return value.replace(microsecond=0)


class Token(BaseModel):
    """JWT Token DTO."""

    class Config(BaseConfig):
        extra = Extra.allow

    exp: datetime
    """Expiration - datetime for token expiration."""
    iat: datetime = Field(default_factory=lambda: _normalize_datetime(datetime.now(timezone.utc)))
    """Issued at - should always be current now."""
    sub: constr(min_length=1)  # type: ignore[valid-type]
    """Subject - usually a unique identifier of the user or equivalent entity."""
    iss: Optional[str] = None
    """Issuer - optional unique identifier for the issuer."""
    aud: Optional[str] = None
    """Audience - intended audience."""
    jti: Optional[str] = None
    """JWT ID - a unique identifier of the JWT between different issuers."""

    @validator("exp", always=True)
    def validate_exp(cls, value: datetime) -> datetime:  # pylint: disable=no-self-argument
        """Ensure that 'exp' value is a future datetime.

        Args:
            value: A datetime instance.

        Raises:
            ValueError: if value is not a future datetime instance.

        Returns:
            The validated datetime.
        """

        value = _normalize_datetime(value)
        if value.timestamp() >= _normalize_datetime(datetime.now(timezone.utc)).timestamp():
            return value
        raise ValueError("exp value must be a datetime in the future")

    @validator("iat", always=True)
    def validate_iat(cls, value: datetime) -> datetime:  # pylint: disable=no-self-argument
        """Ensure that 'iat' value is a past or current datetime.

        Args:
            value: A datetime instance.

        Raises:
            ValueError: if value is not a past or current datetime instance.

        Returns:
            The validated datetime.
        """
        value = _normalize_datetime(value)
        if value.timestamp() <= _normalize_datetime(datetime.now(timezone.utc)).timestamp():
            return value
        raise ValueError("iat must be a current or past time")

    @staticmethod
    def decode(encoded_token: str, secret: Union[str, Dict[str, str]], algorithm: str) -> "Token":
        """Decode a passed in token string and returns a Token instance.

        Args:
            encoded_token: A base64 string containing an encoded JWT.
            secret: The secret with which the JWT is encoded. It may optionally be an individual JWK or JWS set dict
            algorithm: The algorithm used to encode the JWT.

        Returns:
            A decoded Token instance.

        Raises:
            [NotAuthorizedException][starlite.exceptions.NotAuthorizedException]: If token is invalid.
        """
        try:
            payload = jwt.decode(token=encoded_token, key=secret, algorithms=[algorithm], options={"verify_aud": False})
            return Token(**payload)
        except (JWTError, ValidationError) as e:
            raise NotAuthorizedException("Invalid token") from e

    def encode(self, secret: str, algorithm: str) -> str:
        """Encode the token instance into a string.

        Args:
            secret: The secret with which the JWT is encoded.
            algorithm: The algorithm used to encode the JWT.

        Returns:
            An encoded token string.

        Raises:
            [ImproperlyConfiguredException][starlite.exceptions.ImproperlyConfiguredException]: If encoding fails.
        """
        try:
            return cast("str", jwt.encode(claims=self.dict(exclude_none=True), key=secret, algorithm=algorithm))
        except (JWTError, JWSError) as e:
            raise ImproperlyConfiguredException("Failed to encode token") from e
