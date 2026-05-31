===========
AbstractDTO
===========

Litestar 维护一套 DTO 工厂类型，可用于为流行的数据建模库（如 ORM）创建 DTO。
这些工厂以模型类型作为泛型类型参数，并创建 
:class:`AbstractDTO <litestar.dto.base_dto.AbstractDTO>` 的子类型，
支持该模型类型与原始字节之间的转换。

以下工厂目前可用：

- :class:`DataclassDTO <litestar.dto.dataclass_dto.DataclassDTO>`
- :class:`MsgspecDTO <litestar.dto.msgspec_dto.MsgspecDTO>`
- :class:`PydanticDTO <litestar.plugins.pydantic.PydanticDTO>`
- :class:`SQLAlchemyDTO <advanced_alchemy.extensions.litestar.dto.SQLAlchemyDTO>`

使用 DTO 工厂
-------------

DTO 工厂用于为特定的数据建模库创建 DTO。以下示例为 SQLAlchemy 模型创建 DTO：

.. literalinclude:: /examples/data_transfer_objects/factory/simple_dto_factory_example.py
    :caption: SQLAlchemy 模型 DTO
    :language: python

这里我们看到 SQLAlchemy 模型被用作处理器的 ``data`` 和返回注解，
然而，在上述示例中我们确实存在一些问题。首先，用户的密码已在处理器的响应中返回给他们。其次，用户能够设置模型上的 ``created_at`` 字段，而该字段应该只设置一次，并在内部定义。

让我们探讨如何配置 DTO 来管理这样的场景。

.. _dto-marking-fields:

标记字段
--------

:func:`dto_field <litestar.dto.field.dto_field>` 函数可用于标记具有基于 DTO 配置的模型属性。

标记为 ``"private"`` 或 ``"read-only"`` 的字段不会从客户端数据解析到用户模型中，
``"private"`` 字段永远不会序列化到返回数据中。

.. literalinclude:: /examples/data_transfer_objects/factory/marking_fields.py
    :caption: 标记字段
    :language: python
    :emphasize-lines: 6,14,15
    :linenos:

请注意，``id`` 字段是主键，由定义的 SQLAlchemy 基类特殊处理。

.. note::

    "标记"模型字段的过程会根据库而有所不同。例如，
    :class:`DataclassDTO <.dto.DataclassDTO>` 期望标记在 ``dataclasses.field`` 的 ``metadata`` 参数中进行。

排除字段
--------

可以使用 :class:`DTOConfig <litestar.dto.config.DTOConfig>` 显式排除字段。

以下示例演示从序列化响应中排除属性，包括从嵌套模型中排除字段。

.. literalinclude:: /examples/data_transfer_objects/factory/excluding_fields.py
    :caption: 排除字段
    :language: python
    :emphasize-lines: 6,10,37-46,49
    :linenos:

这里，配置使用 exclude 参数创建，它是一组字符串。每个字符串表示应从输出 DTO 中排除的 ``User`` 对象中字段的路径。

.. code-block:: python

    config = DTOConfig(
        exclude={
            "id",
            "address.id",
            "address.street",
            "pets.0.id",
            "pets.0.user_id",
        }
    )

在此示例中，``"id"`` 表示 ``User`` 对象的 id 字段，``"address.id"`` 和 ``"address.street"`` 表示嵌套在 ``User`` 对象内的 ``Address`` 对象的字段，``"pets.0.id"`` 和 ``"pets.0.user_id"`` 表示嵌套在 ``User.pets`` 列表中的 ``Pets`` 对象的字段。

.. note::

    给定一个泛型类型，具有任意数量的类型参数（例如 ``GenericType[Type0, Type1, ..., TypeN]``），
    我们使用类型参数的索引来指示排除应引用哪个类型。例如，``a.0.b`` 从 ``a`` 的第一个类型参数中排除 ``b`` 字段，``a.1.b`` 从 ``a`` 的第二个类型参数中排除 ``b`` 字段，依此类推。

重命名字段
----------

可以使用 :class:`DTOConfig <litestar.dto.config.DTOConfig>` 重命名字段。
以下示例在客户端使用名称 ``userName``，在内部使用 ``user``。

.. literalinclude:: /examples/data_transfer_objects/factory/renaming_fields.py
    :caption: 重命名字段
    :language: python
    :emphasize-lines: 4,8,19,20,24
    :linenos:

也可以使用将应用于所有字段的重命名策略来重命名字段。
以下示例使用预定义的重命名策略，该策略将所有字段名称转换为客户端的驼峰命名。

