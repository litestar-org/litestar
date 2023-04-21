from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import pytest

from litestar._signature.models.attrs_signature_model import _converter
from tests import Person, PersonFactory

now = datetime.now(tz=timezone.utc)
today = now.date()
time_now = time(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)
one_minute = timedelta(minutes=1)
person = PersonFactory.build()


@pytest.mark.parametrize(
    "value,expected",
    (
        ("1", True),
        (b"1", True),
        ("True", True),
        (b"True", True),
        ("on", True),
        (b"on", True),
        ("t", True),
        (b"t", True),
        ("true", True),
        (b"true", True),
        ("y", True),
        (b"y", True),
        ("yes", True),
        (b"yes", True),
        (1, True),
        (True, True),
        ("0", False),
        (b"0", False),
        ("False", False),
        (b"False", False),
        ("f", False),
        (b"f", False),
        ("false", False),
        (b"false", False),
        ("n", False),
        (b"n", False),
        ("no", False),
        (b"no", False),
        ("off", False),
        (b"off", False),
        (0, False),
        (False, False),
    ),
)
def test_cattrs_converter_structure_bool(value: Any, expected: Any) -> None:
    result = _converter.structure(value, bool)
    assert result == expected


def test_cattrs_converter_structure_bool_value_error() -> None:
    with pytest.raises(ValueError):
        _converter.structure(None, bool)
        _converter.structure("foofoofoo", bool)
        _converter.structure(object(), bool)
        _converter.structure(type, bool)
        _converter.structure({}, bool)
        _converter.structure([], bool)


@pytest.mark.parametrize(
    "value,cls,expected",
    (
        (now, datetime, now.isoformat()),
        (now.isoformat(), datetime, now.isoformat()),
    ),
)
def test_cattrs_converter_structure_datetime(value: Any, cls: Any, expected: Any) -> None:
    result = _converter.structure(value, cls).isoformat()
    assert result == expected


@pytest.mark.parametrize(
    "value,cls,expected",
    (
        (now, date, today.isoformat()),
        (now.isoformat(), date, today.isoformat()),
        (now.timestamp(), date, today.isoformat()),
        (today, date, today.isoformat()),
        (today.isoformat(), date, today.isoformat()),
    ),
)
def test_cattrs_converter_structure_date(value: Any, cls: Any, expected: Any) -> None:
    result = _converter.structure(value, cls).isoformat()
    assert result == expected


@pytest.mark.parametrize(
    "value,cls,expected",
    (
        (time_now, time, time_now.isoformat()),
        (time_now.isoformat(), time, time_now.isoformat()),
    ),
)
def test_cattrs_converter_structure_time(value: Any, cls: Any, expected: Any) -> None:
    result = _converter.structure(value, cls).isoformat()
    assert result == expected


@pytest.mark.parametrize(
    "value,cls,expected",
    (
        (one_minute, timedelta, one_minute.total_seconds()),
        (one_minute.total_seconds(), timedelta, one_minute.total_seconds()),
        ("1 minute", timedelta, one_minute.total_seconds()),
    ),
)
def test_cattrs_converter_structure_timedelta(value: Any, cls: Any, expected: Any) -> None:
    result = _converter.structure(value, cls).total_seconds()
    assert result == expected


@pytest.mark.parametrize(
    "value,cls,expected",
    (
        (person, Person, person.dict()),
        (person.dict(), Person, person.dict()),
    ),
)
def test_cattrs_converter_structure_pydantic(value: Any, cls: Any, expected: Any) -> None:
    result = _converter.structure(value, cls).dict()
    assert result == expected
