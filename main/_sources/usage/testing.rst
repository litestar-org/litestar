Testing
=======

Testing a Litestar application is made simple by the testing utilities provided out of the box.
Based on `httpx <https://www.python-httpx.org/>`_, they come with a familiar interface and integrate seamlessly into
synchronous or asynchronous tests.


Test Clients
------------

Litestar provides 2 test clients:

- :class:`~litestar.testing.AsyncTestClient`: An asynchronous test client to be used in asynchronous environments. It
  runs the application and client on an externally managed event loop. Ideal for testing asynchronous behaviour, or when
  dealing with asynchronous resources
- :class:`~litestar.testing.TestClient`: A synchronous test client. It runs the application in a newly created event
  loop within a separate thread. Ideal when no async behaviour needs to be tested, and no external event loop is
  provided by the testing library


Let's say we have a very simple app with a health check endpoint:

.. code-block:: python
    :caption: ``my_app/main.py``

    from litestar import Litestar, MediaType, get


    @get(path="/health-check", media_type=MediaType.TEXT)
    def health_check() -> str:
        return "healthy"


    app = Litestar(route_handlers=[health_check])


We would then test it using the test client like so:

.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. code-block:: python
            :caption: ``tests/test_health_check.py``

            from litestar.status_codes import HTTP_200_OK
            from litestar.testing import TestClient

            from my_app.main import app

            app.debug = True


            def test_health_check():
                with TestClient(app=app) as client:
                    response = client.get("/health-check")
                    assert response.status_code == HTTP_200_OK
                    assert response.text == "healthy"

    .. tab-item:: Async
        :sync: async

        .. code-block:: python
            :caption: ``tests/test_health_check.py``

            from litestar.status_codes import HTTP_200_OK
            from litestar.testing import AsyncTestClient

            from my_app.main import app

            app.debug = True


            async def test_health_check():
                async with AsyncTestClient(app=app) as client:
                    response = await client.get("/health-check")
                    assert response.status_code == HTTP_200_OK
                    assert response.text == "healthy"


Since we would probably need to use the client in multiple places, it's better to make it into a pytest fixture:


.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. code-block:: python
            :caption: ``tests/conftest.py``

            from typing import TYPE_CHECKING, Iterator

            import pytest

            from litestar.testing import TestClient

            from my_app.main import app

            if TYPE_CHECKING:
                from litestar import Litestar

            app.debug = True


            @pytest.fixture(scope="function")
            def test_client() -> Iterator[TestClient[Litestar]]:
                with TestClient(app=app) as client:
                    yield client


    .. tab-item:: Async
        :sync: async

        .. code-block:: python
            :caption: ``tests/conftest.py``

            from typing import TYPE_CHECKING, AsyncIterator

            import pytest

            from litestar.testing import AsyncTestClient

            from my_app.main import app

            if TYPE_CHECKING:
                from litestar import Litestar

            app.debug = True


            @pytest.fixture(scope="function")
            async def test_client() -> AsyncIterator[AsyncTestClient[Litestar]]:
                async with AsyncTestClient(app=app) as client:
                    yield client


We would then be able to rewrite our test like so:

.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: /examples/testing/test_health_check_sync.py
            :caption: ``tests/test_health_check.py``
            :language: python


    .. tab-item:: Async
        :sync: async

        .. literalinclude:: /examples/testing/test_health_check_async.py
            :caption: ``tests/test_health_check.py``
            :language: python


Deciding which test client to use
+++++++++++++++++++++++++++++++++

In most situations, it doesn't make a functional difference, and just comes down to preference, as both clients offer
the same API and capabilities. However, there are some situations where the way the clients run and interact with the
application are important, specifically when testing in an asynchronous context.

A common issue when using `anyio's pytest plugin <https://anyio.readthedocs.io/en/stable/testing.html>`_ or
`pytest-asyncio <https://github.com/pytest-dev/pytest-asyncio>`_ to run asynchronous tests or fixtures, using the
synchronous :class:`~litestar.testing.TestClient` means that the application will run in a *different event loop* than
the test or fixture. In practice, this can result in some difficult to debug and solve situations, especially when
setting up async resources outside the application, for example when using the factory pattern.

