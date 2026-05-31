文件系统
============

当使用 :class:`~litestar.response.File` 发送文件或使用 :func:`~litestar.static_files.create_static_files_router` 提供文件服务时，除了从本地文件系统提供服务外，Litestar 还支持自定义文件系统，包括对 `fsspec <https://filesystem-spec.readthedocs.io/en/latest/>`_ 的支持，这使得可以集成各种远程文件系统。

在其核心，文件系统是任何实现抽象 :class:`~litestar.file_system.BaseFileSystem` 类的类。默认情况下，Litestar 附带单个实现：:class:`~litestar.file_system.BaseLocalFileSystem`。


.. literalinclude:: /examples/responses/file_response_fs.py
    :language: python
    :caption: 从 S3 发送文件


支持的文件系统
----------------------

除了基于 :class:`~litestar.file_system.BaseFileSystem` 实现的文件系统外，所有 ``fsspec`` 文件系统（同步和异步）都受支持。它们将分别包装在 :class:`~litestar.file_system.FsspecSyncWrapper` 或 :class:`~litestar.file_system.FsspecAsyncWrapper` 中以符合通用接口。


fsspec
+++++++

在接受 :class:`~litestar.file_system.BaseFileSystem` 的任何地方，通常也接受 ``fsspec`` 文件系统。

将它们设置在 `Registry` 中，或使用 :func:`~litestar.file_system.maybe_wrap_fsspec_file_system` 手动包装一次并使用该包装器，这样它们就不必为每次使用再次包装，这仍然是有意义的：

.. tab-set::

    .. tab-item:: 不推荐

        .. literalinclude:: /examples/file_systems/fsspec_implicit_wrap.py
            :language: python

    .. tab-item:: 建议这样做

        .. literalinclude:: /examples/file_systems/fsspec_wrap.py
            :language: python
            :caption: 显式包装 fsspec 文件系统

        或者

        .. literalinclude:: /examples/file_systems/fsspec_registry_wrap.py
            :language: python
            :caption: 使用注册表自动包装 fsspec 文件系统


.. important::

    如果使用异步 fsspec 文件系统，应始终使用 ``asynchronous=True`` 构造它，**而不** 传递 ``loop``，以便 Litestar 可以使用它们的原生异步函数。

    .. seealso::
        https://filesystem-spec.readthedocs.io/en/latest/async.html#using-from-async



适配支持符号链接的文件系统
+++++++++++++++++++++++++++++++++++++++++++

处理符号链接可能很棘手。为了确保 Litestar 始终做正确的事情，确实支持符号链接的现有文件系统可以注册为"可链接的"，而无需实现 :class:`~litestar.file_system.LinkableFileSystem`。

要将文件系统注册为可链接的，可以使用 :meth:`~litestar.file_system.LinkableFileSystem.register_as_linkable` 注册类型和解析此文件系统上符号链接的函数。

.. literalinclude:: /examples/file_systems/register_linkable.py
    :language: python

.. tip::

    默认情况下，:class:`fsspec.implementations.local.LocalFileSystem` 已经注册为可链接的文件系统


注册表
--------

为了更轻松的配置和测试，可以使用 :class:`~litestar.file_system.FileSystemRegistry` 在名称下注册文件系统，以便以后引用。

.. literalinclude:: /examples/file_systems/registry.py
    :language: python
    :caption: 使用注册表从 S3 发送文件


.. tip::
    添加 fsspec 文件系统时，它将自动被包装以与 :class:`~litestar.file_system.BaseFileSystem` 兼容。


:class:`~litestar.file_system.FileSystemRegistry` 实现为插件，除非显式传递其实例给应用程序，否则会自动设置。

如果需要，可以像访问任何其他插件一样访问注册表：

.. literalinclude:: /examples/file_systems/registry_access.py
    :language: python
    :caption: 访问注册表


设置默认文件系统
+++++++++++++++++++++++++++++

对于涉及发送文件的操作，如果没有显式传递文件系统，Litestar 将使用注册表中定义的默认文件系统。它默认为 :class:`~litestar.file_system.BaseLocalFileSystem`，但可以配置为任何受支持的文件系统。

.. literalinclude:: /examples/file_systems/registry_default.py
    :language: python
    :caption: 更改默认文件系统