.. literalinclude:: /examples/data_transfer_objects/factory/renaming_all_fields.py
    :caption: 重命名所有字段
    :language: python
    :emphasize-lines: 4,8,19,20,21,22,24
    :linenos:

使用 `rename_fields` 映射直接重命名的字段将从 `rename_strategy` 中排除。

重命名策略接受预定义策略之一："camel"、"pascal"、"upper"、"lower"、"kebab"，
或者可以提供接受字段名称作为字符串参数并应返回字符串的回调。

类型检查
--------

工厂检查分配给它们的类型是否是作为泛型类型提供给 DTO 工厂的类型的子类。这意味着如果您有一个接受 ``User`` 模型的处理器，并且您为其分配了 ``UserDTO`` 工厂，那么 DTO 将只接受 ``User`` 类型的 "data" 和返回类型。

.. literalinclude:: /examples/data_transfer_objects/factory/type_checking.py
    :caption: 类型检查
    :language: python
    :emphasize-lines: 25,26,31
    :linenos:

在上面的示例中，处理器被声明使用 ``UserDTO``，它已使用 ``User`` 类型缩小。但是，我们使用 ``Foo`` 类型注释处理器。这将在运行时引发如下错误：

    litestar.exceptions.dto.InvalidAnnotationException: DTO narrowed with
    '<class 'docs.examples.data_transfer_objects.factory.type_checking.User'>', handler type is
    '<class 'docs.examples.data_transfer_objects.factory.type_checking.Foo'>'

嵌套字段
--------

可以使用 :class:`DTOConfig <litestar.dto.config.DTOConfig>` 的 ``max_nested_depth`` 参数
控制从客户端数据解析和序列化到返回数据的相关项的深度。

在此示例中，我们为处理入站客户端数据的 DTO 设置 ``max_nested_depth=0``，并将其保留为返回 DTO 的默认值 ``1``。

.. literalinclude:: /examples/data_transfer_objects/factory/related_items.py
    :caption: 相关项
    :language: python
    :emphasize-lines: 25,35,39
    :linenos:

当处理器接收客户端数据时，我们可以看到 ``b`` 字段尚未解析到为我们的 data 参数注入的 ``A`` 模型中（第 35 行）。

然后我们向数据添加一个 ``B`` 实例（第 39 行），其中包括对 ``a`` 的反向引用，从检查返回数据可以看到 ``b`` 包含在响应数据中，但是 ``b.a`` 不包含，这是由于默认的 ``max_nested_depth`` 为 ``1``。

处理未知字段
------------

默认情况下，DTO 将静默忽略源数据中的未知字段。
可以使用 :class:`DTOConfig <litestar.dto.config.DTOConfig>` 的 ``forbid_unknown_fields`` 参数配置此行为。
设置为 ``True`` 时，如果数据包含模型上未定义的字段，将返回验证错误响应：

.. literalinclude:: /examples/data_transfer_objects/factory/unknown_fields.py
    :caption: 未知字段
    :language: python
    :linenos:


DTO Data
--------

有时我们需要能够访问 DTO 已解析和验证的数据，但不转换为数据模型的实例。

在以下示例中，我们创建一个 ``User`` 模型，它是一个具有 3 个必需字段的 :func:`dataclass <dataclasses.dataclass>`：``id``、``name`` 和 ``age``。

我们还创建了一个 DTO，不允许客户端在 ``User`` 模型上设置 ``id`` 字段，并在处理器上设置它。

.. literalinclude:: /examples/data_transfer_objects/factory/dto_data_problem_statement.py
    :language: python
    :emphasize-lines: 18-21,27
    :linenos:

请注意，我们的 ``User`` 模型为 ``id`` 字段有一个模型级别的 ``default_factory=uuid4``。这就是为什么我们可以将客户端数据解码到此模型中。

然而，在某些情况下，没有明确的方法以这种方式提供默认值。

处理此问题的一种方法是创建不同的模型，例如，我们可能创建一个没有 ``id`` 字段的 ``UserCreate`` 模型，并将客户端数据解码到其中。但是，当我们从客户端接受的数据有很多可变性时，例如 `PATCH <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PATCH>`_ 请求，这种方法可能会变得相当繁琐。

这就是 :class:`DTOData <litestar.dto.data_structures.DTOData>` 类的用武之地。它是一个泛型类，接受它将包含的数据类型，并提供用于与该数据交互的有用方法。

.. literalinclude:: /examples/data_transfer_objects/factory/dto_data_usage.py
    :language: python
    :emphasize-lines: 5,23,25
    :linenos:

