最后润色和回顾
-----------------------

我们可以对应用程序进行最后一项改进。目前,我们同时使用
:class:`SQLAlchemyInitPlugin <advanced_alchemy.extensions.litestar.plugins.SQLAlchemyInitPlugin>` 和
:class:`SQLAlchemySerializationPlugin <advanced_alchemy.extensions.litestar.plugins.SQLAlchemySerializationPlugin>`,但此配置有一个快捷方式::class:`SQLAlchemyPlugin <advanced_alchemy.extensions.litestar.plugins.SQLAlchemyPlugin>` 是两者的组合,因此我们可以通过使用它来简化配置。

这是我们的最终应用程序:

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_plugin.py
    :language: python
    :linenos:
    :emphasize-lines: 10, 82

回顾
=====

在本教程中,我们学习了如何使用 SQLAlchemy 插件创建一个使用数据库存储和检索数据的简单应用程序。

在最终应用程序中定义了 ``TodoItem``,表示一个 TODO 项目。它从 `SQLAlchemy <http://www.sqlalchemy.org/>`_ 提供的
:class:`DeclarativeBase <sqlalchemy.orm.DeclarativeBase>` 类扩展:

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_plugin.py
    :language: python
    :linenos:
    :lines: 1-6, 12-21

接下来,我们定义一个依赖项,集中我们的数据库事务管理和错误处理。此依赖项依赖于 ``db_session`` 依赖项,该依赖项由 SQLAlchemy 插件提供,并通过 ``transaction`` 参数提供给我们的处理器:

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_plugin.py
    :language: python
    :linenos:
    :lines: 1-11, 22-32

我们还定义了几个实用函数,帮助我们从数据库中检索 TODO 项目:

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_plugin.py
    :language: python
    :linenos:
    :lines: 1-11, 33-50

我们定义路由处理器,这是可以创建、检索和更新 TODO 项目的接口:

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_plugin.py
    :language: python
    :linenos:
    :lines: 1-11, 51-69

最后,我们定义应用程序,使用
:class:`SQLAlchemyPlugin <advanced_alchemy.extensions.litestar.plugins.SQLAlchemyPlugin>` 配置 SQLAlchemy 并管理引擎和会话生命周期,并注册我们的 ``transaction`` 依赖项。

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_plugin.py
    :language: python
    :linenos:
    :lines: 1-11, 78-83

.. seealso::

    * `Advanced Alchemy 文档 <https://docs.advanced-alchemy.litestar.dev/>`_
