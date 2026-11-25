import dataclasses
import sys
import warnings

import pytest

from litestar.dto import DTOConfig
from litestar.exceptions import ImproperlyConfiguredException, LitestarDeprecationWarning


def test_include_and_exclude_raises() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        DTOConfig(include={"a"}, exclude={"b"})


@dataclasses.dataclass(frozen=True)
class SubConfig(DTOConfig):
    extra: int = 0


@pytest.mark.parametrize("value", [True, False])
def test_experimental_codegen_backend_is_deprecated_and_ignored(value: bool) -> None:
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        DTOConfig()
        DTOConfig(experimental_codegen_backend=None)
        config = DTOConfig(experimental_codegen_backend=value, exclude={"a"})
        round_trips = [
            dataclasses.replace(config, partial=True),
            DTOConfig(**dataclasses.asdict(config)),
            SubConfig(**dataclasses.asdict(config)),
        ]
        replaced = dataclasses.replace(config, experimental_codegen_backend=value)

    assert [(warning.category, warning.filename) for warning in record] == [(LitestarDeprecationWarning, __file__)] * 2
    message = str(record[0].message)
    assert "DTOConfig.experimental_codegen_backend" in message
    assert "Deprecated in litestar 3.0" in message
    assert "removed in 4.0" in message
    assert config.experimental_codegen_backend is None
    assert replaced == config == DTOConfig(exclude={"a"})
    assert all(round_trip.exclude == {"a"} for round_trip in round_trips)


@dataclasses.dataclass(frozen=True)
class PostInitConfig(DTOConfig):
    def __post_init__(self) -> None:
        super().__post_init__()


def test_experimental_codegen_backend_warning_names_the_caller_of_a_subclass() -> None:
    with pytest.warns(LitestarDeprecationWarning) as record:
        line = sys._getframe().f_lineno + 1
        PostInitConfig(experimental_codegen_backend=True)

    assert [(warning.filename, warning.lineno) for warning in record] == [(__file__, line)]
