import pytest

from litestar.dto import DTOConfig
from litestar.exceptions import ImproperlyConfiguredException


def test_include_and_exclude_raises() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        DTOConfig(include={"a"}, exclude={"b"})


@pytest.mark.parametrize("value", [True, False])
def test_experimental_codegen_backend_is_deprecated(value: bool) -> None:
    with pytest.warns(DeprecationWarning, match="DTOConfig.experimental_codegen_backend"):
        config = DTOConfig(experimental_codegen_backend=value)

    assert config.experimental_codegen_backend is value


def test_experimental_codegen_backend_unset_does_not_warn(recwarn: pytest.WarningsRecorder) -> None:
    DTOConfig()

    assert not recwarn.list
