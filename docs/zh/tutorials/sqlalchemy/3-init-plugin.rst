使用初始化插件
---------------------

在我们的示例应用程序中,我们已经看到我们需要在应用程序的生命周期范围内管理数据库引擎,并在请求范围内管理会话。这是一个常见的模式,:class:`SQLAlchemyInitPlugin <advanced_alchemy.extensions.litestar.plugins.SQLAlchemyInitPlugin>` 插件为此提供了帮助。

在我们的最新更新中,我们利用了插件的两个特性:

1. 插件将自动为我们创建数据库引擎,并在应用程序的生命周期范围内管理它。
2. 插件将自动为我们创建数据库会话,并在请求范围内管理它。

我们通过依赖注入访问数据库会话,使用 ``db_session`` 参数。

更新后的代码如下:

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_init_plugin.py
    :language: python
    :linenos:
    :emphasize-lines: 12, 28, 76-78, 85

最显著的区别是我们不再需要 ``db_connection()`` 生命周期上下文管理器 - 插件为我们处理这个。它还处理在我们的数据库中创建表,如果我们在创建 ``SQLAlchemyAsyncConfig`` 实例时提供我们的元数据并设置 ``create_all=True``。

此外,我们有一个新的 ``db_session`` 依赖项可用,我们在 ``provide_transaction()`` 依赖提供程序中使用它,而不是创建我们自己的会话。

下一步
==========

接下来,我们将对应用程序进行最后一次更改,然后我们将进行回顾!
