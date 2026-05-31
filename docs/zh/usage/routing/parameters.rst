===========
参数
===========

路径参数
--------

路径 :term:`参数 <parameter>` 是在 URL 的 ``path`` 组件中声明的参数。
它们使用简单的语法 ``{param_name:param_type}`` 声明：

.. literalinclude:: /examples/parameters/path_parameters_1.py
    :language: python
    :caption: 在路由处理器中定义路径参数

在上面的示例中有两个组成部分：

1. 路径 :term:`参数 <parameter>` 在 :class:`@get() <.handlers.get>` :term:`装饰器 <decorator>` 中定义，
   它声明了参数的名称（``user_id``）和类型（:class:`int`）。
2. :term:`被装饰 <decorator>` 的函数 ``get_user`` 定义了一个与 ``path`` :term:`关键字参数 <argument>` 中
   定义的参数同名的参数。

参数名称的关联确保了路径参数的值将在函数被调用时注入到函数中。

支持的路径参数类型
~~~~~~~~~~~~~~~~~~

目前支持以下类型：

* ``date``: 接受日期字符串和时间戳。
* ``datetime``: 接受日期时间字符串和时间戳。
* ``decimal``: 接受十进制值和浮点数。
* :class:`float`: 接受整数和浮点数。
* :class:`int`: 接受整数和浮点数。
* :class:`path`: 接受有效的 POSIX 路径。
* :class:`str`: 接受所有字符串值。
* ``time``: 接受带有可选时区的时间字符串，兼容标准（Pydantic/Msgspec）日期时间格式。
* ``timedelta``: 接受与标准（Pydantic/Msgspec）timedelta 格式兼容的持续时间字符串。
* ``uuid``: 接受所有 uuid 值。

路径 :term:`参数 <parameter>` 中声明的类型和函数中的类型不需要 1:1 匹配 - 只要函数声明中的参数
使用"更高"的类型进行类型注解，低级类型可以强制转换为该类型，这就可以。例如，考虑这个：

.. literalinclude:: /examples/parameters/path_parameters_2.py
    :language: python
    :caption: 将路径参数强制转换为不同类型

在 ``path`` :term:`关键字参数 <argument>` 中定义的 :term:`参数 <parameter>` 被类型注解为 :class:`int`，
因为作为请求的一部分传递的值将是以毫秒为单位的时间戳，没有任何小数。
但是函数声明中的参数被类型注解为 :class:`datetime.datetime`。

这是可行的，因为 int 值将自动从 :class:`int` 强制转换为 :class:`~datetime.datetime`。

因此，当函数被调用时，它将使用 :class:`~datetime.datetime` 类型的参数调用。

.. note:: 只有在函数内部实际使用 :term:`参数 <parameter>` 时，才需要在函数声明中定义它。
    如果路径参数是路径的一部分，但函数不使用它，可以省略它。
    它仍然会被验证并正确添加到 OpenAPI 模式中。

Parameter 函数
--------------

:func:`~.params.Parameter` 是一个辅助函数，用于包装一个 :term:`参数 <parameter>`，
并添加额外的信息到 OpenAPI 模式中。

路径参数的额外验证和文档
~~~~~~~~~~~~~~~~~~~~~~~~

如果您想为给定的路径 :term:`参数 <parameter>` 添加验证或增强生成的 OpenAPI 文档，
可以使用 `the parameter function`_：

.. literalinclude:: /examples/parameters/path_parameters_3.py
    :language: python
    :caption: 为路径参数添加额外的验证和文档

在上面的示例中，:func:`~.params.Parameter` 用于将 :paramref:`~.params.Parameter.version` 的值
限制在 1 到 10 之间，然后设置 OpenAPI 模式的 :paramref:`~.params.Parameter.title`、
:paramref:`~.params.Parameter.description`、:paramref:`~.params.Parameter.examples` 和
:paramref:`externalDocs <.params.Parameter.external_docs>` 部分。

查询参数
--------

查询 :term:`参数 <parameter>` 被定义为处理器函数的 :term:`关键字参数 <argument>`。
每个未另外指定的 :term:`关键字参数 <argument>`（例如作为 :ref:`路径参数 <usage/routing/parameters:path parameters>`）
将被解释为查询参数。

.. literalinclude:: /examples/parameters/query_params.py
    :language: python
    :caption: 在路由处理器中定义查询参数

.. admonition:: 技术细节
    :class: info

    这些 :term:`参数 <parameter>` 将从函数签名中解析，并用于生成内部数据模型。
    这个模型将用于验证参数并生成 OpenAPI 模式。

    这种能力允许您使用任意数量的模式/建模库，包括 Pydantic、Msgspec、Attrs 和 Dataclasses，
    它将遵循与这些库相同的验证和解析方式。

查询 :term:`参数 <parameter>` 有三种基本类型：

- 必需
- 带有默认值的必需
- 带有默认值的可选

查询参数默认是 **必需的**。如果这样的参数没有值，
将引发 :exc:`~.exceptions.http_exceptions.ValidationException`。

默认值
~~~~~~

在此示例中，如果请求中未指定 ``param``，它将具有值 ``"hello"``。
但是，如果它作为查询 :term:`参数 <parameter>` 传递，它将被覆盖：

.. literalinclude:: /examples/parameters/query_params_default.py
    :language: python
    :caption: 为查询参数定义默认值

可选 :term:`参数 <parameter>`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

除了只设置默认值外，还可以使查询参数完全可选。

在这里，我们给出了默认值 ``None``，但仍然将查询参数的类型声明为 :class:`字符串 <str>`。
这意味着此参数不是必需的。

如果给出，它必须是 :class:`字符串 <str>`。
如果未给出，它将具有默认值 ``None``

