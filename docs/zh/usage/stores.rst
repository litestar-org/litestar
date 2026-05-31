:tocdepth: 4

存储
======

.. py:currentmodule:: litestar.stores


在开发应用程序时，通常需要一个简单的存储机制，例如在 :doc:`缓存响应数据</usage/caching>` 或为 :ref:`服务器端会话 <usage/middleware/builtin-middleware:Server-side sessions>` 存储数据时。在这些情况下，通常不需要传统数据库，简单的键/值存储就足够了。

Litestar 提供了几个低级键值存储，提供异步接口以线程和进程安全的方式存储数据。这些存储通过 :class:`注册表 <litestar.stores.registry.StoreRegistry>` 集中管理，允许在整个应用程序和第三方集成（例如插件）中轻松访问。


内置存储
---------------

:class:`MemoryStore <litestar.stores.memory.MemoryStore>`
    一个简单的内存存储，使用字典来保存数据。此存储不提供持久性，也不是线程或多进程安全的，但它适用于基本应用程序（如缓存），并且通常具有最低的开销。这是 Litestar 内部使用的默认存储。如果您计划启用 :doc:`多个 Web 工作进程 </reference/cli>` 并且需要跨多个工作进程的进程间通信，则应使用其他非内存存储之一。

:class:`FileStore <litestar.stores.file.FileStore>`
    将数据保存为磁盘上的文件的存储。内置持久性，数据易于提取和备份。与内存解决方案相比速度较慢，主要适用于需要存储大量数据、特别长寿命或持久性非常重要的情况。提供 `命名空间`_。

:class:`RedisStore <litestar.stores.redis.RedisStore>`
    由 `redis <https://redis.io/>`_ 支持的存储。它提供 Redis 的所有保证和功能，使其适用于几乎所有应用程序。提供 `命名空间`_。

:class:`ValkeyStore <litestar.stores.valkey.ValkeyStore>`
    由 `valkey <https://valkey.io>`_ 支持的存储，valkey 是 Redis 的一个分支，是 Redis 许可证更改的结果。与 RedisStore 类似，它适用于几乎所有应用程序并支持 `命名空间`_。在撰写本文时，:class:`Valkey <valkey.asyncio.Valkey>` 等同于 :class:`redis.asyncio.Redis`，所有有关 Redis 的说明也适用于 Valkey。

.. admonition:: 为什么不支持 memcached？
    :class: info

    Memcached 不是受支持的后端，将来也可能不会添加。原因很简单，因为很难正确支持 memcached，因为它缺少很多基本功能，如检查键的过期时间，或类似 Redis 的 `SCAN <https://redis.io/commands/scan/>`_ 命令，该命令允许实现基于模式的键删除。


与存储交互
------------------------

存储的最基本操作是：

- :meth:`get <.base.Store.get>`：检索存储的值
- :meth:`set <.base.Store.set>`：在存储中设置值
- :meth:`delete <.base.Store.delete>`：删除存储的值


获取和设置值
++++++++++++++++++++++++++


.. literalinclude:: /examples/stores/get_set.py
    :language: python


设置过期时间
++++++++++++++++++++++

:meth:`set <.base.Store.set>` 方法有一个可选参数 ``expires_in``，允许指定存储值应该过期的时间。


.. literalinclude:: /examples/stores/expiry.py
    :language: python


.. note::
    由各个存储决定如何处理过期值，实现可能有所不同。例如，:class:`基于 redis 的存储 <.redis.RedisStore>` 使用 Redis 的原生过期机制来处理此问题，而 :class:`FileStore <.file.FileStore>` 仅在尝试访问过期值时删除它们，或通过 :meth:`delete_expired <.file.FileStore.delete_expired>` 方法显式删除。


还可以在每次访问时延长过期时间，这对于服务器端会话或 LRU 缓存等应用程序很有用：

.. literalinclude:: /examples/stores/expiry_renew_on_get.py
    :language: python


删除过期值
#######################

使用 :class:`MemoryStore <.memory.MemoryStore>` 或 :class:`FileStore <.file.FileStore>` 时，过期数据不会自动删除。相反，它只会在访问数据时发生，或者通过 :meth:`MemoryStore.delete_expired <.memory.MemoryStore.delete_expired>` 或 :meth:`FileStore.delete_expired <.file.FileStore.delete_expired>` 显式调用此过程。

定期调用 ``delete_expired`` 是一个好习惯，以确保存储值的大小不会无限增长。

在此示例中，:ref:`after_response <after_response>` 处理程序用于最多每 30 秒删除一次过期项：

.. literalinclude:: /examples/stores/delete_expired_after_response.py
    :language: python

使用 :class:`FileStore <.file.FileStore>` 时，也可以在启动时删除过期项：


.. literalinclude:: /examples/stores/delete_expired_on_startup.py
    :language: python


.. note::
    对于 :class:`MemoryStore <.memory.MemoryStore>`，不需要这样做，因为数据只是存储在字典中。这意味着每次创建此存储的新实例时，它都会从空开始。


可以存储什么
++++++++++++++++++

存储通常操作 :class:`bytes`；它们接受字节来存储，并将返回字节。为方便起见，:meth:`set <.base.Store.set>` 方法还允许传入字符串，这些字符串将在存储之前进行 UTF-8 编码。这意味着即使将字符串传递给 :meth:`set <.base.Store.set>`，:meth:`get <.base.Store.get>` 也将返回字节。

这种限制的原因很简单：用于存储数据的不同后端提供了截然不同的编码、存储和（反）序列化能力。由于存储设计为可互换，这意味着要满足一个共同的分母，即所有后端都支持的类型。:class:`bytes` 满足这些要求，并可以存储各种各样的数据。

