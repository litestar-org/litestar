import dataclasses
from typing import Any, List, Optional, Sequence, Union

from litestar.security.jwt.token import JWTDecodeOptions, Token


@dataclasses.dataclass
class CustomToken(Token):
    @classmethod
    def decode_payload(
        cls,
        encoded_token: str,
        secret: str,
        algorithms: List[str],
        issuer: Optional[List[str]] = None,
        audience: Union[str, Sequence[str], None] = None,
        options: Optional[JWTDecodeOptions] = None,
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
