import json
from pathlib import PosixPath
from typing import Any

import pydantic
import pytest
from pydantic import (
    BaseModel,
    ByteSize,
    ConstrainedBytes,
    ConstrainedDate,
    ConstrainedDecimal,
    ConstrainedFloat,
    ConstrainedFrozenSet,
    ConstrainedInt,
    ConstrainedList,
    ConstrainedSet,
    ConstrainedStr,
    EmailStr,
    NameEmail,
    PaymentCardNumber,
    SecretBytes,
    SecretStr,
    StrictBool,
    StrictBytes,
    StrictFloat,
    StrictInt,
    StrictStr,
)
from pydantic.color import Color

from starlite.utils.serialization import default_serializer, encode_json
from tests import PersonFactory

person = PersonFactory.build()


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


class Model(BaseModel):
    path: PosixPath = PosixPath("example")

    email_str: pydantic.EmailStr = EmailStr("info@example.org")
    name_email: NameEmail = NameEmail("info", "info@example.org")
    color: Color = Color("rgb(255, 255, 255)")
    bytesize: ByteSize = ByteSize.validate("100b")
    secret_str: SecretStr = SecretStr("hello")
    secret_bytes: SecretBytes = SecretBytes(b"hello")
    payment_card_number: PaymentCardNumber = PaymentCardNumber("4000000000000002")

    constr: pydantic.constr() = ConstrainedStr("hello")  # type: ignore[valid-type]
    conbytes: pydantic.conbytes() = ConstrainedBytes(b"hello")  # type: ignore[valid-type]
    condate: pydantic.condate() = ConstrainedDate.today()  # type: ignore[valid-type]
    condecimal: pydantic.condecimal() = ConstrainedDecimal(3.14)  # type: ignore[valid-type]
    confloat: pydantic.confloat() = ConstrainedFloat(1.0)  # type: ignore[valid-type]
    conset: pydantic.conset(int) = ConstrainedSet([1])  # type: ignore[valid-type]
    confrozenset: pydantic.confrozenset(int) = ConstrainedFrozenSet([1])  # type: ignore[valid-type]
    conint: pydantic.conint() = ConstrainedInt(1)  # type: ignore[valid-type]
    conlist: pydantic.conlist(str) = ConstrainedList([1])  # type: ignore[valid-type]

    strict_str: StrictStr = StrictStr("hello")
    strict_int: StrictInt = StrictInt(1)
    strict_float: StrictFloat = StrictFloat(1.0)
    strict_bytes: StrictBytes = StrictBytes(b"hello")
    strict_bool: StrictBool = StrictBool(True)

    custom_str: CustomStr = CustomStr()
    custom_int: CustomInt = CustomInt()
    custom_float: CustomFloat = CustomFloat()
    custom_list: CustomList = CustomList()
    custom_set: CustomSet = CustomSet()
    custom_frozenset: CustomFrozenSet = CustomFrozenSet()
    custom_tuple: CustomTuple = CustomTuple()


model = Model()


@pytest.mark.parametrize(
    "value, expected",
    [
        (model.email_str, "info@example.org"),
        (model.name_email, "info <info@example.org>"),
        (model.color, "white"),
        (model.bytesize, 100),
        (model.secret_str, "**********"),
        (model.secret_bytes, "**********"),
        (model.payment_card_number, "4000000000000002"),
        (model.constr, "hello"),
        (model.conbytes, "hello"),
        (model.condate, model.condate.isoformat()),
        (model.condecimal, 3.14),
        (model.conset, {1}),
        (model.confrozenset, frozenset([1])),
        (model.conint, 1),
        # (model.conlist, [1]),
        (model.strict_str, "hello"),
        (model.strict_int, 1),
        (model.strict_float, 1.0),
        (model.strict_bytes, "hello"),
        (model.strict_bool, 1),
        (model, model.dict()),
        (model.custom_str, ""),
        (model.custom_int, 0),
        (model.custom_float, 0.0),
        # (model.custom_list, []),
        (model.custom_set, set()),
        (model.custom_frozenset, frozenset()),
        # (model.custom_tuple, ()),
    ],
)
def test_default_serializer(value: Any, expected: Any) -> None:
    assert default_serializer(value) == expected


def test_pydantic_json_compatibility() -> None:
    assert json.loads(model.json()) == json.loads(encode_json(model))


def test_unsupported_type_raises() -> None:
    with pytest.raises(TypeError):
        encode_json(lambda: None)