在上面的示例中，我们将 :class:`DTOData <litestar.dto.data_structures.DTOData>` 的实例注入到处理器中，
并使用它在使用服务器生成的 ``id`` 值增强客户端数据后创建 ``User`` 实例。

有关可用方法的更多信息，请参阅 :class:`参考文档 <litestar.dto.data_structures.DTOData>`。

.. _dto-create-instance-nested-data:

为嵌套数据提供值
~~~~~~~~~~~~~~~~

要增强用于实例化模型实例的数据，我们可以向 
:meth:`create_instance() <litestar.dto.data_structures.DTOData.create_instance>` 方法提供关键字参数。

有时我们需要为嵌套数据提供值，例如，在创建具有排除字段的嵌套模型的模型的新实例时。

.. literalinclude:: /examples/data_transfer_objects/factory/providing_values_for_nested_data.py
    :language: python
    :emphasize-lines: 9-12,20,28,34
    :linenos:

双下划线语法 ``address__id`` 作为关键字参数传递给 
:meth:`create_instance() <litestar.dto.data_structures.DTOData.create_instance>` 方法调用，
用于为嵌套属性指定值。在这种情况下，它用于为嵌套在 ``Person`` 实例中的 ``Address`` 实例的 ``id`` 属性提供值。

这是 Python 中处理嵌套结构的常见约定。双下划线可以解释为"遍历"，因此 ``address__id`` 意味着"遍历 address 以获取其 id"。

在此脚本的上下文中，``create_instance(id=1, address__id=2)`` 的意思是"从客户端数据创建一个新的 ``Person`` 实例，给定 id 为 ``1``，并用 id 为 ``2`` 补充客户端地址数据"。

DTO 工厂和 PATCH 请求
----------------------

`PATCH <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PATCH>`_ 请求是数据传输对象的特殊情况。
原因是我们需要能够接受和验证客户端有效负载中模型属性的任何子集，这需要一些特殊的内部处理。

.. literalinclude:: /examples/data_transfer_objects/factory/patch_requests.py
    :language: python
    :emphasize-lines: 7,20,27,28,30
    :linenos:

``PatchDTO`` 类为 ``Person`` 类定义。``PatchDTO`` 的 ``config`` 属性设置为排除 ``id`` 字段，防止客户端在更新 person 时设置它，``partial`` 属性设置为 ``True``，
这允许 DTO 接受模型属性的子集。

在处理器内部，调用 :meth:`DTOData.update_instance <litestar.dto.data_structures.DTOData.update_instance>` 方法在返回之前更新 ``Person`` 的实例。

在我们的请求中，我们只更新 ``Person`` 的 ``name`` 属性，从 ``"Peter"`` 更新为 ``"Peter Pan"``，并在响应中接收完整对象 - 具有修改后的名称。

隐式私有字段
------------

以下划线开头命名的字段默认被视为"私有"。
这意味着它们不会从客户端数据解析，也不会序列化到返回数据中。

.. literalinclude:: /examples/data_transfer_objects/factory/leading_underscore_private.py
    :language: python
    :linenos:

可以通过将 
:attr:`DTOConfig.underscore_fields_private <litestar.dto.config.DTOConfig.underscore_fields_private>` 
属性设置为 ``False`` 来覆盖此行为。

.. literalinclude:: /examples/data_transfer_objects/factory/leading_underscore_private_override.py
    :language: python
    :linenos:
    :emphasize-lines: 14,15

包装返回数据
------------

Litestar 的 DTO 工厂类型足够通用，可以管理您的数据，即使它嵌套在泛型包装器中。

以下示例演示了一个路由处理器，它返回包装在泛型类型中的 DTO 管理数据。包装器用于传递有关响应的附加元数据 - 在这种情况下，是返回的项数。继续阅读以了解如何自己执行此操作。

.. literalinclude:: /examples/data_transfer_objects/factory/enveloping_return_data.py
    :caption: 包装返回数据
    :language: python
    :linenos:

首先，创建一个泛型数据类作为您的包装器。此类型将包含您的数据和您可能需要的任何其他属性。在此示例中，我们有一个具有 ``count`` 属性的 ``WithCount`` 数据类。包装器必须是具有一个或多个类型参数的 python 泛型类型，并且这些类型参数中至少有一个应该描述将使用数据填充的实例属性。

.. code-block:: python

   from dataclasses import dataclass
   from typing import Generic, TypeVar

   T = TypeVar("T")


   @dataclass
   class WithCount(Generic[T]):
       count: int
       data: List[T]


