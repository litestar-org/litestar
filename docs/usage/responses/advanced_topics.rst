Advanced Topics
===============

Background Tasks
----------------

All Litestar responses allow passing in a ``background`` kwarg. This kwarg accepts either an instance of
:class:`BackgroundTask <.background_tasks.BackgroundTask>` or an instance of
:class:`BackgroundTasks <.background_tasks.BackgroundTasks>`, which wraps an iterable of
:class:`BackgroundTask <.background_tasks.BackgroundTask>` instances.

A background task is a sync or async callable (function, method, or class that implements the :meth:`object.__call__`
dunder method) that will be called after the response finishes sending the data.

Thus, in the following example the passed in background task will be executed after the response sends:

.. literalinclude:: /examples/responses/background_tasks_1.py
    :caption: Background Task Passed into Response
    :language: python

When the ``greeter`` handler is called, the logging task will be called with any ``*args`` and ``**kwargs`` passed into
the :class:`BackgroundTask <.background_tasks.BackgroundTask>`.

.. note::

    In the above example ``"greeter"`` is an arg and ``message=f"was called with name {name}"`` is a kwarg.
    The function signature of ``logging_task`` allows for this, so this should pose no problem.
    :class:`BackgroundTask <.background_tasks.BackgroundTask>` is typed with :class:`ParamSpec <typing.ParamSpec>`,
    enabling correct type checking for arguments and keyword arguments passed to it.

Route decorators (e.g. ``@get``, ``@post``, etc.) also allow passing in a background task with the ``background`` kwarg:

.. literalinclude:: /examples/responses/background_tasks_2.py
    :caption: Background Task Passed into Decorator
    :language: python


.. note::

    Route handler arguments cannot be passed into background tasks when they are passed into decorators.

Executing Multiple Background Tasks
+++++++++++++++++++++++++++++++++++

You can also use the :class:`BackgroundTasks <.background_tasks.BackgroundTasks>` class and pass to it an iterable
(:class:`list`, :class:`tuple`, etc.) of :class:`BackgroundTask <.background_tasks.BackgroundTask>` instances:

.. literalinclude:: /examples/responses/background_tasks_3.py
    :caption: Multiple Background Tasks
    :language: python


:class:`BackgroundTasks <.background_tasks.BackgroundTasks>` class
accepts an optional keyword argument ``run_in_task_group`` with a default value of ``False``. Setting this to ``True``
allows background tasks to run concurrently, using an `anyio.task_group <https://anyio.readthedocs.io/en/stable/tasks.html>`_.

.. note::

   Setting ``run_in_task_group`` to ``True`` will not preserve execution order.

Pagination
-----------

When you need to return a large number of items from an endpoint it is common practice to use pagination to ensure
clients can request a specific subset or "page" from the total dataset. Litestar supports three types of pagination out
of the box:

* classic pagination
* limit / offset pagination
* cursor pagination

Classic Pagination
++++++++++++++++++

In classic pagination the dataset is divided into pages of a specific size and the consumer then requests a specific page.

.. literalinclude:: /examples/pagination/using_classic_pagination.py
    :caption: Classic Pagination
    :language: python

The data container for this pagination is called :class:`ClassicPagination <.pagination.ClassicPagination>`, which is
what will be returned by the paginator in the above example This will also generate the corresponding OpenAPI
documentation.

If you require async logic, you can implement
the :class:`AbstractAsyncClassicPaginator <.pagination.AbstractAsyncClassicPaginator>` instead of the
:class:`AbstractSyncClassicPaginator <.pagination.AbstractSyncClassicPaginator>`.

Offset Pagination
+++++++++++++++++

In offset pagination the consumer requests a number of items specified by ``limit`` and the ``offset`` from the beginning of the dataset.
For example, given a list of 50 items, you could request ``limit=10``, ``offset=39`` to request items 40-50.

.. literalinclude:: /examples/pagination/using_offset_pagination.py
    :caption: Offset Pagination
    :language: python

The data container for this pagination is
called :class:`OffsetPagination <.pagination.OffsetPagination>`, which is what will be returned by the paginator in the
above example This will also generate the corresponding OpenAPI documentation.

If you require async logic, you can implement
the :class:`AbstractAsyncOffsetPaginator <.pagination.AbstractAsyncOffsetPaginator>` instead of the
:class:`AbstractSyncOffsetPaginator <.pagination.AbstractSyncOffsetPaginator>`.

Offset Pagination With SQLAlchemy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When retrieving paginated data from the database using SQLAlchemy, the Paginator instance requires an SQLAlchemy session
instance to make queries. This can be achieved with :doc:`/usage/dependency-injection`


Cursor Pagination
+++++++++++++++++

In cursor pagination the consumer requests a number of items specified by ``results_per_page`` and a ``cursor`` after which results are given.
Cursor is unique identifier within the dataset that serves as a way to point the starting position.

.. literalinclude:: /examples/pagination/using_cursor_pagination.py
    :caption: Cursor Pagination
    :language: python

The data container for this pagination is called :class:`CursorPagination <.pagination.CursorPagination>`, which is what
will be returned by the paginator in the above example This will also generate the corresponding OpenAPI documentation.

If you require async logic, you can implement
the :class:`AbstractAsyncCursorPaginator <.pagination.AbstractAsyncCursorPaginator>` instead of the
:class:`AbstractSyncCursorPaginator <.pagination.AbstractSyncCursorPaginator>`.
