import string
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis.strategies import datetimes, none, one_of, sampled_from, text

from starlite import ImproperlyConfiguredException, NotAuthorizedException
from starlite.contrib.jwt import Token


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
        exp=(datetime.now(timezone.utc) + timedelta(seconds=30)),
        aud=token_audience,
        iss=token_issuer,
        jti=token_unique_jwt_id,
    )
    encoded_token = token.encode(secret=token_secret, algorithm=algorithm)
    decoded_token = token.decode(encoded_token=encoded_token, secret=token_secret, algorithm=algorithm)
    assert token.dict() == decoded_token.dict()


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
    with pytest.raises(ValueError):
        Token(
            sub="123",
            exp=exp,
            iat=(datetime.now() - timedelta(seconds=30)),
        )


@given(iat=datetimes(min_value=datetime.now() + timedelta(days=1)))
def test_iat_validation(iat: datetime) -> None:
    with pytest.raises(ValueError):
        Token(
            sub="123",
            iat=iat,
            exp=(iat + timedelta(seconds=120)),
        )