.. literalinclude:: /examples/parameters/query_params_optional.py
    :language: python
    :caption: 定义可选查询参数

类型强制转换
------------

可以将查询 :term:`参数 <parameter>` 强制转换为不同的类型。
查询参数最初是 :class:`字符串 <str>`，但其值可以解析为各种类型。

.. literalinclude:: /examples/parameters/query_params_types.py
    :language: python
    :caption: 将查询参数强制转换为不同类型

替代名称和约束
--------------

有时您可能希望"重新映射"查询 :term:`参数 <parameter>`，以允许 URL 中的名称与
处理器函数中使用的名称不同。这可以通过使用 :func:`~.params.Parameter` 来完成。

.. literalinclude:: /examples/parameters/query_params_remap.py
    :language: python
    :caption: 将查询参数重新映射到不同的名称

在这里，我们从处理器函数中的 ``snake_case`` 重新映射到 URL 中的 ``camelCase``。
这意味着对于 URL ``http://127.0.0.1:8000?camelCase=foo``，``camelCase`` 的值
将用于 ``snake_case`` 参数的值。

:func:`~.params.Parameter` 还允许我们定义额外的约束：

.. literalinclude:: /examples/parameters/query_params_constraints.py
    :language: python
    :caption: 查询参数的约束

在这种情况下，``param`` 被验证为 *大于 5 的整数*。

记录枚举查询参数
----------------

默认情况下，为枚举查询 :term:`参数 <parameter>` 生成的 OpenAPI 模式使用枚举的 docstring
作为模式的描述部分。描述可以使用 `the parameter function`_ 的 :paramref:`~.params.Parameter.description`
参数更改，但这样做可能会覆盖同一枚举的其他查询参数的描述，因为每个枚举只生成一个模式。
可以通过使用 :paramref:`~.params.Parameter.schema_component_key` 参数来避免这种情况，
以便生成单独的模式：

.. literalinclude:: /examples/parameters/query_params_enum.py
    :language: python
    :caption: 具有相同枚举类型和不同描述的查询参数

在上面的示例中，``q1`` 查询参数的模式引用了一个"q1"模式组件，描述为"This is q1"。
``q2`` 查询参数的模式引用了一个"MyEnum"模式组件，描述为"My enum accepts two values"。
``q3`` 查询参数的模式引用了一个"q3"模式组件，描述为"This is q3"。

如果我们没有为 ``q1`` 和 ``q3`` 的 :func:`~.params.Parameter` 传递
:paramref:`~.params.Parameter.schema_component_key` 参数，
那么所有三个查询参数的模式都将引用同一个"MyEnum"模式组件，描述为"This is q1"。

Header 和 Cookie 参数
---------------------

与 *Query* :term:`参数 <parameter>` 不同，*Header* 和 *Cookie* 参数必须使用
`the parameter function`_ 声明，例如：

.. literalinclude:: /examples/parameters/header_and_cookie_parameters.py
    :language: python
    :caption: 定义 header 和 cookie 参数

如上所示，header 参数使用 ``header`` :term:`关键字参数 <argument>` 声明，
cookie 参数使用 ``cookie`` :term:`关键字参数 <argument>` 声明。
除了这个区别外，它们的工作方式与查询参数相同。

分层参数
--------

作为 Litestar :ref:`分层架构 <usage/applications:layered architecture>` 的一部分，
您不仅可以在单个路由处理器函数中声明 :term:`参数 <parameter>`，
还可以在应用程序的其他层上声明：

.. literalinclude:: /examples/parameters/layered_parameters.py
    :language: python
    :caption: 在应用程序的不同层上声明参数

在上面的示例中，除了在路由处理器中声明的参数外，我们还在 :class:`Litestar 应用 <.app.Litestar>`、
:class:`路由器 <.router.Router>` 和 :class:`控制器 <.controller.Controller>` 层上声明了
:term:`参数 <parameter>`。现在，更仔细地检查这些。

* ``app_param`` 是一个具有键 ``special-cookie`` 的 cookie 参数。我们通过将 :class:`str`
  作为参数传递给 :func:`~.params.Parameter` 函数来为其设置类型。
  这是我们在 OpenAPI 文档中获得类型所必需的。此外，假设此参数是必需的，
  因为它没有在 :paramref:`~.params.Parameter.required` 上显式设置为 ``False``。

  这很重要，因为路由处理器函数根本没有声明一个名为 ``app_param`` 的参数，
  但它仍然要求将此参数作为请求的一部分发送，否则验证将失败。

* ``router_param`` 是一个具有键 ``MyHeader`` 的 header 参数。
  因为它在 :paramref:`~.params.Parameter.required` 上设置为 ``False``，
  如果不存在，它将不会失败验证，除非路由处理器显式声明它 - 在这种情况下就是这样。

  因此，对于声明它为 :class:`str` 而不是 ``str | None`` 的路由器处理器函数，它实际上是必需的。
  如果提供了 :class:`字符串 <str>` 值，它将针对提供的正则表达式进行测试。
* ``controller_param`` 是一个具有键 ``controller_param`` 的查询参数。
  它在控制器上定义了 :paramref:`~.params.Parameter.lt` 设置为 ``100``，
  这意味着提供的值必须小于 100。

  但是路由处理器重新声明它，将 :paramref:`~.params.Parameter.lt` 设置为 ``50``，
  这意味着对于路由处理器，此值必须小于 50。
* ``local_param`` 是路由处理器本地的 :ref:`查询参数 <usage/routing/parameters:query parameters>`，
  ``path_param`` 是 :ref:`路径参数 <usage/routing/parameters:path parameters>`。

.. note:: 您不能在不同的应用程序层中声明路径 :term:`参数 <parameter>`。
    原因是为了确保简单性 - 否则参数解析变得非常难以正确完成。
