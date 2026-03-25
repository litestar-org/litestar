from types import ModuleType, TracebackType
from typing import Any, Optional, Protocol, TypeAlias, Union


class PDBProtocol(Protocol):
    @staticmethod
    def post_mortem(
        traceback: TracebackType | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any: ...


Debugger: TypeAlias = Union[ModuleType, PDBProtocol]
