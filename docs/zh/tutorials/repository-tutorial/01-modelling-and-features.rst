数据库建模和仓储功能简介
----------------------------------------------------------
在本教程中,我们将介绍 Litestar 中集成的仓储功能,首先使用包含的 SQLAlchemy 声明式模型助手进行数据库建模。这些是一系列类和混入,它们结合了常用的函数/列类型,使模型的使用更加容易。

.. tip:: 本教程的完整代码可以在下面的 :ref:`完整代码 <01-repo-full-code>` 部分找到。

建模
---------

我们将从建模作者和书籍之间的实体和关系开始。
我们将首先创建 ``Author`` 表,利用
:class:`UUIDBase <advanced_alchemy.base.UUIDBase>` 类。为了保持简单,我们的第一个模型将只包含三个字段:``id``、``name`` 和 ``dob``。

.. literalinclude:: /examples/sqla/sqlalchemy_declarative_models.py
    :language: python
    :caption: ``app.py``
    :lines: 9, 11, 18-20
    :linenos:

书籍实体不被视为"强"实体,因此总是需要一个作者才能创建。我们需要配置我们的 SQLAlchemy 类,以便它知道这种关系。我们将通过合并 ``Book`` 关系来扩展 ``Author`` 模型。这允许每个 ``Author`` 记录拥有多个 ``Book`` 记录。通过以这种方式配置,SQLAlchemy 将在每个 ``Book`` 记录中使用 ``author_id`` 字段时自动包含必要的外键约束。

.. literalinclude:: /examples/sqla/sqlalchemy_declarative_models.py
    :language: python
    :caption: ``app.py``
    :lines: 9, 11, 18-22, 27-30
    :linenos:

通过使用审计模型,我们可以自动记录记录创建和上次更新的时间。

要实现这一点,我们将通过
:class:`UUIDAuditBase <advanced_alchemy.base.UUIDAuditBase>` 类定义一个新的 ``Book`` 模型。注意这里唯一的修改是我们继承的父类。这个微小的更改使 `book` 表在部署时自动具有时间戳列(`created` 和 `updated`)!

.. note::

    如果你的应用程序需要基于整数的主键,可以在
    :class:`BigIntBase <advanced_alchemy.base.BigIntAuditBase>` 和
    :class:`BigIntAuditBase <advanced_alchemy.base.UUIDAuditBase>`
    分别找到等效的基础模型和基础审计模型实现。

.. important::
    仅限 `Spanner <https://cloud.google.com/spanner>`_:

    在 Spanner 中使用单调变化的主键被认为是反模式,并会导致性能问题。此外,Spanner 目前不包含类似于 ``Sequence`` 对象的习语。这意味着 ``BigIntBase`` 和 ``BigIntAuditBase`` 目前不支持 Spanner。

内置基础模型提供的其他功能包括:

- 同步和异步仓储实现已经过各种流行数据库引擎的测试和验证。截至目前,支持六个数据库引擎:Postgres、SQLite、MySQL、DuckDB、Oracle 和 Spanner。
- 从模型名称自动推导表名。例如,名为 ``EventLog`` 的模型将对应于 ``event_log`` 数据库表。
- 一个 :class:`GUID <advanced_alchemy.types.GUID>` 数据库类型,在支持的引擎中建立本机 UUID 或作为后备的 ``Binary(16)``。
- 一个 ``BigInteger`` 变体
  :class:`BigIntIdentity <advanced_alchemy.types.BigIntIdentity>`,对于不支持的变体将恢复为 ``Integer``。
- 一个自定义 :class:`JsonB <advanced_alchemy.types.JsonB>` 类型,在可能的情况下使用本机 ``JSONB``,并将 ``Binary`` 或 ``Blob`` 作为替代。
- 一个自定义 :class:`EncryptedString <advanced_alchemy.types.EncryptedString>` 加密字符串,支持多个加密后端。

让我们在查看仓储类时继续构建这个。

.. _01-repo-full-code:

完整代码
---------

.. dropdown:: 完整代码(点击切换)

    .. literalinclude:: /examples/sqla/sqlalchemy_declarative_models.py
        :language: python
        :caption: ``app.py``
        :emphasize-lines: 9, 18-21, 27-30
        :linenos:
