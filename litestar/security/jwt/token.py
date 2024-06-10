from __future__ import annotations

import base64
import dataclasses
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec, ed448, ed25519, rsa
from jwt import InvalidTokenError, PyJWTError

from litestar.exceptions import ImproperlyConfiguredException, NotAuthorizedException

if TYPE_CHECKING:
    from jwt.algorithms import AllowedPublicKeys
    from typing_extensions import Self


__all__ = ("Token",)


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


@dataclass
class Token:
    """JWT Token DTO."""

    exp: datetime
    """Expiration - datetime for token expiration."""
    sub: str
    """Subject - usually a unique identifier of the user or equivalent entity."""
    iat: datetime = field(default_factory=lambda: _normalize_datetime(datetime.now(timezone.utc)))
    """Issued at - should always be current now."""
    iss: str | None = field(default=None)
    """Issuer - optional unique identifier for the issuer."""
    aud: str | None = field(default=None)
    """Audience - intended audience."""
    jti: str | None = field(default=None)
    """JWT ID - a unique identifier of the JWT between different issuers."""
    extras: dict[str, Any] = field(default_factory=dict)
    """Extra fields that were found on the JWT token."""

    def __post_init__(self) -> None:
        if len(self.sub) < 1:
            raise ImproperlyConfiguredException("sub must be a string with a length greater than 0")

        if isinstance(self.exp, datetime) and (
            (exp := _normalize_datetime(self.exp)).timestamp()
            >= _normalize_datetime(datetime.now(timezone.utc)).timestamp()
        ):
            self.exp = exp
        else:
            raise ImproperlyConfiguredException("exp value must be a datetime in the future")

        if isinstance(self.iat, datetime) and (
            (iat := _normalize_datetime(self.iat)).timestamp()
            <= _normalize_datetime(datetime.now(timezone.utc)).timestamp()
        ):
            self.iat = iat
        else:
            raise ImproperlyConfiguredException("iat must be a current or past time")

    @classmethod
    def decode(cls, encoded_token: str, secret: str | dict[str, str], algorithm: str) -> Self:
        """Decode a passed in token string and returns a Token instance.

        Args:
            encoded_token: A base64 string containing an encoded JWT.
            secret: The secret with which the JWT is encoded. It may optionally be an individual JWK or JWS set dict
            algorithm: The algorithm used to encode the JWT.

        Returns:
            A decoded Token instance.

        Raises:
            NotAuthorizedException: If the token is invalid.
        """

        def base64url_decode(code: str) -> bytes:
            padding = "=" * (4 - (len(code) % 4))
            return base64.urlsafe_b64decode(code + padding)

        if isinstance(secret, str):
            converted_secret: AllowedPublicKeys | str | bytes = secret
        else:
            if secret["kty"] == "RSA":
                n = int.from_bytes(base64url_decode(secret["n"]), byteorder="big")
                e = int.from_bytes(base64url_decode(secret["e"]), byteorder="big")
                converted_secret = rsa.RSAPublicNumbers(e, n).public_key(default_backend())
            elif secret["kty"] == "EC":
                x = int.from_bytes(base64url_decode(secret["x"]), byteorder="big")
                y = int.from_bytes(base64url_decode(secret["y"]), byteorder="big")
                converted_secret = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key(default_backend())
            elif secret["kty"] == "OKP" and secret["crv"] == "Ed25519":
                x = base64url_decode(secret["x"])
                converted_secret = ed25519.Ed25519PublicKey.from_public_bytes(x)
            elif secret["kty"] == "OKP" and secret["crv"] == "Ed448":
                x = base64url_decode(secret["x"])
                converted_secret = ed448.Ed448PublicKey.from_public_bytes(x)
            else:
                raise TypeError("The secret is not a form of allowed public key.")

        try:
            payload = jwt.decode(
                jwt=encoded_token, key=converted_secret, algorithms=[algorithm], options={"verify_aud": False}
            )
            exp = datetime.fromtimestamp(payload.pop("exp"), tz=timezone.utc)
            iat = datetime.fromtimestamp(payload.pop("iat"), tz=timezone.utc)
            field_names = {f.name for f in dataclasses.fields(Token)}
            extra_fields = payload.keys() - field_names
            extras = payload.pop("extras", {})
            for key in extra_fields:
                extras[key] = payload.pop(key)
            return cls(exp=exp, iat=iat, **payload, extras=extras)
        except (KeyError, PyJWTError, ImproperlyConfiguredException) as e:
            raise NotAuthorizedException("Invalid token") from e

    def encode(self, secret: str, algorithm: str) -> str:
        """Encode the token instance into a string.

        Args:
            secret: The secret with which the JWT is encoded.
            algorithm: The algorithm used to encode the JWT.

        Returns:
            An encoded token string.

        Raises:
            ImproperlyConfiguredException: If encoding fails.
        """
        try:
            return jwt.encode(
                payload={k: v for k, v in asdict(self).items() if v is not None}, key=secret, algorithm=algorithm
            )
        except (PyJWTError, InvalidTokenError) as e:
            raise ImproperlyConfiguredException("Failed to encode token") from e
