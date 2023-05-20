What's new in 2.0?
==================

Overview of changes

TBD: Intro section



HTMX support
    Basic support for HTMX requests and responses.

    .. seealso::

        :doc:`/usage/contrib/htmx`

Unified storage interfaces
    Storage backends for server-side sessions ``starlite.cache.Cache``` have been
    unified and replaced by the ``starlite.storages``, which implements generic
    asynchronous key/values stores backed by memory, the file system or redis.

    .. seealso::

        :doc:`/usage/stores`


Event bus
    A simple event bus system for Litestar, supporting synchronous and asynchronous
    listeners and emitters, providing a similar interface to handlers. It currently
    features a simple in-memory, process-local backend

    .. seealso::
        :doc:`/usage/events`
        :doc:`/reference/events`


SQLAlchemy Repository
    TBD


Enhanced WebSocket support
    A new set of features for handling WebSockets, including automatic connection
    handling, (de)serialization of incoming and outgoing data analogous to route
    handlers, OOP based event dispatching, data iterators and more.

    .. seealso::
        :ref:`change:2.0.0alpha3-enhanced websockets support`
        :ref:`change:2.0.0alpha6-websockets: managing a socket's lifespan using a context manager in websocket listeners`
        :ref:`change:2.0.0alpha6-websockets: messagepack support`
        :ref:`change:2.0.0alpha6-websockets: data iterators`
        :doc:`/usage/websockets`


Attrs signature modelling
    TBD


:class:`~typing.Annotated` support in route handler
    :class:`Annotated <typing.Annotated>` can now be used in route handler and
    dependencies to specify additional information about the fields

    .. code-block:: python

        @get("/")
        def index(param: int = Parameter(gt=5)) -> dict[str, int]:
            ...

    .. code-block:: python

        @get("/")
        def index(param: Annotated[int, Parameter(gt=5)]) -> dict[str, int]:
            ...


DTOs
    TBD


Channels
    :doc:`channels </usage/channels>` are a general purpose event streaming module,
    which can for example be used to broadcast messages via WebSockets and includes
    functionalities such as automatically generating WebSocket route handlers to
    broadcast messages
