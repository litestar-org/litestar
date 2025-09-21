:orphan:

3.x Changelog
=============

.. changelog:: 3.0.0
    :date: 2024-08-30

    .. change:: Make ``AsyncTestClient`` async-native
        :type: feature
        :pr: 4291
        :issue: 1920
        :breaking:

        Re-implement :class:`~litestar.testing.AsyncTestClient` to be async-native, i.e. use the currently running event
        loop to run the application, instead of running a separate event loop in a new thread. Additionally, a new
        :class:`~litestar.testing.AsyncWebSocketTestSession` has been introduced, providing an async testing utility
        for WebSockets.

        To ensure consisten behaviour across ``TestClient`` and ``AsyncTestClient``, all testing utilities have been
        rewritten to be async first, with their synchronous counterparts proxying calls to the async implementation,
        which they run internally within a dedicated thread + event loop.

        .. seealso::
            :ref:`usage/testing:Test Clients`
            :ref:`usage/testing:Deciding which test client to use`


