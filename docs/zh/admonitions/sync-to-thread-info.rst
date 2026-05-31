.. admonition:: 同步和异步可调用对象
    :class: important

    支持同步和异步可调用对象。其中一个重要方面是，使用执行阻塞操作（例如 I/O 或计算密集型任务）的同步函数可能会阻塞运行事件循环的主线程，进而阻塞整个应用程序。

    为了缓解这种情况，可以将 ``sync_to_thread`` 参数设置为 ``True``，这将导致该函数在线程池中运行。

    如果同步函数是非阻塞的，将 ``sync_to_thread`` 设置为 ``False`` 将告知 Litestar 用户确信其行为，并且该函数可以被视为非阻塞的。

    如果传递了同步函数而未设置显式的 ``sync_to_thread`` 值，则会引发警告。

    .. seealso::

        :doc:`/topics/sync-vs-async`
