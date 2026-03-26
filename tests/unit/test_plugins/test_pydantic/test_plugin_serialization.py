from __future__ import annotations

import datetime
import json
from decimal import Decimal
from functools import partial
from pathlib import Path
from typing import Any

import pydantic as pydantic_v2
import pytest
from pydantic_extra_types.color import Color as ColorV2

from litestar.exceptions import SerializationException
from litestar.plugins.pydantic import PydanticInitPlugin, _model_dump, _model_dump_json
from litestar.serialization import (
    decode_json,
    decode_msgpack,
    default_serializer,
    encode_json,
    encode_msgpack,
    get_serializer,
)

from . import PydanticVersion

TODAY = datetime.date.today()
YESTERDAY_DATE = TODAY - datetime.timedelta(days=1)
FUTURE_DATE = TODAY + datetime.timedelta(days=1)
YESTERDAY_DATETIME = datetime.datetime(2023, 6, 14, 12, 0, 0)
FUTURE_DATETIME = datetime.datetime(2030, 6, 16, 12, 0, 0)
AWARE_DATETIME = datetime.datetime(2023, 6, 15, 12, 0, 0, tzinfo=datetime.UTC)
NAIVE_DATETIME = datetime.datetime(2023, 6, 15, 12, 0, 0).replace(tzinfo=None)


class CustomStr(str):
    pass


class CustomInt(int):
    pass


class CustomFloat(float):
    pass


class CustomList(list):
    pass


class CustomSet(set):
    pass


class CustomFrozenSet(frozenset):
    pass


class CustomTuple(tuple):
    pass


