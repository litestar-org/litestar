import dataclasses
import warnings

import pytest

from litestar.dto import DTOConfig
from litestar.exceptions import ImproperlyConfiguredException, LitestarDeprecationWarning


def test_include_and_exclude_raises() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        DTOConfig(include={"a"}, exclude={"b"})


@pytest.mark.parametrize("value", [True, False])
def test_experimental_codegen_backend_emits_deprecation_warning(value: bool) -> None:
    with pytest.warns(LitestarDeprecationWarning, match="DTOConfig.experimental_codegen_backend") as record:
        config = DTOConfig(experimental_codegen_backend=value)

    assert len(record) == 1
    assert record[0].filename == __file__
    assert "Deprecated in litestar 3.0" in str(record[0].message)
    assert "removed in 4.0" in str(record[0].message)
    assert config.experimental_codegen_backend is None
    assert config == DTOConfig()


def test_experimental_codegen_backend_unset_does_not_warn() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        DTOConfig()
        DTOConfig(experimental_codegen_backend=None)


def test_experimental_codegen_backend_warns_once_through_round_trips() -> None:
    @dataclasses.dataclass(frozen=True)
    class SubConfig(DTOConfig):
        extra: int = 0

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        config = DTOConfig(experimental_codegen_backend=False, exclude={"a"})
        replaced = dataclasses.replace(config, partial=True)
        copied = DTOConfig(**dataclasses.asdict(config))
        sub = SubConfig(**dataclasses.asdict(config))

    assert len(record) == 1
    assert record[0].category is LitestarDeprecationWarning
    assert replaced.exclude == {"a"}
    assert copied.exclude == {"a"}
    assert sub.exclude == {"a"}
