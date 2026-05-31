=========
基本使用
=========

这里我们演示如何为路由处理器声明 DTO 类型。出于演示目的，我们假设我们正在使用数据模型 ``User``，
并且已经在应用程序中创建了两个 DTO 类型：``UserDTO`` 和 ``UserReturnDTO``。

DTO 层参数
~~~~~~~~~~

在 Litestar 应用程序的每个 :ref:`层 <layered-architecture>` 上，
有两个参数控制负责从处理器接收和返回数据的 DTO：

- ``dto``：此参数描述将用于解析入站数据的 DTO，该数据将作为处理器的 ``data`` 关键字参数注入。
  此外，如果处理器上没有声明 ``return_dto``，这也将用于编码处理器的返回数据。
- ``return_dto``：此参数描述将用于编码从处理器返回的数据的 DTO。
  如果未提供，则使用 ``dto`` 参数描述的 DTO。

提供给这两个参数的对象必须是符合 
:class:`AbstractDTO <litestar.dto.base_dto.AbstractDTO>` 协议的类。

在处理器上定义 DTO
~~~~~~~~~~~~~~~~~~

``dto`` 参数
-------------

.. literalinclude:: /examples/data_transfer_objects/the_dto_parameter.py
    :caption: 使用 ``dto`` 参数
    :language: python

在此示例中，``UserDTO`` 执行将客户端数据解码为 ``User`` 类型，
并将返回的 ``User`` 实例编码为 Litestar 可以编码为字节的类型。

``return_dto`` 参数
-------------------

.. literalinclude:: /examples/data_transfer_objects/the_return_dto_parameter.py
    :caption: 使用 ``return_dto`` 参数
    :language: python

在此示例中，``UserDTO`` 执行将客户端数据解码为 ``User`` 类型，
``UserReturnDTO`` 负责将 ``User`` 实例转换为 Litestar 可以编码为字节的类型。

覆盖隐式 ``return_dto``
-----------------------

如果没有为处理器声明 ``return_dto`` 类型，
则为 ``dto`` 参数声明的类型将用于解码和编码请求和响应数据。
如果此行为不理想，可以通过将 ``return_dto`` 显式设置为 ``None`` 来禁用它。

.. literalinclude:: /examples/data_transfer_objects/overriding_implicit_return_dto.py
    :caption: 禁用隐式 ``return_dto`` 行为
    :language: python

在此示例中，我们使用 ``UserDTO`` 解码请求数据并将其转换为 ``User`` 类型，
但我们想自己管理响应数据的编码，因此我们显式声明 ``return_dto`` 为 ``None``。

在层上定义 DTO
~~~~~~~~~~~~~~

DTO 可以在应用程序的任何 :ref:`层 <layered-architecture>` 上定义。
应用的 DTO 类型是在所有权链中定义的、最接近相关处理器的类型。

.. literalinclude:: /examples/data_transfer_objects/defining_dtos_on_layers.py
    :caption: 在 Controller 上定义 DTO
    :language: python

在此示例中，任何声明了 ``data`` 关键字参数的处理器接收到的 ``User`` 实例，
都由 ``UserDTO`` 类型转换，所有处理器返回值都由 ``UserReturnDTO`` 转换为可编码类型
（``delete()`` 路由除外，该路由禁用了 ``return_dto``）。

DTO 同样可以在 :class:`路由器 <litestar.router.Router>` 和
:class:`应用程序本身 <litestar.app.Litestar>` 上定义。


使用 codegen 后端提高性能
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

    此功能在 ``2.2.0`` 中引入，隐藏在 ``DTO_CODEGEN`` 功能标志后面。
    从 ``2.8.0`` 开始，它被认为是稳定的并默认启用。
    仍然可以通过使用 ``DTOConfig(experimental_codegen_backend=False)`` 覆盖选择性地禁用它。

DTO 后端是为所有 DTO 功能执行繁重工作的部分。它负责转换、验证和解析。
因此，它也是对性能影响最大的部分。为了减少 DTO 引入的开销，引入了 DTO codegen 后端；
这是一个通过在运行时生成优化的 Python 代码来执行所有必要操作以提高效率的 DTO 后端。

禁用后端
--------

你可以使用 ``experimental_codegen_backend=False`` 选择性地禁用 codegen 后端：

.. code-block:: python

    from dataclasses import dataclass
    from litestar.dto import DTOConfig, DataclassDTO


    @dataclass
    class Foo:
        name: str


    class FooDTO(DataclassDTO[Foo]):
        config = DTOConfig(experimental_codegen_backend=False)

启用后端
--------

.. note:: 这是针对 Litestar 2.8.0 之前版本的历史文档
    从 2.8.0 开始，此后端默认启用

.. warning:: ``ExperimentalFeatures.DTO_CODEGEN`` 已弃用，将在 3.0.0 中移除

.. dropdown:: 启用 DTO codegen 后端
    :icon: git-pull-request-closed

    你可以通过向 Litestar 应用程序传递适当的功能标志来为所有 DTO 全局启用此后端：

    .. code-block:: python

        from litestar import Litestar
        from litestar.config.app import ExperimentalFeatures

        app = Litestar(experimental_features=[ExperimentalFeatures.DTO_CODEGEN])


    或者为单个 DTO 选择性地启用：

    .. code-block:: python

        from dataclasses import dataclass
        from litestar.dto import DTOConfig, DataclassDTO


        @dataclass
        class Foo:
            name: str


        class FooDTO(DataclassDTO[Foo]):
            config = DTOConfig(experimental_codegen_backend=True)

    同样的标志可用于选择性地禁用后端：

    .. code-block:: python

        from dataclasses import dataclass
        from litestar.dto import DTOConfig, DataclassDTO


        @dataclass
        class Foo:
            name: str


        class FooDTO(DataclassDTO[Foo]):
            config = DTOConfig(experimental_codegen_backend=False)


性能改进
--------

这是一些显示某些操作性能提升的初步数据：

=================================== ===========
操作                                 提升
=================================== ===========
JSON 转 Python                      ~2.5x
JSON 转 Python（集合）               ~3.5x
Python 转 Python                    ~2.5x
Python 转 Python（集合）             ~5x
Python 转 JSON                      ~5.3x
Python 转 JSON（集合）               ~5.4x
=================================== ===========


.. seealso::
    如果你对技术细节感兴趣，请查看
    https://github.com/litestar-org/litestar/pull/2388