.. admonition:: 技术细节

    :class:`MemoryStore <.memory.MemoryStore>` 与此不同，因为它在存储值之前不做任何编码。这意味着技术上可以在此存储中存储任意对象，并获取相同的对象。但是，这不会反映在存储的类型中，因为底层的 :class:`Store <.base.Store>` 接口不保证此行为，并且不保证 :class:`MemoryStore <.memory.MemoryStore>` 在这种情况下始终如此行为。


命名空间
+++++++++++

当存储用于多个目的时，需要一些额外的簿记来安全地执行批量操作，例如 :class:`delete_all <.base.Store.delete_all>`。例如，如果使用了 :class:`RedisStore <.redis.RedisStore>`，简单地发出 `FLUSHALL <https://redis.io/commands/flushall/>`_ 命令可能会产生不可预见的后果。

为了帮助解决这个问题，一些存储提供命名空间功能，允许构建简单的存储层次结构。它们带有附加的 :meth:`with_namespace <.base.NamespacedStore.with_namespace>` 方法，该方法返回一个新的 :class:`NamespacedStore <.base.NamespacedStore>` 实例。一旦创建了命名空间存储，对它的操作将只影响它自己及其子命名空间。

使用 :class:`RedisStore <.redis.RedisStore>` 时，这允许重用相同的底层 :class:`Redis <redis.asyncio.Redis>` 实例和连接，同时确保隔离。

.. note::
    :class:`RedisStore <.redis.RedisStore>` 默认使用 ``LITESTAR`` 命名空间；此存储创建的所有键在 redis 中存储数据时都将使用 ``LITESTAR`` 前缀。
    :meth:`RedisStore.delete_all <.redis.RedisStore.delete_all>` 的实现方式是它只会删除与当前命名空间匹配的键，使其安全且无副作用。

    可以通过在创建新实例时显式传递 ``namespace=None`` 来关闭此功能。


.. literalinclude:: /examples/stores/namespacing.py
    :language: python

即使这里定义的所有三个存储都使用相同的 Redis 实例，在 ``cache_store`` 上调用 ``delete_all`` 也不会影响 ``session_store`` 中的数据。

像这样分层定义存储仍然允许通过简单地在根存储上调用 :meth:`delete_all <.base.Store.delete_all>` 来轻松清除所有内容。


使用注册表管理存储
---------------------------------

:class:`StoreRegistry <litestar.stores.registry.StoreRegistry>` 是一个中心位置，可以通过它配置和管理存储，并可以帮助轻松访问应用程序其他部分、Litestar 内部或第三方集成设置和使用的存储。它通过 :class:`Litestar.stores <litestar.app.Litestar>` 属性在整个应用程序上下文中可用。

它基于几个基本原则：

- 可以向注册表提供初始存储映射
- 可以使用 :meth:`get <.registry.StoreRegistry.get>` 请求注册的存储
- 如果请求的存储尚未注册，将使用 `默认工厂`_ 创建并注册该名称的存储


.. literalinclude:: /examples/stores/registry.py
    :language: python


此模式提供存储隔离，并提供一种简单的方法来配置中间件和其他 Litestar 功能或第三方集成使用的存储。

在以下示例中，通过注册表访问由 :class:`RateLimitMiddleware <litestar.middleware.rate_limit.RateLimitMiddleware>` 设置的存储：

.. literalinclude:: /examples/stores/registry_access_integration.py
    :language: python


这是有效的，因为 :class:`RateLimitMiddleware <litestar.middleware.rate_limit.RateLimitMiddleware>` 也会通过 ``app.stores.get`` 在内部请求其存储。


默认工厂
+++++++++++++++++++

上面的模式通过使用注册表的默认工厂来实现；每次请求尚未注册的存储时都会调用的可调用对象。它类似于 :meth:`dict.get` 的 ``default`` 参数。

默认情况下，默认工厂是一个返回新 :class:`MemoryStore <litestar.stores.memory.MemoryStore>` 实例的函数。可以通过向注册表提供自定义 ``default_factory`` 方法来更改此行为。

要使用此功能，可以直接将注册表实例传递给应用程序：

.. literalinclude:: /examples/stores/registry_default_factory.py
    :language: python

现在，每次请求未定义的存储时，注册表都将返回相同的 :class:`MemoryStore <litestar.stores.memory.MemoryStore>`。


使用注册表配置集成
++++++++++++++++++++++++++++++++++++++++++++

此机制还允许控制各种集成使用的存储，例如中间件：

.. literalinclude:: /examples/stores/registry_configure_integrations.py
    :language: python


在此示例中，注册表使用 ``sessions`` 和 ``response_cache`` 键设置存储。这些不是魔术常量，而是可以更改的配置值。这些名称恰好是它们的默认值。调整这些默认值可以轻松重用存储，而无需更复杂的设置：

.. literalinclude:: /examples/stores/configure_integrations_set_names.py
    :language: python

现在，速率限制中间件和响应缓存将使用 ``redis`` 存储，而会话将存储在 ``file`` 存储中。


使用命名空间设置默认工厂
++++++++++++++++++++++++++++++++++++++++++++

默认工厂可以与 `命名空间`_ 结合使用，以创建隔离的、分层组织的存储，只需最少的样板代码：

.. literalinclude:: /examples/stores/registry_default_factory_namespacing.py
    :language: python


无需任何额外配置，每次使用唯一名称调用 ``app.stores.get`` 都将仅返回此名称的命名空间，同时重用底层 Redis 实例。


存储生命周期
++++++++++++++

当应用程序关闭时，存储可能不会自动关闭。
特别是对于 RedisStore，如果您不使用类方法 :meth:`RedisStore.with_client <.redis.RedisStore.with_client>` 并传入自己的 Redis 实例，则情况就是如此。
在这种情况下，您有责任自己关闭 Redis 实例。
