from types import ModuleType, TracebackType
from typing import Any, Protocol, Union

from typing_extensions import TypeAliasType


class PDBProtocol(Protocol):
    @staticmethod
    def post_mortem(
        traceback: TracebackType | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any: ...


Debugger = TypeAliasType("Debugger", Union[ModuleType, PDBProtocol])
