from functools import lru_cache

import pytest
from starlette.status import HTTP_204_NO_CONTENT

from starlite import ImproperlyConfiguredException, get
from starlite.utils import model_function_signature


def test_create_function_signature_model_ignore_return_annotation():
    @get(path="/health", status_code=HTTP_204_NO_CONTENT)
    async def health_check() -> None:
        return

    assert model_function_signature(health_check.fn, [])().dict() == {}


def test_create_function_signature_model_validation():
    with pytest.raises(ImproperlyConfiguredException):
        model_function_signature(lru_cache(maxsize=0)(lambda x: x), [])
