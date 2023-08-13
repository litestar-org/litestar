import pytest

from litestar.dto import DTOConfig
from litestar.exceptions import ImproperlyConfiguredException


def test_include_and_exclude_raises() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        DTOConfig(include={"a"}, exclude={"b"})