现在，为您的数据对象创建一个 DTO 并使用 ``DTOConfig`` 对其进行配置。在此示例中，我们从最终输出中排除 ``password`` 和 ``created_at``。

.. code-block:: python

   from advanced_alchemy.dto import SQLAlchemyDTO
   from litestar.dto import DTOConfig


   class UserDTO(SQLAlchemyDTO[User]):
       config = DTOConfig(exclude={"password", "created_at"})

然后，设置您的路由处理器。此示例设置一个 ``/users`` 端点，其中返回包装在 ``WithCount`` 数据类中的 ``User`` 对象列表。

.. code-block:: python

   from litestar import get


   @get("/users", dto=UserDTO, sync_to_thread=False)
   def get_users() -> WithCount[User]:
       return WithCount(
           count=1,
           data=[
               User(
                   id=1,
                   name="Litestar User",
                   password="xyz",
                   created_at=datetime.now(),
               ),
           ],
       )


此设置允许 DTO 管理将 ``User`` 对象渲染到响应中。DTO 工厂类型将找到包装器类型上保存数据的属性，并对其执行序列化操作。

返回包装数据受以下约束：

#. 从处理器返回的类型必须是 Litestar 可以原生编码的类型。
#. 泛型包装器类型可以有多个类型参数，但必须恰好有一个类型参数是 DTO 支持的类型。

使用 Litestar 的分页类型
-------------------------

Litestar 提供分页响应包装器类型，DTO 工厂类型可以开箱即用地处理这一点。

.. literalinclude:: /examples/data_transfer_objects/factory/paginated_return_data.py
    :caption: 分页返回数据
    :language: python
    :linenos:

在我们的示例中，DTO 已定义和配置，我们从用户的最终表示中排除 ``password`` 和 ``created_at`` 字段。

.. code-block:: python

   from advanced_alchemy.dto import SQLAlchemyDTO
   from litestar.dto import DTOConfig


   class UserDTO(SQLAlchemyDTO[User]):
       config = DTOConfig(exclude={"password", "created_at"})

该示例设置了一个 ``/users`` 端点，其中返回包装在 :class:`ClassicPagination <.pagination.ClassicPagination>` 中的分页 ``User`` 对象列表。

.. code-block:: python

   from litestar import get
   from litestar.pagination import ClassicPagination


   @get("/users", dto=UserDTO, sync_to_thread=False)
   def get_users() -> ClassicPagination[User]:
       return ClassicPagination(
           page_size=10,
           total_pages=1,
           current_page=1,
           items=[
               User(
                   id=1,
                   name="Litestar User",
                   password="xyz",
                   created_at=datetime.now(),
               ),
           ],
       )

:class:`ClassicPagination <.pagination.ClassicPagination>` 类包含 ``page_size``（每页项数）、``total_pages``（总页数）、``current_page``（当前页码）和 ``items``（当前页的项）。

DTO 对包含在 ``items`` 属性中的数据进行操作，分页包装器由 Litestar 的序列化过程自动处理。

将 Litestar 的 Response 类型与 DTO 工厂一起使用
----------------------------------------------

Litestar 的 DTO（数据传输对象）工厂类型可以处理包装在 ``Response`` 类型中的数据。

.. literalinclude:: /examples/data_transfer_objects/factory/response_return_data.py
    :caption: Response 包装的返回数据
    :language: python
    :linenos:

我们为 ``User`` 类型创建一个 DTO，并使用 ``DTOConfig`` 对其进行配置，以从序列化输出中排除 ``password`` 和 ``created_at``。

.. code-block:: python

   from advanced_alchemy.dto import SQLAlchemyDTO
   from litestar.dto import DTOConfig


   class UserDTO(SQLAlchemyDTO[User]):
       config = DTOConfig(exclude={"password", "created_at"})


该示例设置了一个 ``/users`` 端点，其中返回包装在 ``Response`` 类型中的 ``User`` 对象。

.. code-block:: python

   from litestar import get, Response


   @get("/users", dto=UserDTO, sync_to_thread=False)
   def get_users() -> Response[User]:
       return Response(
           content=User(
               id=1,
               name="Litestar User",
               password="xyz",
               created_at=datetime.now(),
           ),
           headers={"X-Total-Count": "1"},
       )

``Response`` 对象将 ``User`` 对象封装在其 ``content`` 属性中，并允许我们配置客户端接收的响应。在这种情况下，我们添加一个自定义标头。
