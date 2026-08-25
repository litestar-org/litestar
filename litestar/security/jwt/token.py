from __future__ import annotations

import dataclasses
from collections.abc import Sequence  # noqa: TC003
from dataclasses import InitVar, asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, TypedDict

import jwt

from litestar.exceptions import ImproperlyConfiguredException, NotAuthorizedException

if TYPE_CHECKING:
    from typing import Self

__all__ = (
    "JWTDecodeOptions",
    "Token",
)


def _normalize_datetime(value: datetime) -> datetime:
    """Convert the given value into UTC and strip microseconds.

    Args:
        value: A datetime instance

    Returns:
        A datetime instance
    """
    if value.tzinfo is not None:
        value = value.astimezone(UTC)

    return value.replace(microsecond=0)


class JWTDecodeOptions(TypedDict, total=False):
    """``options`` for PyJWTs :func:`jwt.decode`"""

    verify_aud: bool
    verify_iss: bool
    verify_exp: bool
    verify_nbf: bool
    strict_aud: bool
    require: list[str]


@dataclass
class Token:
    """JWT Token DTO."""

    exp: datetime
    """Expiration - datetime for token expiration."""
    sub: str
    """Subject - usually a unique identifier of the user or equivalent entity."""
    iat: datetime = field(default_factory=lambda: _normalize_datetime(datetime.now(UTC)))
    """Issued at - should always be current now."""
    iss: str | None = field(default=None)
    """Issuer - optional unique identifier for the issuer."""
    aud: str | Sequence[str] | None = field(default=None)
    """Audience - intended audience(s)."""
    jti: str | None = field(default=None)
    """JWT ID - a unique identifier of the JWT between different issuers."""
    extras: dict[str, Any] = field(default_factory=dict)
    """Extra fields that were found on the JWT token."""

    leeway: InitVar[float] = 0
    """Leeway in seconds for validating the ``exp`` claim during construction.

    This is an :class:`~dataclasses.InitVar` -- it is used during ``__post_init__``
    validation but is **not** stored as an instance attribute.
    """

    def __post_init__(self, leeway: float) -> None:
        if len(self.sub) < 1:
            raise ImproperlyConfiguredException("sub must be a string with a length greater than 0")

        if (
            isinstance(self.exp, datetime)
            and ((exp := _normalize_datetime(self.exp)) + timedelta(seconds=leeway)).timestamp()
            >= _normalize_datetime(datetime.now(UTC)).timestamp()
        ):
            self.exp = exp
        else:
            raise ImproperlyConfiguredException(f"exp value must be a datetime in the future (leeway={leeway}s)")

        if isinstance(self.iat, datetime) and (
            (iat := _normalize_datetime(self.iat)).timestamp() <= _normalize_datetime(datetime.now(UTC)).timestamp()
        ):
            self.iat = iat
        else:
            raise ImproperlyConfiguredException("iat must be a current or past time")

    @classmethod
    def decode_payload(
        cls,
        encoded_token: str,
        secret: str | bytes,
        algorithms: list[str],
        issuer: str | Sequence[str] | None = None,
        audience: str | Sequence[str] | None = None,
        options: JWTDecodeOptions | None = None,
        leeway: float | timedelta = 0,
    ) -> Any:
        """Decode and verify the JWT and return its payload.

        Args:
            encoded_token: A base64 string containing an encoded JWT.
            secret: The secret with which the JWT is encoded.
            algorithms: A list of algorithms used to decode the JWT.
            issuer: Verify the issuer when decoding the token.
            audience: Verify the audience when decoding the token.
            options: Options for PyJWT's ``jwt.decode``.
            leeway: A time margin in seconds (or as a :class:`timedelta`) to account for
                clock skew when verifying the ``exp`` and ``nbf`` claims. Defaults to ``0``.

        Returns:
            The decoded JWT payload.
        """
        return jwt.decode(
            jwt=encoded_token,
            key=secret,
            algorithms=algorithms,
            issuer=issuer,
            audience=audience,
            options=options,  # type: ignore[arg-type]
            leeway=leeway,
        )

    @classmethod
    def _build_decode_options(
        cls,
        audience: str | Sequence[str] | None,
        issuer: str | Sequence[str] | None,
        require_claims: Sequence[str] | None,
        verify_exp: bool,
        verify_nbf: bool,
        strict_audience: bool,
    ) -> tuple[JWTDecodeOptions, str | Sequence[str] | None]:
        """Build JWT decode options and resolve the audience value.

        Returns:
            A tuple of (options, resolved_audience).
        """
        options: JWTDecodeOptions = {
            "verify_aud": bool(audience),
            "verify_iss": bool(issuer),
        }
        if require_claims:
            options["require"] = list(require_claims)
        if verify_exp is False:
            options["verify_exp"] = False
        if verify_nbf is False:
            options["verify_nbf"] = False
        if strict_audience:
            if audience is None or (not isinstance(audience, str) and len(audience) != 1):
                raise ValueError("When using 'strict_audience=True', 'audience' must be a sequence of length 1")
            options["strict_aud"] = True
            # although not documented, pyjwt requires audience to be a string if
            # using the strict_aud option
            if not isinstance(audience, str):
                audience = audience[0]
        return options, audience

    @classmethod
    def decode(
        cls,
        encoded_token: str,
        secret: str | bytes,
        algorithm: str,
        audience: str | Sequence[str] | None = None,
        issuer: str | Sequence[str] | None = None,
        require_claims: Sequence[str] | None = None,
        verify_exp: bool = True,
        verify_nbf: bool = True,
        strict_audience: bool = False,
        leeway: float | timedelta = 0,
    ) -> Self:
        """Decode a passed in token string and return a Token instance.

        Args:
            encoded_token: A base64 string containing an encoded JWT.
            secret: The secret with which the JWT is encoded.
            algorithm: The algorithm used to encode the JWT.
            audience: Verify the audience when decoding the token. If the audience in
                the token does not match any audience given, raise a
                :exc:`NotAuthorizedException`
            issuer: Verify the issuer when decoding the token. If the issuer in the
                token does not match any issuer given, raise a
                :exc:`NotAuthorizedException`
            require_claims: Verify that the given claims are present in the token
            verify_exp: Verify that the value of the ``exp`` (*expiration*) claim is in
                the future
            verify_nbf: Verify that the value of the ``nbf`` (*not before*) claim is in
                the past
            strict_audience: Verify that the value of the ``aud`` (*audience*) claim is
                a single value, and not a list of values, and matches ``audience``
                exactly. Requires the value passed to the ``audience`` to be a sequence
                of length 1
            leeway: A time margin in seconds (or as a :class:`timedelta`) to account for
                clock skew when verifying the ``exp`` (*expiration*) and ``nbf``
                (*not before*) claims. Defaults to ``0``.

        Returns:
            A decoded Token instance.

        Raises:
            NotAuthorizedException: If the token is invalid.
        """
        options, audience = cls._build_decode_options(
            audience=audience,
            issuer=issuer,
            require_claims=require_claims,
            verify_exp=verify_exp,
            verify_nbf=verify_nbf,
            strict_audience=strict_audience,
        )

        try:
            payload = cls.decode_payload(
                encoded_token=encoded_token,
                secret=secret,
                algorithms=[algorithm],
                audience=audience,
                issuer=issuer,
                options=options,
                leeway=leeway,
            )
            payload["exp"] = cls._decode_datetime_claim(payload, "exp")
            payload["iat"] = cls._decode_datetime_claim(payload, "iat")
            cls._require_claim(payload, "sub")
            extra_fields = payload.keys() - {f.name for f in dataclasses.fields(cls)}
            extras = payload.setdefault("extras", {})
            for key in extra_fields:
                extras[key] = payload.pop(key)
            leeway_seconds = leeway.total_seconds() if isinstance(leeway, timedelta) else float(leeway)
            return cls(**payload, leeway=leeway_seconds)
        except (
            KeyError,
            jwt.exceptions.InvalidTokenError,
            ImproperlyConfiguredException,
        ) as e:
            raise NotAuthorizedException("Invalid token") from e

    @classmethod
    def _require_claim(cls, payload: dict[str, Any], claim: str) -> Any:
        try:
            return payload[claim]
        except KeyError as e:
            raise NotAuthorizedException("Invalid token") from e

    @classmethod
    def _decode_datetime_claim(cls, payload: dict[str, Any], claim: str) -> datetime:
        claim_value = cls._require_claim(payload, claim)
        try:
            return datetime.fromtimestamp(claim_value, tz=UTC)
        except (OSError, OverflowError, TypeError, ValueError):
            raise NotAuthorizedException("Invalid token") from None

    def encode(
        self,
        secret: str | bytes,
        algorithm: str,
        headers: dict[str, Any] | None = None,
    ) -> str:
        """Encode the token instance into a string.

        Args:
            secret: The secret with which the JWT is encoded.
            algorithm: The algorithm used to encode the JWT.
            headers: Optional headers to include in the JWT (e.g., {"kid": "..."}).

        Returns:
            An encoded token string.

        Raises:
            ImproperlyConfiguredException: If encoding fails.
        """
        try:
            return jwt.encode(
                payload={k: v for k, v in asdict(self).items() if v is not None},
                key=secret,
                algorithm=algorithm,
                headers=headers,
            )
        except (jwt.DecodeError, NotImplementedError) as e:
            raise ImproperlyConfiguredException("Failed to encode token") from e
