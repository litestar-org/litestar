import secrets
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis.strategies import datetimes
from jose import jwt

from litestar.exceptions import ImproperlyConfiguredException, NotAuthorizedException
from litestar.security.jwt import Token


@pytest.mark.parametrize("algorithm", ["HS256", "HS384", "HS512"])
@pytest.mark.parametrize("token_issuer", [None, "e3d7d10edbbc28bfebd8861d39ae7587acde1e1fcefe2cbbec686d235d68f475"])
@pytest.mark.parametrize("token_audience", [None, "627224198b4245ed91cf8353e4ccdf1650728c7ee92748f55fe1e9a9c4d961df"])
@pytest.mark.parametrize(
    "token_unique_jwt_id", [None, "10f5c6967783ddd6bb0c4e8262d7097caeae64705e45f83275e3c32eee5d30f2"]
)
@pytest.mark.parametrize("token_extras", [None, {"email": "test@test.com"}])
def test_token(
    algorithm: str,
    token_issuer: Optional[str],
    token_audience: Optional[str],
    token_unique_jwt_id: Optional[str],
    token_extras: Optional[Dict[str, Any]],
) -> None:
    token_secret = secrets.token_hex()
    token = Token(
        sub=secrets.token_hex(),
        exp=(datetime.now(timezone.utc) + timedelta(minutes=30)),
        aud=token_audience,
        iss=token_issuer,
        jti=token_unique_jwt_id,
        extras=token_extras or {},
    )
    encoded_token = token.encode(secret=token_secret, algorithm=algorithm)
    decoded_token = token.decode(encoded_token=encoded_token, secret=token_secret, algorithm=algorithm)
    assert asdict(token) == asdict(decoded_token)


@pytest.mark.parametrize(
    "algorithm, secret",
    [
        (
            "nope",
            "1",
        ),
        (
            "HS256",
            "",
        ),
        (
            None,
            None,
        ),
        (
            "HS256",
            None,
        ),
        (
            "",
            None,
        ),
        (
            "",
            "",
        ),
        (
            "",
            "1",
        ),
    ],
)
def test_encode_validation(algorithm: str, secret: str) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        Token(
            sub="123",
            exp=(datetime.now(timezone.utc) + timedelta(seconds=30)),
        ).encode(algorithm="nope", secret=secret)


def test_decode_validation() -> None:
    token = Token(
        sub="123",
        exp=(datetime.now(timezone.utc) + timedelta(seconds=30)),
    )
    algorithm = "HS256"
    secret = uuid4().hex
    encoded_token = token.encode(algorithm=algorithm, secret=secret)

    token.decode(encoded_token=encoded_token, algorithm=algorithm, secret=secret)

    with pytest.raises(NotAuthorizedException):
        token.decode(encoded_token=secret, algorithm=algorithm, secret=secret)

    with pytest.raises(NotAuthorizedException):
        token.decode(encoded_token=encoded_token, algorithm="nope", secret=secret)

    with pytest.raises(NotAuthorizedException):
        token.decode(encoded_token=encoded_token, algorithm=algorithm, secret=uuid4().hex)


@given(exp=datetimes(min_value=datetime(1970, 1, 1), max_value=datetime.now() - timedelta(seconds=1)))
def test_exp_validation(exp: datetime) -> None:
    if sys.platform == "win32" and exp == datetime(1970, 1, 1):
        # this does not work on windows. see https://bugs.python.org/issue29097
        pytest.skip("Skipping because .timestamp is weird on windows sometimes")

    with pytest.raises(ImproperlyConfiguredException):
        Token(
            sub="123",
            exp=exp,
            iat=(datetime.now() - timedelta(seconds=30)),
        )


@given(iat=datetimes(min_value=datetime.now() + timedelta(days=1)))
def test_iat_validation(iat: datetime) -> None:
    if sys.platform == "win32" and iat >= datetime(3000, 1, 1, 0, 0):
        # this does not work on windows. see https://bugs.python.org/issue29097
        pytest.skip("Skipping because .timestamp is weird on windows sometimes")

    with pytest.raises(ImproperlyConfiguredException):
        Token(
            sub="123",
            iat=iat,
            exp=(iat + timedelta(seconds=120)),
        )


def test_sub_validation() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        Token(
            sub="",
            iat=(datetime.now() - timedelta(seconds=30)),
            exp=(datetime.now() + timedelta(seconds=120)),
        )


def test_extra_fields() -> None:
    raw_token = {
        "sub": secrets.token_hex(),
        "iat": datetime.now(timezone.utc),
        "azp": "extra value",
        "email": "thetest@test.com",
        "exp": (datetime.now(timezone.utc) + timedelta(seconds=30)),
    }
    token_secret = secrets.token_hex()
    encoded_token = jwt.encode(claims=raw_token, key=token_secret, algorithm="HS256")
    token = Token.decode(encoded_token=encoded_token, secret=token_secret, algorithm="HS256")
    assert "azp" in token.extras
    assert "email" in token.extras

    raw_token = {
        "sub": secrets.token_hex(),
        "iat": datetime.now(timezone.utc),
        "exp": (datetime.now(timezone.utc) + timedelta(seconds=30)),
    }
    token_secret = secrets.token_hex()
    encoded_token = jwt.encode(claims=raw_token, key=token_secret, algorithm="HS256")
    token = Token.decode(encoded_token=encoded_token, secret=token_secret, algorithm="HS256")
    assert token.extras == {}