class ModelV2(pydantic_v2.BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    conset: pydantic_v2.conset(int, min_length=1)  # type: ignore[valid-type]
    confrozenset: pydantic_v2.confrozenset(int, min_length=1)  # type: ignore[valid-type]
    conlist: pydantic_v2.conlist(int, min_length=1)  # type: ignore[valid-type]

    path: Path

    email_str: pydantic_v2.EmailStr
    name_email: pydantic_v2.NameEmail
    color: ColorV2
    bytesize: pydantic_v2.ByteSize
    secret_str: pydantic_v2.SecretStr
    secret_bytes: pydantic_v2.SecretBytes
    payment_card_number: pydantic_v2.PaymentCardNumber

    constr: pydantic_v2.constr(min_length=1)  # type: ignore[valid-type]
    conbytes: pydantic_v2.conbytes(min_length=1)  # type: ignore[valid-type]
    condate: pydantic_v2.condate(ge=TODAY)  # type: ignore[valid-type]
    condecimal: pydantic_v2.condecimal(ge=Decimal("1"))  # type: ignore[valid-type]
    confloat: pydantic_v2.confloat(ge=0)  # type: ignore[valid-type]

    conint: pydantic_v2.conint(ge=0)  # type: ignore[valid-type]

    url: pydantic_v2.AnyUrl
    http_url: pydantic_v2.HttpUrl

    paste_date: pydantic_v2.PastDate
    future_date: pydantic_v2.FutureDate
    paste_datetime: pydantic_v2.PastDatetime
    future_datetime: pydantic_v2.FutureDatetime
    aware_datetime: pydantic_v2.AwareDatetime
    naive_datetime: pydantic_v2.NaiveDatetime


serializer = partial(default_serializer, type_encoders=PydanticInitPlugin.encoders())


@pytest.fixture()
def model_type(pydantic_version: PydanticVersion) -> type[ModelV2]:
    return ModelV2


@pytest.fixture()
def model(pydantic_version: PydanticVersion) -> ModelV2:
    return ModelV2(
        path=Path("example"),
        email_str=pydantic_v2.parse_obj_as(pydantic_v2.EmailStr, "info@example.org"),  # pyright: ignore[reportArgumentType]
        name_email=pydantic_v2.NameEmail("info", "info@example.org"),
        color=ColorV2("rgb(255, 255, 255)"),
        bytesize=pydantic_v2.ByteSize(100),
        secret_str=pydantic_v2.SecretStr("hello"),
        secret_bytes=pydantic_v2.SecretBytes(b"hello"),
        payment_card_number=pydantic_v2.PaymentCardNumber("4000000000000002"),
        constr="hello",
        conbytes=b"hello",
        condate=TODAY,
        condecimal=Decimal("3.14"),
        confloat=1.0,
        conset={1},
        confrozenset=frozenset([1]),
        conint=1,
        conlist=[1],
        url="some://example.org/",  # type: ignore[arg-type]
        http_url="http://example.org/",  # type: ignore[arg-type]
        paste_date=YESTERDAY_DATE,
        future_date=FUTURE_DATE,
        paste_datetime=YESTERDAY_DATETIME,
        future_datetime=FUTURE_DATETIME,
        aware_datetime=AWARE_DATETIME,
        naive_datetime=NAIVE_DATETIME,
    )


@pytest.mark.parametrize(
    "attribute_name, expected",
    [
        ("path", "example"),
        ("email_str", "info@example.org"),
        ("name_email", "info <info@example.org>"),
        ("color", "white"),
        ("bytesize", 100),
        ("secret_str", "**********"),
        ("secret_bytes", "**********"),
        ("payment_card_number", "4000000000000002"),
        ("constr", "hello"),
        ("conbytes", b"hello"),
        ("condate", TODAY.isoformat()),
        ("condecimal", 3.14),
        ("conset", {1}),
        ("confrozenset", frozenset([1])),
        ("conint", 1),
        ("url", "some://example.org/"),
        ("http_url", "http://example.org/"),
        ("paste_date", YESTERDAY_DATE.isoformat()),
        ("future_date", FUTURE_DATE.isoformat()),
        ("paste_datetime", YESTERDAY_DATETIME.isoformat()),
        ("future_datetime", FUTURE_DATETIME.isoformat()),
        ("aware_datetime", AWARE_DATETIME.isoformat()),
        ("naive_datetime", NAIVE_DATETIME.isoformat()),
    ],
)
def test_default_serializer(model: ModelV2, attribute_name: str, expected: Any) -> None:
    assert serializer(getattr(model, attribute_name)) == expected


def test_serialization_of_model_instance(model: ModelV2) -> None:
    assert serializer(getattr(model, "conbytes")) == b"hello"
    assert serializer(model) == _model_dump(model)


@pytest.mark.parametrize("prefer_alias", [False, True])
def test_pydantic_json_compatibility(model: ModelV2, prefer_alias: bool, pydantic_version: PydanticVersion) -> None:
    raw = _model_dump_json(model, by_alias=prefer_alias)
    encoded_json = encode_json(model, serializer=get_serializer(PydanticInitPlugin.encoders(prefer_alias=prefer_alias)))

    raw_result = json.loads(raw)
    encoded_result = json.loads(encoded_json)

    assert raw_result == encoded_result


@pytest.mark.parametrize("encoder", [encode_json, encode_msgpack])
def test_encoder_raises_serialization_exception(model: ModelV2, encoder: Any) -> None:
    with pytest.raises(SerializationException):
        encoder(object())


@pytest.mark.parametrize("decoder", [decode_json, decode_msgpack])
def test_decode_json_raises_serialization_exception(model: ModelV2, decoder: Any) -> None:
    with pytest.raises(SerializationException):
        decoder(b"str")


@pytest.mark.parametrize("prefer_alias", [False, True])
def test_decode_json_typed(model: ModelV2, prefer_alias: bool, model_type: type[ModelV2]) -> None:
    dumped_model = _model_dump_json(model, by_alias=prefer_alias)
    decoded_model = decode_json(value=dumped_model, target_type=model_type, type_decoders=PydanticInitPlugin.decoders())
    assert _model_dump_json(decoded_model, by_alias=prefer_alias) == dumped_model


@pytest.mark.parametrize("prefer_alias", [False, True])
def test_decode_msgpack_typed(model: ModelV2, model_type: type[ModelV2], prefer_alias: bool) -> None:
    model_json = _model_dump_json(model, by_alias=prefer_alias)
    assert (
        decode_msgpack(
            encode_msgpack(model, serializer=get_serializer(PydanticInitPlugin.encoders(prefer_alias=prefer_alias))),
            model_type,
            type_decoders=PydanticInitPlugin.decoders(),
        ).json()
        == model_json
    )
