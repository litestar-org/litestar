from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

import pydantic
from pydantic import (
    conbytes,
    condate,
    condecimal,
    confloat,
    conint,
    conlist,
    conset,
    constr,
)

from litestar.exceptions import HTTPException


class PetException(HTTPException):
    status_code = 406


class Gender(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"
    ANY = "A"


constr_kws: "list[dict[str, Any]]" = [
    {"pattern": "^[a-zA-Z]$"},
    {"to_upper": True, "min_length": 1, "pattern": "^[a-zA-Z]$"},
    {"to_lower": True, "min_length": 1, "pattern": "^[a-zA-Z]$"},
    {"to_lower": True, "min_length": 10, "pattern": "^[a-zA-Z]$"},
    {"to_lower": True, "min_length": 10, "max_length": 100, "pattern": "^[a-zA-Z]$"},
    {"min_length": 1},
    {"min_length": 10},
    {"min_length": 10, "max_length": 100},
]

conlist_kws: "list[dict[str, Any]]" = [
    {"min_length": 1},
    {"min_length": 1, "max_length": 10},
]

if pydantic.VERSION.startswith("1"):
    for kw in constr_kws:
        if "pattern" in kw:
            kw["regex"] = kw.pop("pattern")

    for kw in conlist_kws:
        if "max_length" in kw:
            kw["max_items"] = kw.pop("max_length")
        if "min_length" in kw:
            kw["min_items"] = kw.pop("min_length")

constrained_string = [
    *(constr(**kw) for kw in constr_kws),
    *[
        conbytes(min_length=1),
        conbytes(min_length=10),
        conbytes(min_length=10, max_length=100),
    ],
]

constrained_collection = [
    *(conlist(int, **kw) for kw in conlist_kws),
    *(conset(int, **kw) for kw in conlist_kws),
]

constrained_numbers = [
    conint(gt=10, lt=100),
    conint(ge=10, le=100),
    conint(ge=10, le=100, multiple_of=7),
    confloat(gt=10, lt=100),
    confloat(ge=10, le=100),
    confloat(ge=10, le=100, multiple_of=4.2),
    confloat(gt=10, lt=100, multiple_of=10),
    condecimal(gt=Decimal("10"), lt=Decimal("100")),
    condecimal(ge=Decimal("10"), le=Decimal("100")),
    condecimal(gt=Decimal("10"), lt=Decimal("100"), multiple_of=Decimal("5")),
    condecimal(ge=Decimal("10"), le=Decimal("100"), multiple_of=Decimal("2")),
]

constrained_dates = [
    condate(gt=date.today() - timedelta(days=10), lt=date.today() + timedelta(days=100)),
    condate(ge=date.today() - timedelta(days=10), le=date.today() + timedelta(days=100)),
    condate(gt=date.today() - timedelta(days=10), lt=date.today() + timedelta(days=100)),
    condate(ge=date.today() - timedelta(days=10), le=date.today() + timedelta(days=100)),
]
