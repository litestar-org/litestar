.. admonition:: Synchronous and asynchronous callables
    :class: important

    Both synchronous and asynchronous :term:`callables <python:callable>` are supported. One important aspect of
    this is that using a synchronous function which perform blocking operations, such
    as I/O or computationally intensive tasks, can potentially block the main thread
    running the event loop, and in turn block the whole application.

    To mitigate this, the :paramref:`~litestar.handlers.HTTPRouteHandler.sync_to_thread` parameter can be set to
    ``True``, which will result in the function being run in a thread pool. Should the function be
    non-blocking, :paramref:`~litestar.handlers.HTTPRouteHandler.sync_to_thread` should be set to ``False`` instead.

    If a synchronous function is passed, without setting an explicit
    :paramref:`~litestar.handlers.HTTPRouteHandler.sync_to_thread` value, a warning will be raised.

    .. seealso::

        :doc:`/topics/sync-vs-async`
