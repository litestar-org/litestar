from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Literal

from litestar.exceptions import MissingDependencyException
from litestar.serialization import decode_json, encode_json
from litestar.types import Empty

try:
    import sqlalchemy  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("sqlalchemy") from e

if TYPE_CHECKING:
    from typing import Any, Mapping

    from sqlalchemy.engine.interfaces import IsolationLevel
    from sqlalchemy.pool import Pool
    from typing_extensions import TypeAlias

    from litestar.types import EmptyType

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
    """Configuration for SQLAlchemy's :class:`Engine <sqlalchemy.engine.Engine>`.

    For details see: https://docs.sqlalchemy.org/en/20/core/engines.html
    """

    connect_args: dict[Any, Any] | EmptyType = Empty
    """A dictionary of arguments which will be passed directly to the DBAPI's ``connect()`` method as keyword arguments.
    """
    echo: _EchoFlagType | EmptyType = Empty
    """If ``True``, the Engine will log all statements as well as a ``repr()`` of their parameter lists to the default
    log handler, which defaults to ``sys.stdout`` for output. If set to the string "debug", result rows will be printed
    to the standard output as well. The echo attribute of Engine can be modified at any time to turn logging on and off;
    direct control of logging is also available using the standard Python logging module.
    """
    echo_pool: _EchoFlagType | EmptyType = Empty
    """If ``True``, the connection pool will log informational output such as when connections are invalidated as well
    as when connections are recycled to the default log handler, which defaults to sys.stdout for output. If set to the
    string "debug", the logging will include pool checkouts and checkins. Direct control of logging is also available
    using the standard Python logging module."""
    enable_from_linting: bool | EmptyType = Empty
    """Defaults to True. Will emit a warning if a given SELECT statement is found to have un-linked FROM elements which
    would cause a cartesian product."""
    execution_options: Mapping[str, Any] | EmptyType = Empty
    """Dictionary execution options which will be applied to all connections. See
    :attr:`Connection.execution_options() <sqlalchemy.engine.Connection.execution_options>` for details."""
    hide_parameters: bool | EmptyType = Empty
    """Boolean, when set to ``True``, SQL statement parameters will not be displayed in INFO logging nor will they be
    formatted into the string representation of :class:`StatementError <sqlalchemy.exc.StatementError>` objects."""
    insertmanyvalues_page_size: int | EmptyType = Empty
    """Number of rows to format into an INSERT statement when the statement uses “insertmanyvalues” mode, which is a
    paged form of bulk insert that is used for many backends when using executemany execution typically in conjunction
    with RETURNING. Defaults to 1000, but may also be subject to dialect-specific limiting factors which may override
    this value on a per-statement basis."""
    isolation_level: IsolationLevel | EmptyType = Empty
    """Optional string name of an isolation level which will be set on all new connections unconditionally. Isolation
    levels are typically some subset of the string names "SERIALIZABLE", "REPEATABLE READ", "READ COMMITTED",
    "READ UNCOMMITTED" and "AUTOCOMMIT" based on backend."""
    json_deserializer: Callable[[str], Any] = decode_json
    """For dialects that support the :class:`JSON <sqlalchemy.types.JSON>` datatype, this is a Python callable that will
    convert a JSON string to a Python object. By default, this is set to Litestar's
    :attr:`decode_json() <.serialization.decode_json>` function."""
    json_serializer: Callable[[Any], str] = serializer
    """For dialects that support the JSON datatype, this is a Python callable that will render a given object as JSON.
    By default, Litestar's :attr:`encode_json() <.serialization.encode_json>` is used."""
    label_length: int | None | EmptyType = Empty
    """Optional integer value which limits the size of dynamically generated column labels to that many characters. If
    less than 6, labels are generated as “_(counter)”. If ``None``, the value of ``dialect.max_identifier_length``,
    which may be affected via the
    :attr:`create_engine.max_identifier_length parameter <sqlalchemy.create_engine.params.max_identifier_length>`, is
    used instead. The value of
    :attr:`create_engine.label_length <sqlalchemy.create_engine.params.label_length>` may not be larger than that of
    :attr:`create_engine.max_identifier_length <sqlalchemy.create_engine.params.max_identifier_length>`."""
    logging_name: str | EmptyType = Empty
    """String identifier which will be used within the “name” field of logging records generated within the
    “sqlalchemy.engine” logger. Defaults to a hexstring of the object`s id."""
    max_identifier_length: int | None | EmptyType = Empty
    """Override the max_identifier_length determined by the dialect. if ``None`` or ``0``, has no effect. This is the
    database`s configured maximum number of characters that may be used in a SQL identifier such as a table name, column
    name, or label name. All dialects determine this value automatically, however in the case of a new database version
    for which this value has changed but SQLAlchemy`s dialect has not been adjusted, the value may be passed here."""
    max_overflow: int | EmptyType = Empty
    """The number of connections to allow in connection pool “overflow”, that is connections that can be opened above
    and beyond the pool_size setting, which defaults to five. This is only used with
    :class:`QueuePool <sqlalchemy.pool.QueuePool>`."""
    module: Any | None | EmptyType = Empty
    """Reference to a Python module object (the module itself, not its string name). Specifies an alternate DBAPI module
    to be used by the engine`s dialect. Each sub-dialect references a specific DBAPI which will be imported before first
    connect. This parameter causes the import to be bypassed, and the given module to be used instead. Can be used for
    testing of DBAPIs as well as to inject “mock” DBAPI implementations into the
    :class:`Engine <sqlalchemy.engine.Engine>`."""
    paramstyle: _ParamStyle | None | EmptyType = Empty
    """The paramstyle to use when rendering bound parameters. This style defaults to the one recommended by the DBAPI
    itself, which is retrieved from the ``.paramstyle`` attribute of the DBAPI. However, most DBAPIs accept more than
    one paramstyle, and in particular it may be desirable to change a “named” paramstyle into a “positional” one, or
    vice versa. When this attribute is passed, it should be one of the values "qmark", "numeric", "named", "format" or
    "pyformat", and should correspond to a parameter style known to be supported by the DBAPI in use."""
    pool: Pool | None | EmptyType = Empty
    """An already-constructed instance of :class:`Pool <sqlalchemy.pool.Pool>`, such as a
    :class:`QueuePool <sqlalchemy.pool.QueuePool>` instance. If non-None, this pool will be used directly as the
    underlying connection pool for the engine, bypassing whatever connection parameters are present in the URL argument.
    For information on constructing connection pools manually, see
    `Connection Pooling <https://docs.sqlalchemy.org/en/20/core/pooling.html>`_."""
    poolclass: type[Pool] | None | EmptyType = Empty
    """A :class:`Pool <sqlalchemy.pool.Pool>` subclass, which will be used to create a connection pool instance using
    the connection parameters given in the URL. Note this differs from pool in that you don`t actually instantiate the
    pool in this case, you just indicate what type of pool to be used."""
    pool_logging_name: str | EmptyType = Empty
    """String identifier which will be used within the “name” field of logging records generated within the
    “sqlalchemy.pool” logger. Defaults to a hexstring of the object`s id."""
    pool_pre_ping: bool | EmptyType = Empty
    """If True will enable the connection pool “pre-ping” feature that tests connections for liveness upon each
    checkout."""
    pool_size: int | EmptyType = Empty
    """The number of connections to keep open inside the connection pool. This used with
    :class:`QueuePool <sqlalchemy.pool.QueuePool>` as well as
    :class:`SingletonThreadPool <sqlalchemy.pool.SingletonThreadPool>`. With
    :class:`QueuePool <sqlalchemy.pool.QueuePool>`, a pool_size setting of ``0`` indicates no limit; to disable pooling,
    set ``poolclass`` to :class:`NullPool <sqlalchemy.pool.NullPool>` instead."""
    pool_recycle: int | EmptyType = Empty
    """This setting causes the pool to recycle connections after the given number of seconds has passed. It defaults to
    ``-1``, or no timeout. For example, setting to ``3600`` means connections will be recycled after one hour. Note that
    MySQL in particular will disconnect automatically if no activity is detected on a connection for eight hours
    (although this is configurable with the MySQLDB connection itself and the server configuration as well)."""
    pool_reset_on_return: Literal["rollback", "commit"] | EmptyType = Empty
    """Set the :attr:`Pool.reset_on_return <sqlalchemy.pool.Pool.params.reset_on_return` parameter of the underlying
    :class`Pool <sqlalchemy.pool.Pool>` object, which can be set to the values ``"rollback"``, ``"commit"``, or
    ``None``."""
    pool_timeout: int | EmptyType = Empty
    """Number of seconds to wait before giving up on getting a connection from the pool. This is only used with
    :class:`QueuePool <sqlalchemy.pool.QueuePool>`. This can be a float but is subject to the limitations of Python time
    functions which may not be reliable in the tens of milliseconds."""
    pool_use_lifo: bool | EmptyType = Empty
    """Use LIFO (last-in-first-out) when retrieving connections from :class:`QueuePool <sqlalchemy.pool.QueuePool>`
    instead of FIFO (first-in-first-out). Using LIFO, a server-side timeout scheme can reduce the number of connections
    used during non-peak periods of use. When planning for server-side timeouts, ensure that a recycle or pre-ping
    strategy is in use to gracefully handle stale connections."""
    plugins: list[str] | EmptyType = Empty
    """String list of plugin names to load. See :class:`CreateEnginePlugin <sqlalchemy.engine.CreateEnginePlugin>` for
    background."""
    query_cache_size: int | EmptyType = Empty
    """Size of the cache used to cache the SQL string form of queries. Set to zero to disable caching.

    See :attr:`query_cache_size <sqlalchemy.create_engine.params.query_cache_size>` for more info.
    """
    use_insertmanyvalues: bool | EmptyType = Empty
    """``True`` by default, use the “insertmanyvalues” execution style for INSERT..RETURNING statements by default."""
