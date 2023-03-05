from __future__ import annotations

from typing import TYPE_CHECKING, FrozenSet, List, Optional, Set, Tuple, Union

import pytest

from starlite._signature.parsing import create_signature_model

from . import ConcreteDTO

if TYPE_CHECKING:
    from typing import Any


@pytest.mark.parametrize(
    "annotation",
    [
        ConcreteDTO,
        FrozenSet[ConcreteDTO],
        List[ConcreteDTO],
        Set[ConcreteDTO],
        Tuple[ConcreteDTO, ...],
        Tuple[ConcreteDTO, ConcreteDTO],
        Optional[ConcreteDTO],
        Union[ConcreteDTO, None],  # noqa: SIM907
    ],
)
def test_create_signature_model(annotation: type[Any]) -> None:
    def func(data: annotation) -> None:  # type:ignore[valid-type]
        ...

    signature_model = create_signature_model(
        func, plugins=[], dependency_name_set=set(), namespace={"annotation": annotation}
    )
    assert signature_model.fields["data"].has_dto_annotation