The following example uses a shared instance of an ``httpx.AsyncClient``. It uses the common factory function, which
allows to customise the client for tests, for example to add authentication headers.

.. literalinclude:: /examples/testing/async_resource_test_issue.py
    :language: python

Running this test will fail with a ``RuntimeError: Event loop is closed``, when trying to close the ``AsyncClient``
instance. This is happening because:

- The ``http_test_client`` fixture sets up the client in *event loop A*
- The ``TestClient`` instance created within the ``test_handler`` test sets up *event loop B* and runs the application
  in it
- A call to ``http_client.get``, the ``httpx.AsyncClient`` instance creates a new connection within *loop B* and
  attaches it to the client instance
- The ``TestClient`` instance closes *event loop B*
- The cleanup step of the ``http_test_client`` fixture calls ``httpx.AsyncClient.aclose()`` instance within *loop A*,
  which internally tries to close the connection made in the previous step. That connection however is still attached
  to *loop B* that was owned by the ``TestClient`` instance, and is now closed


This can easily fixed by switching the test from :class:`~litestar.testing.TestClient` to
:class:`~litestar.testing.AsyncTestClient`:

.. literalinclude:: /examples/testing/async_resource_test_issue_fix.py
    :language: python

Now the fixture, test and application code are all running within the same event loop, ensuring that all resources can
be cleaned up properly without issues.

.. literalinclude:: /examples/testing/event_loop_demonstration.py
    :language: python
    :caption: Showcasing the different running event loops when using ``TestClient``


Testing websockets
++++++++++++++++++

Litestar's test client enhances the httpx client to support websockets. To test a websocket endpoint, you can use the
:meth:`websocket_connect <litestar.testing.TestClient.websocket_connect>` method on the test client. The method returns
a websocket connection object that you can use to send and receive messages, see an example below for json:

For more information, see also the :class:`WebSocket <litestar.connection.WebSocket>` class in the API documentation and
the :ref:`websocket <usage/websockets:websockets>` documentation.


.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: /examples/testing/test_websocket_sync.py
            :language: python

    .. tab-item:: Async
        :sync: async

        .. literalinclude:: /examples/testing/test_websocket_async.py
            :language: python


Using sessions
++++++++++++++

If you are using :ref:`session middleware <usage/middleware/builtin-middleware:session middleware>` for session
persistence across requests, then you might want to inject or inspect session data outside a request. For this,
:class:`TestClient <.testing.TestClient>` provides two methods:

* :meth:`set_session_data <litestar.testing.TestClient.set_session_data>`
* :meth:`get_session_data <litestar.testing.TestClient.get_session_data>`


.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: /examples/testing/test_set_session_data.py
            :caption: Setting session data
            :language: python


        .. literalinclude:: /examples/testing/test_get_session_data.py
            :caption: Getting session data
            :language: python

    .. tab-item:: Async
        :sync: async

        .. literalinclude:: /examples/testing/test_set_session_data_async.py
            :caption: Setting session data
            :language: python


        .. literalinclude:: /examples/testing/test_get_session_data_async.py
            :caption: Getting session data
            :language: python


Running async functions on TestClient
+++++++++++++++++++++++++++++++++++++

When using the synchronous :class:`TestClient <.testing.TestClient>`, it runs the application in a separate thread,
which provides the event loop. For this, it makes use of :class:`anyio.BlockingPortal <anyio.abc.BlockingPortal>`.

``TestClient`` makes this portal public, so it can be used to run arbitrary asynchronous code in the same event loop as
the application:

.. literalinclude:: /examples/testing/test_with_portal.py
   :caption: Using a blocking portal
   :language: python


Creating a test app
-------------------

