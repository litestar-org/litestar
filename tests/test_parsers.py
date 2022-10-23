from typing import Dict

import pytest
from pydantic import BaseConfig
from pydantic.fields import ModelField

from starlite import Cookie, RequestEncodingType
from starlite.datastructures import FormMultiDict
from starlite.parsers import parse_cookie_string, parse_form_data, parse_query_params
from starlite.testing import RequestFactory


def test_parse_query_params() -> None:
    query = {
        "value": "10",
        "veggies": ["tomato", "potato", "aubergine"],
        "calories": "122.53",
        "healthy": True,
        "polluting": False,
    }
    request = RequestFactory().get("/", query_params=query)  # type: ignore[arg-type]
    result = parse_query_params(query_string=request.scope.get("query_string", b""))
    assert result == {
        "value": ["10"],
        "veggies": ["tomato", "potato", "aubergine"],
        "calories": ["122.53"],
        "healthy": [True],
        "polluting": [False],
    }


def test_parse_form_data() -> None:
    form_data = FormMultiDict(
        [
            ("value", "10"),
            ("value", "12"),
            ("veggies", '["tomato", "potato", "aubergine"]'),
            ("nested", '{"some_key": "some_value"}'),
            ("calories", "122.53"),
            ("healthy", True),
            ("polluting", False),
        ]
    )
    result = parse_form_data(
        media_type=RequestEncodingType.MULTI_PART,
        form_data=form_data,
        field=ModelField(name="test", type_=int, class_validators=None, model_config=BaseConfig),
    )
    assert result == {
        "value": [10, 12],
        "veggies": ["tomato", "potato", "aubergine"],
        "nested": {"some_key": "some_value"},
        "calories": 122.53,
        "healthy": True,
        "polluting": False,
    }


@pytest.mark.parametrize(
    "cookie_string, expected",
    (
        ("ABC    = 123;   efg  =   456", {"ABC": "123", "efg": "456"}),
        (("foo= ; bar="), {"foo": "", "bar": ""}),
        ('foo="bar=123456789&name=moisheZuchmir"', {"foo": "bar=123456789&name=moisheZuchmir"}),
        ("email=%20%22%2c%3b%2f", {"email": ' ",;/'}),
        ("foo=%1;bar=bar", {"foo": "%1", "bar": "bar"}),
        ("foo=bar;fizz  ; buzz", {"": "buzz", "foo": "bar"}),
        ("  fizz; foo=  bar", {"": "fizz", "foo": "bar"}),
        ("foo=false;bar=bar;foo=true", {"bar": "bar", "foo": "true"}),
        ("foo=;bar=bar;foo=boo", {"bar": "bar", "foo": "boo"}),
        (
            Cookie(key="abc", value="123", path="/head", domain="localhost").to_header(header=""),
            {"Domain": "localhost", "Path": "/head", "SameSite": "lax", "abc": "123"},
        ),
    ),
)
def test_parse_cookie_string(cookie_string: str, expected: Dict[str, str]) -> None:
    assert parse_cookie_string(cookie_string) == expected
