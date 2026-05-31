调试
=========

使用 Python 调试器
--------------------------

您可以配置 Litestar 在发生异常时进入 :doc:`Python 调试器 <python:library/pdb>`。这可以通过不同方式配置：

使用 ``pdb_on_exception`` 选项配置 ``Litestar``
    .. code-block:: python

        app = Litestar(pdb_on_exception=True)


使用 CLI 运行应用并使用 ``--pdb`` 标志
    .. code-block:: shell

        litestar run --pdb

使用 ``LITESTAR_PDB`` 环境变量
    ``LITESTAR_PDB=1``


使用 IDE 调试
---------------------

您可以轻松地将 IDE 的调试器附加到应用程序，无论您是通过 CLI 还是像 `uvicorn <https://www.uvicorn.org/>`_ 这样的 Web 服务器运行它。

Intellij / PyCharm
++++++++++++++++++

使用 CLI
*************

1. 通过 ``Run`` > ``Edit Configurations`` 创建新的调试配置
2. 选择 ``Module name`` 选项并将其设置为 ``litestar``
3. 添加 ``run`` 参数以及您想传递给 CLI 的其他可选参数

   .. image:: /images/debugging/pycharm-config-cli.png

4. 通过 ``Run`` > ``Debug Litestar`` 在调试器中运行应用程序

   .. image:: /images/debugging/pycharm-debug.png
        :align: center


.. important::
    与 ``--reload`` 和 ``--web-concurrency`` 参数一起使用时，路由处理程序内的断点可能无法正常工作。如果您想在使用这些选项的同时使用 CLI，可以通过 ``Run`` > ``Attach to process`` 手动将调试器附加到正在运行的 uvicorn 进程。


使用 uvicorn
*************

1. 通过 ``Run`` > ``Edit Configurations`` 创建新的调试配置
2. 选择 ``Module name`` 选项并将其设置为 ``uvicorn``
3. 添加 ``app:app`` 参数（或指向您的应用程序对象的等效路径）

   .. image:: /images/debugging/pycharm-config-uvicorn.png

4. 通过 ``Run`` > ``Debug Litestar`` 在调试器中运行应用程序

   .. image:: /images/debugging/pycharm-debug.png
        :align: center


VS Code
+++++++


使用 CLI
*************


1. 通过 ``Run`` > ``Add configuration`` 添加新的调试配置
    .. image:: /images/debugging/vs-code-add-config.png
        :align: center
2. 从 ``Select a debug configuration`` 对话框中选择 ``Module``
    .. image:: /images/debugging/vs-code-select-config.png
3. 输入 ``litestar`` 作为模块名称
    .. image:: /images/debugging/vs-code-config-litestar.png
4. 在打开的 JSON 文件中，按如下方式修改配置：
    .. code-block:: json

        {
            "name": "Python: Litestar app",
            "type": "python",
            "request": "launch",
            "module": "litestar",
            "justMyCode": true,
            "args": ["run"]
        }

5. 通过 ``Run`` > ``Start debugging`` 在调试器中运行应用程序
    .. image:: /images/debugging/vs-code-debug.png
        :align: center


使用 uvicorn
**************

1. 通过 ``Run`` > ``Add configuration`` 添加新的调试配置
    .. image:: /images/debugging/vs-code-add-config.png
        :align: center
2. 从 ``Select a debug configuration`` 对话框中选择 ``Module``
    .. image:: /images/debugging/vs-code-select-config.png
3. 输入 ``uvicorn`` 作为模块名称
    .. image:: /images/debugging/vs-code-config-litestar.png
4. 在打开的 JSON 文件中，按如下方式修改配置：
    .. code-block:: json

        {
            "name": "Python: Litestar app",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "justMyCode": true,
            "args": ["app:app"]
        }

5. 通过 ``Run`` > ``Start debugging`` 在调试器中运行应用程序
    .. image:: /images/debugging/vs-code-debug.png
        :align: center


自定义调试器
-------------------------

您可以使用 debug_module 选项配置 Litestar 以启用交互式调试。目前，它支持以下调试工具：`ipdb <https://github.com/gotcha/ipdb>`_、`PuDB <https://documen.tician.de/pudb/>`_ 和 `pdbr <https://github.com/cansarigol/pdbr>`_。也支持 `pdb++ <https://github.com/pdbpp/pdbpp>`_。默认值是 `pdb <https://docs.python.org/3/library/pdb.html>`_。

    .. code-block:: python

        import ipdb


        app = Litestar(pdb_on_exception=True, debugger_module=ipdb)
