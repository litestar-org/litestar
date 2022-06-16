from typing import Optional

import pytest
from pydantic.fields import FieldInfo
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from typing_extensions import Type

from starlite import Parameter, create_test_client, get


@pytest.mark.parametrize(
    "t_type,param_dict, param, should_raise",
    [
        (str, {"special-cookie": "123"}, Parameter(cookie="special-cookie", min_length=1, max_length=3), False),
        (str, {"special-cookie": "123"}, Parameter(cookie="special-cookie", min_length=1, max_length=2), True),
        (str, {}, Parameter(cookie="special-cookie", min_length=1, max_length=2), True),
        (Optional[str], {}, Parameter(cookie="special-cookie", min_length=1, max_length=2, required=False), False),
        (int, {"special-cookie": "123"}, Parameter(cookie="special-cookie", ge=100, le=201), False),
        (int, {"special-cookie": "123"}, Parameter(cookie="special-cookie", ge=100, le=120), True),
        (int, {}, Parameter(cookie="special-cookie", ge=100, le=120), True),
        (Optional[int], {}, Parameter(cookie="special-cookie", ge=100, le=120, required=False), False),
    ],
)
def test_cookie_params(t_type: Type, param_dict: dict, param: FieldInfo, should_raise: bool) -> None:
    test_path = "/test"

    @get(path=test_path)
    def test_method(special_cookie: t_type = param) -> None:  # type: ignore
        if special_cookie:
            assert special_cookie in [param_dict.get("special-cookie"), int(param_dict.get("special-cookie"))]  # type: ignore

    with create_test_client(test_method) as client:
        response = client.get(test_path, cookies=param_dict)
        if should_raise:
            assert response.status_code == HTTP_400_BAD_REQUEST
        else:
            assert response.status_code == HTTP_200_OK