Litestar also offers a helper function called :func:`create_test_client <litestar.testing.create_test_client>` which
first creates an instance of Litestar and then a test client using it. There are multiple use cases for this helper -
when you need to check generic logic that is decoupled from a specific Litestar app, or when you want to test endpoints
in isolation.

.. code-block:: python
    :caption: ``my_app/tests/test_health_check.py``

    from litestar.status_codes import HTTP_200_OK
    from litestar.testing import create_test_client

    from my_app.main import health_check

    def test_health_check():
        with create_test_client([health_check]) as client:
            response = client.get("/health-check")
            assert response.status_code == HTTP_200_OK
            assert response.text == "healthy"


Running a live server
---------------------

The test clients make use of HTTPX's ability to directly call into an ASGI app, without
having to run an actual server. In most cases this is sufficient but there are some
exceptions where this won't work, due to the limitations of the emulated client-server
communication.

For example, when using server-sent events with an infinite generator, it will lock up
the test client, since HTTPX tries to consume the full response before returning a
request.

Litestar offers two helper functions,
:func:`litestar.testing.subprocess_sync_client` and
:func:`litestar.testing.subprocess_async_client` that will
launch a Litestar instance with in a subprocess and set up an httpx client for running
tests. You can either load your actual app file or create subsets from it as you would
with the regular test client setup:

.. literalinclude:: /examples/testing/subprocess_sse_app.py
    :language: python

.. literalinclude:: /examples/testing/test_subprocess_sse.py
    :language: python

By default, the subprocess client will capture all output from the litestar instance. To discard output in the main (testing) process, set the ``capture_output`` argument to ``False`` when creating the client:

.. code-block:: python

    @pytest.fixture(name="async_client")
    async def fx_async_client() -> AsyncIterator[httpx.AsyncClient]:
        async with subprocess_async_client(workdir=ROOT, app="subprocess_sse_app:app", capture_output=False) as client:
            yield client


RequestFactory
--------------

Another helper is the :class:`RequestFactory <litestar.testing.RequestFactory>` class, which creates instances of
:class:`litestar.connection.request.Request <litestar.connection.request.Request>`. The use case for this helper is when
you need to test logic that expects to receive a request object.

For example, lets say we wanted to unit test a *guard* function in isolation, to which end we'll reuse the examples
from the :doc:`route guards </usage/security/guards>` documentation:


.. code-block:: python
    :caption: ``my_app/guards.py``

    from litestar import Request
    from litestar.exceptions import NotAuthorizedException
    from litestar.handlers.base import BaseRouteHandler


    def secret_token_guard(request: Request, route_handler: BaseRouteHandler) -> None:
        if (
            route_handler.opt.get("secret")
            and not request.headers.get("Secret-Header", "") == route_handler.opt["secret"]
        ):
            raise NotAuthorizedException()

We already have our route handler in place:

.. code-block:: python
    :caption: ``my_app/secret.py``

    from os import environ

    from litestar import get

    from my_app.guards import secret_token_guard


    @get(path="/secret", guards=[secret_token_guard], opt={"secret": environ.get("SECRET")})
    def secret_endpoint() -> None: ...

We could thus test the guard function like so:

.. code-block:: python
    :caption: ``tests/guards/test_secret_token_guard.py``

    import pytest

    from litestar.exceptions import NotAuthorizedException
    from litestar.testing import RequestFactory

    from my_app.guards import secret_token_guard
    from my_app.secret import secret_endpoint

    request = RequestFactory().get("/")


    def test_secret_token_guard_failure_scenario():
        copied_endpoint_handler = secret_endpoint.copy()
        copied_endpoint_handler.opt["secret"] = None
        with pytest.raises(NotAuthorizedException):
            secret_token_guard(request=request, route_handler=copied_endpoint_handler)


    def test_secret_token_guard_success_scenario():
        copied_endpoint_handler = secret_endpoint.copy()
        copied_endpoint_handler.opt["secret"] = "super-secret"
        secret_token_guard(request=request, route_handler=copied_endpoint_handler)
