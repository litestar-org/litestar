import string
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis.strategies import datetimes, none, one_of, sampled_from, text

from starlite.contrib.jwt import Token
from starlite.exceptions import ImproperlyConfiguredException, NotAuthorizedException


@given(
    algorithm=sampled_from(
        [
            "HS256",
            "HS384",
            "HS512",
        ]
    ),
    token_sub=text(min_size=1),
    token_secret=text(min_size=10),
    token_issuer=one_of(none(), text(max_size=256)),
    token_audience=one_of(none(), text(max_size=256, alphabet=string.ascii_letters)),
    token_unique_jwt_id=one_of(none(), text(max_size=256)),
)
def test_token(
    algorithm: str,
    token_sub: str,
    token_secret: str,
    token_issuer: Optional[str],
    token_audience: Optional[str],
    token_unique_jwt_id: Optional[str],
) -> None:
    token = Token(
        sub=token_sub,
        exp=(datetime.now(timezone.utc) + timedelta(minutes=30)),
        aud=token_audience,
        iss=token_issuer,
        jti=token_unique_jwt_id,
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


@given(exp=datetimes(max_value=datetime.now() - timedelta(seconds=1)))
def test_exp_validation(exp: datetime) -> None:
    if sys.platform == "win32" and exp == datetime(1970, 1, 1, 0, 0):
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
