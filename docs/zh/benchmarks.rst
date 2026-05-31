基准测试
==========

方法论
-----------

- 基准测试使用 `bombardier <https://github.com/codesenberg/bombardier>`__ 基准测试工具完成。
- 基准测试在专用机器上运行，基础安装为 Debian 11。
- 每个框架都包含在自己的 docker 容器中，在专用的 CPU 核心上运行（使用 ``cset shield`` 命令和 docker 的 ``--cpuset-cpus`` 选项）。
- 框架的测试编写方式使其在完成相同任务时尽可能具有可比性（你可以在 `此处 <https://github.com/litestar-org/api-performance-tests/tree/main/frameworks>`__ 查看它们）。
- 每个应用程序都使用 `uvicorn <https://www.uvicorn.org/>`__ 运行，并配置 **一个工作进程** 和 `uvloop <https://uvloop.readthedocs.io/>`__。
- 测试数据是随机生成的，并从共享模块导入。
- 所有框架都使用其“原生”配置，即不应用任何额外的优化。所有测试都根据各自的官方文档编写，并应用了其中展示的最佳实践。

结果
-------

..  note::
    如果某个特定框架的结果缺失，则表示

    - 该框架不支持此功能（这将在测试说明中提及）
    - 超过 0.1% 的响应被丢弃

JSON
~~~~

将字典序列化为 JSON

.. figure:: /images/benchmarks/rps_json.svg
   :alt: RPS JSON

   RPS JSON

.. note::
   
   以上基准测试仅供参考，实际性能可能因具体使用场景而异。
    由于所有框架都使用其“原生”配置，Litestar 将通过 `msgspec <https://jcristharif.com/msgspec/>`_ 运行数据，而 FastAPI 将通过 `Pydantic <https://docs.pydantic.dev/latest/>`_ 运行数据。


序列化
~~~~~~~~~~~~~

将 Pydantic 模型和数据类序列化为 JSON

.. figure:: /images/benchmarks/rps_serialization.svg
   :alt: RPS 序列化 Pydantic 模型和数据类为 JSON

   RPS 序列化 Pydantic 模型和数据类为 JSON


文件
~~~~~

.. figure:: /images/benchmarks/rps_files.svg
   :alt: RPS 文件

   RPS 文件

.. note::
   
   以上基准测试仅供参考，实际性能可能因具体使用场景而异。
    Sanic 和 Quart 不支持或仅部分支持同步文件响应。


路径和查询参数处理
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*所有响应均返回“无内容”*

-  无参数：无路径参数
-  路径参数：单个路径参数，强制转换为整数
-  查询参数：单个查询参数，强制转换为整数
-  混合参数：一个路径参数和一个查询参数，均强制转换为整数

.. figure:: images/benchmarks/rps_params.svg
   :alt: RPS 路径和查询参数

   RPS 路径和查询参数

依赖注入
~~~~~~~~~~~~~~~~~~~~

-  解析 3 个嵌套的同步依赖项
-  解析 3 个嵌套的异步依赖项（仅 ``Litestar`` 和 ``FastAPI`` 支持）
-  解析 3 个嵌套的同步依赖项和 3 个嵌套的异步依赖项（仅 ``Litestar`` 和 ``FastAPI`` 支持）

.. figure:: /images/benchmarks/rps_dependency-injection.svg
   :alt: RPS 依赖注入

   RPS 依赖注入


.. note::
   
   以上基准测试仅供参考，实际性能可能因具体使用场景而异。
