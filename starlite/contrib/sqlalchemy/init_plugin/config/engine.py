from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Literal

from starlite.exceptions import MissingDependencyException
from starlite.serialization import decode_json, encode_json
from starlite.types import Empty

try:
    import sqlalchemy  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("sqlalchemy is not installed") from e

if TYPE_CHECKING:
    from typing import Any, Mapping

    from sqlalchemy.engine.interfaces import IsolationLevel
    from sqlalchemy.pool import Pool
    from typing_extensions import TypeAlias

    from starlite.types import EmptyType

__all__ = ("EngineConfig",)

_EchoFlagType: TypeAlias = "None | bool | Literal['debug']"
_ParamStyle = Literal["qmark", "numeric", "named", "format", "pyformat", "numeric_dollar"]


def serializer(value: Any) -> str:
    """Serialize JSON field values.

    Args:
        value: Any json serializable value.

    Returns:
        JSON string.
    """
    return encode_json(value).decode("utf-8")


@dataclass
class EngineConfig:
    """Configuration for SQLAlchemy's :class`Engine <sqlalchemy.engine.Engine>`.

    For details see: https://docs.sqlalchemy.org/en/20/core/engines.html
    """

    connect_args: dict[Any, Any] | EmptyType = Empty
    echo: _EchoFlagType | EmptyType = Empty
    echo_pool: _EchoFlagType | EmptyType = Empty
    enable_from_linting: bool | EmptyType = Empty
    execution_options: Mapping[str, Any] | EmptyType = Empty
    hide_parameters: bool | EmptyType = Empty
    insertmanyvalues_page_size: int | EmptyType = Empty
    isolation_level: IsolationLevel | EmptyType = Empty
    json_deserializer: Callable[[str], Any] = decode_json
    json_serializer: Callable[[Any], str] = serializer
    label_length: int | None | EmptyType = Empty
    logging_name: str | EmptyType = Empty
    max_identifier_length: int | None | EmptyType = Empty
    max_overflow: int | EmptyType = Empty
    module: Any | None | EmptyType = Empty
    paramstyle: _ParamStyle | None | EmptyType = Empty
    pool: Pool | None | EmptyType = Empty
    poolclass: type[Pool] | None | EmptyType = Empty
    pool_logging_name: str | EmptyType = Empty
    pool_pre_ping: bool | EmptyType = Empty
    pool_size: int | EmptyType = Empty
    pool_recycle: int | EmptyType = Empty
    pool_reset_on_return: Literal["rollback", "commit"] | EmptyType = Empty
    pool_timeout: int | EmptyType = Empty
    pool_use_lifo: bool | EmptyType = Empty
    plugins: list[str] | EmptyType = Empty
    query_cache_size: int | EmptyType = Empty
    use_insertmanyvalues: bool | EmptyType = Empty
