CLI
===

.. |uvicorn| replace:: uvicorn
.. _uvicorn: https://www.uvicorn.org/

Litestar 提供了一个方便的命令行界面（CLI），用于运行和管理 Litestar 应用程序。CLI 由 `click <https://click.palletsprojects.com/>`_、`rich <https://rich.readthedocs.io>`_ 和 `rich-click <https://github.com/ewels/rich-click>`_ 提供支持。

启用所有 CLI 功能
-------------------------

CLI 及其硬依赖项默认包含在内。但是，如果您想运行应用程序（使用 ``litestar run``）或美化 ``litestar schema typescript`` 命令生成的 Typescript，则需要 |uvicorn|_ 和 `jsbeautifier <https://pypi.org/project/jsbeautifier/>`_。它们可以独立安装，但我们建议安装 ``standard`` 额外包，它方便地捆绑了常用的可选依赖项。

.. code-block:: shell
    :caption: 安装 standard 组

    pip install 'litestar[standard]'

安装 ``standard`` 后，您将可以访问 ``litestar run`` 命令。

自动发现
-------------

Litestar 提供对放置在名为 ``app`` 或 ``application`` 的规范模块中的应用程序和应用程序工厂的自动发现。这些模块可以是单个文件或目录。在这些模块或其子模块中，CLI 将检测 :class:`Litestar <.app.Litestar>` 的任何实例、名为 ``create_app`` 的可调用对象，或注释为返回 :class:`Litestar <.app.Litestar>` 实例的可调用对象。

自动发现按以下顺序查找这些位置：

1. ``app.py``
2. ``app/__init__.py``
3. ``app`` 的子模块
4. ``application.py``
5. ``application/__init__.py``
6. ``application`` 的子模块

在这些位置内，Litestar CLI 查找：

1. 名为 ``app`` 的 :term:`对象`，它是 :class:`~.app.Litestar` 的实例
2. 名为 ``application`` 的对象，它是 :class:`~.app.Litestar` 的实例
3. 任何 :class:`~.app.Litestar` 的实例对象
4. 名为 ``create_app`` 的 :term:`可调用对象 <callable>`
5. 注释为返回 :class:`~.app.Litestar` 实例的可调用对象

显式指定应用程序
------------------------------------

可以通过 ``--app`` 参数或 ``LITESTAR_APP`` 环境变量显式指定要使用的应用程序。两者的格式均为 ``<模块名>.<子模块>:<应用实例或工厂>``。

当同时设置 ``--app`` 和 ``LITESTAR_APP`` 时，CLI 选项优先于环境变量。


.. code-block:: bash
    :caption: 使用 'litestar run' 并通过 --app 指定应用程序工厂

    litestar --app=my_application.app:create_my_app run


.. code-block:: bash
    :caption: 使用 'litestar run' 并通过 LITESTAR_APP 指定应用程序工厂

    LITESTAR_APP=my_application.app:create_my_app litestar run



扩展 CLI
-----------------

Litestar 的 CLI 使用 `click <https://click.palletsprojects.com/>`_ 构建，可以通过使用 `入口点 <https://packaging.python.org/en/latest/specifications/entry-points/>`_ 或创建继承自 :class:`~.plugins.CLIPlugin` 的插件来扩展。

使用入口点
^^^^^^^^^^^^^^^^^^

可以在 ``litestar.commands`` 组下添加 CLI 的入口点。这些条目应指向 :class:`click.Command` 或 :class:`click.Group`：

.. tab-set::

    .. tab-item:: setup.py

        .. code-block:: python
            :caption: 使用 `setuptools <https://setuptools.pypa.io/en/latest/>`_

            from setuptools import setup

            setup(
               name="my-litestar-plugin",
               ...,
               entry_points={
                   "litestar.commands": ["my_command=my_litestar_plugin.cli:main"],
               },
            )

    .. tab-item:: pdm

        .. code-block:: toml
            :caption: 使用 `PDM <https://pdm.fming.dev/>`_

            [project.scripts]
            my_command = "my_litestar_plugin.cli:main"

            # 或者，作为入口点：

            [project.entry-points."litestar.commands"]
            my_command = "my_litestar_plugin.cli:main"

    .. tab-item:: poetry

        .. code-block:: toml
            :caption: 使用 `poetry <https://python-poetry.org/>`_

            [tool.poetry.plugins."litestar.commands"]
            my_command = "my_litestar_plugin.cli:main"

    .. tab-item:: uv

        .. code-block:: toml
            :caption: 使用 `uv <https://docs.astral.sh/uv/>`_

            [project.scripts]
            my_command = "my_litestar_plugin.cli:main"

使用插件
^^^^^^^^^^^^^^

可以使用 :class:`~.plugins.CLIPlugin` 创建扩展 CLI 的插件。其 :meth:`~.plugins.CLIPlugin.on_cli_init` 将在 CLI 初始化期间被调用，并接收根 :class:`click.Group` 作为其第一个参数，然后可以用于添加或覆盖命令：

.. code-block:: python
    :caption: 创建 CLI 插件

    from litestar import Litestar
    from litestar.plugins import CLIPlugin
    from click import Group


    class MyPlugin(CLIPlugin):
        def on_cli_init(self, cli: Group) -> None:
            @cli.command()
            def is_debug_mode(app: Litestar):
                print(app.debug)


    app = Litestar(plugins=[MyPlugin()])

访问应用实例
^^^^^^^^^^^^^^^^^^^^^^^^^^

在扩展 Litestar CLI 时，您很可能需要访问加载的 ``Litestar`` 实例。您可以通过向 CLI 函数添加特殊的 ``app`` 参数来实现这一点。这将导致 ``Litestar`` 实例在从 click-context 调用时被注入到函数中。

.. code-block:: python
    :caption: 以编程方式访问应用实例

    import click
    from litestar import Litestar


    @click.command()
    def my_command(app: Litestar) -> None: ...

使用 `server_lifespan` 钩子
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

服务器生命周期钩子提供了一种在 *服务器* 启动和停止之前和之后运行代码的方法。与常规的 `lifespan` 钩子相比，即使服务器启动多个工作进程，它们也只运行一次，而 `lifespan` 钩子会为每个单独的工作进程运行。

这使得它们适合应该恰好发生一次的任务，例如初始化数据库。

.. code-block:: python
    :caption: 使用 `server_lifespan` 钩子

    from contextlib import contextmanager
    from typing import Generator

    from litestar import Litestar
    from litestar.config.app import AppConfig
    from litestar.plugins.base import CLIPlugin


    class StartupPrintPlugin(CLIPlugin):

        @contextmanager
        def server_lifespan(self, app: Litestar) -> Generator[None, None, None]:
            print("i_run_before_startup_plugin")  # noqa: T201
            try:
                yield
            finally:
                print("i_run_after_shutdown_plugin")  # noqa: T201

    def create_app() -> Litestar:
        return Litestar(route_handlers=[], plugins=[StartupPrintPlugin()])


CLI 参考
-------------

Litestar CLI 的最新参考可以通过运行以下命令找到：

.. code-block:: shell
    :caption: 显示 CLI 帮助

    litestar --help

您还可以访问 :doc:`Litestar CLI Click API 参考 </reference/cli>` 以获取相同的信息。
