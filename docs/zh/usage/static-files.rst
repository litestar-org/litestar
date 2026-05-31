静态文件
============

要提供静态文件（即从给定目录提供任意文件），可以使用 :func:`~litestar.static_files.create_static_files_router` 创建 :class:`Router <litestar.router.Router>` 来处理此任务。

.. literalinclude:: /examples/static_files/full_example.py
    :language: python
    :caption: 使用 :func:`create_static_files_router <litestar.static_files.create_static_files_router>` 提供静态文件

在此示例中，目录 ``assets`` 中的文件将在路径 ``/static`` 上提供服务。文件 ``assets/hello.txt`` 现在可在 ``/static/hello.txt`` 上访问

.. attention:: 目录被解释为相对于启动应用程序的工作目录


将文件作为附件发送
----------------------------

默认情况下，文件以"内联"方式发送，这意味着它们将具有 ``Content-Disposition: inline`` 头。

将 :paramref:`~litestar.static_files.create_static_files_router.params.send_as_attachment` 设置为 ``True`` 将改为使用 ``Content-Disposition: attachment`` 发送它们：

.. literalinclude:: /examples/static_files/send_as_attachment.py
    :language: python
    :caption: 使用 :func:`create_static_files_router` 的 :paramref:`~litestar.static_files.create_static_files_router.params.send_as_attachment` 参数将文件作为附件发送


HTML 模式
---------

可以通过将 :paramref:`~litestar.static_files.create_static_files_router.params.html_mode` 设置为 ``True`` 来启用"HTML 模式"。

这将：

- 当请求路径 ``/`` 时提供 ``/index.html``
- 当请求的文件未找到时尝试提供 ``/404.html``

.. literalinclude:: /examples/static_files/html_mode.py
    :language: python
    :caption: 使用 :func:`create_static_files_router` 的 :paramref:`~litestar.static_files.create_static_files_router.params.html_mode` 参数提供 HTML 文件


向生成的路由器传递选项
---------------------------------------

:class:`~litestar.router.Router` 上可用的选项可以直接传递给 :func:`~litestar.static_files.create_static_files_router`：

.. literalinclude:: /examples/static_files/passing_options.py
    :language: python
    :caption: 向 :func:`create_static_files_router` 生成的路由器传递选项


使用自定义路由器类
---------------------------

可以使用 :paramref:`~.static_files.create_static_files_router.params.router_class` 参数自定义使用的路由器类：

.. literalinclude:: /examples/static_files/custom_router.py
    :language: python
    :caption: 使用 :func:`create_static_files_router` 自定义路由器类


检索静态文件的路径
--------------------------------

可以使用 :meth:`~litestar.app.Litestar.route_reverse` 和 :meth:`~litestar.connection.ASGIConnection.url_for` 来检索特定文件的可用路径：

.. literalinclude:: /examples/static_files/route_reverse.py
    :language: python
    :caption: 使用 :meth:`~.app.Litestar.route_reverse` 检索静态文件的路径

.. tip:: ``name`` 参数必须与传递给 :func:`create_static_files_router` 的 ``name`` 参数匹配，默认值为 ``static``。


（远程）文件系统
---------------------

要自定义 Litestar 与文件系统的交互方式，可以将实现 :class:`~litestar.file_system.BaseFileSystem` 的类或任何 `fsspec <https://filesystem-spec.readthedocs.io/en/latest/>`_ 文件系统传递给 ``file_system``，提供 FTP、SFTP、Hadoop、SMB、GitHub 和 `许多其他 <https://filesystem-spec.readthedocs.io/en/latest/api.html#implementations>`_ 的集成，并通过第三方实现支持流行的云提供商，例如

- 通过 `S3FS <https://s3fs.readthedocs.io/en/latest/>`_ 支持 S3
- 通过 `GCSFS <https://gcsfs.readthedocs.io/en/latest/>`_ 支持 Google Cloud Storage
- 通过 `adlfs <https://github.com/fsspec/adlfs>`_ 支持 Azure Blob Storage

.. literalinclude:: /examples/static_files/file_system.py
    :language: python
    :caption: 使用 :func:`create_static_files_router` 自定义文件系统


处理符号链接
-----------------

本地文件系统（例如 Litestar 的 :class:`~litestar.file_system.BaseLocalFileSystem` 或 :class:`fsspec.implementations.local.LocalFileSystem`）可能支持符号链接，这可能导致意外行为。

``allow_symlinks_outside_directory`` 参数控制配置的基目录内的符号链接是否可以指向这些目录外的位置。默认情况下，此设置被禁用以确保严格的访问控制并防止意外暴露指定目录外的文件。

.. danger::

    除非绝对必要，否则保持此选项禁用（默认），以防止意外暴露预期目录外的文件。

    **只应在符号链接行为被充分理解的受控环境中启用。**


安全考虑
++++++++++++++++++++++++

启用此选项会引入潜在的安全风险，因为它可能允许访问不打算提供的文件。配置不当的符号链接可能允许遍历目录边界并暴露敏感信息。

只有在基目录中的所有符号链接都已知并确保有适当的文件系统权限以防止意外暴露时，才应启用此选项。


基于文件系统支持的行为
++++++++++++++++++++++++++++++++++++++

``allow_symlinks_outside_directory`` 的行为取决于底层文件系统的符号链接功能：

**不支持符号链接的文件系统**
  如果配置的 ``file_system`` 不继承自 :class:`LinkableFileSystem`，则将 ``allow_symlinks_outside_directory`` 设置为 ``None`` 以外的任何值将引发 :exc:`TypeError`。这确保不受支持的文件系统不会无意中允许符号链接遍历。

**支持符号链接的文件系统**
  如果文件系统支持符号链接，则默认值为 ``False``。这意味着，除非明确启用，否则符号链接将被限制在定义的基目录内的路径。


.. seealso::

    :ref:`usage/file_systems:Adapting file systems that support symlinks`
