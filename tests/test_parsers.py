from pydantic import BaseConfig
from pydantic.fields import ModelField

from starlite import RequestEncodingType, parsers
from starlite.datastructures import FormMultiDict
from starlite.testing import create_test_request


def test_parse_query_params() -> None:
    query = {
        "value": "10",
        "veggies": ["tomato", "potato", "aubergine"],
        "calories": "122.53",
        "healthy": True,
        "polluting": False,
    }
    request = create_test_request(query=query)  # type: ignore
    result = parsers.parse_query_params(connection=request)
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
    result = parsers.parse_form_data(
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
