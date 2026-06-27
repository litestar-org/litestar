import dataclasses
from collections.abc import Sequence
from typing import Any

from litestar.security.jwt.token import JWTDecodeOptions, Token


@dataclasses.dataclass
class CustomToken(Token):
    @classmethod
    def decode_payload(
        cls,
        encoded_token: str,
        secret: str | bytes,
        algorithms: list[str],
        issuer: str | Sequence[str] | None = None,
        audience: str | Sequence[str] | None = None,
        options: JWTDecodeOptions | None = None,
    ) -> Any:
        payload = super().decode_payload(
            encoded_token=encoded_token,
            secret=secret,
            algorithms=algorithms,
            issuer=issuer,
            audience=audience,
            options=options,
        )
        payload["sub"] = payload["sub"].split("@", maxsplit=1)[1]
        return payload
