from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from typing import TypeAlias

    import pydantic

PydanticVersion = Literal["v2"]
BaseModelType: TypeAlias = "type[pydantic.BaseModel]"
