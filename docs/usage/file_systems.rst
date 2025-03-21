File Systems
============

When sending files with :class:`~litestar.response.File` or serving
them using :func:`~litestar.static_files.create_static_files_router`, in addition to
doing so from the local file system Litestar also supports custom file systems,
including support for `fsspec <https://filesystem-spec.readthedocs.io/en/latest/>`_,
which enables an integration with a wide range of remote file systems.

At its core, a file system is any class that implements the abstract
:class:`~litestar.file_system.BaseFileSystem` class. By default, Litestar ships with a
single implementation: :class:`~litestar.file_system.BaseLocalFileSystem`.


.. literalinclude:: /examples/responses/file_response_fs.py
    :language: python
    :caption: Sending files from S3


Supported file systems
----------------------

In addition to file systems implemented on top of
:class:`~litestar.file_system.BaseFileSystem`, all ``fsspec`` file systems, synchronous
and asynchronous, as supported. They will be wrapped in
:class:`~litestar.file_system.FsspecSyncWrapper` or
:class:`~litestar.file_system.FsspecAsyncWrapper` respective to conform to a common
interface.


fsspec
+++++++

Everywhere :class:`~litestar.file_system.BaseFileSystem` is accepted, ``fsspec``
file systems are usually accepted as well.

It can still make sense to set them up in the `Registry` instead or wrap them manually
with :func:`~litestar.file_system.maybe_wrap_fsspec_file_system` once and use that
wrapper, so they don't have to be wrapped again for every usage:

.. tab-set::

    .. tab-item:: Don't

        .. literalinclude:: /examples/file_systems/fsspec_implicit_wrap.py
            :language: python

    .. tab-item:: Do instead

        .. literalinclude:: /examples/file_systems/fsspec_wrap.py
            :language: python
            :caption: Explicitly wrapping an fsspec file system

        or

        .. literalinclude:: /examples/file_systems/fsspec_registry_wrap.py
            :language: python
            :caption: Using the registry to automatically wrap an fsspec file system


.. important::

    If an asynchronous fsspec file system is used, it should always be constructed with
    ``asynchronous=True`` **without** passing a ``loop``, so Litestar can use their
    native async functions.

    .. seealso::
        https://filesystem-spec.readthedocs.io/en/latest/async.html#using-from-async



Registry
--------

For easier configuration and testing, :class:`~litestar.file_system.FileSystemRegistry`
can be used to register file systems under a name by which they can be referenced later.

.. literalinclude:: /examples/file_systems/registry.py
    :language: python
    :caption: Sending files from S3 by using the registry


.. tip::
    When adding an fsspec file system, it will automatically be wrapped to be compatible
    with :class:`~litestar.file_system.BaseFileSystem`.


:class:`~litestar.file_system.FileSystemRegistry` is implemented as a plugin which is
set up automatically unless an instance of it is passed to the application
explicitly.

If needed, the registry can be accessed like any other plugin:

.. literalinclude:: /examples/file_systems/registry_access.py
    :language: python
    :caption: Accessing the registry


Setting a default file system
+++++++++++++++++++++++++++++

For actions that involve sending files, if no file system is passed explicitly, Litestar
will use the default file system defined in the registry. This defaults to
:class:`~litestar.file_system.BaseLocalFileSystem`, but may be configured to any
supported file system.

.. literalinclude:: /examples/file_systems/registry_default.py
    :language: python
    :caption: Changing the default file system
