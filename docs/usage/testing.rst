Testing
=======

Testing is a first class citizen in Litestar, which offers several powerful testing utilities out of the box.


Test Client
-----------

Litestar's test client is built on top of
the `httpx <https://github.com/encode/httpx>`_ library. To use the test client you should pass to it an
instance of Litestar as the ``app`` kwarg.

Suppose we have a very simple app with a health check endpoint:

.. code-block:: python
    :caption: my_app/main.py

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
            :caption: tests/test_health_check.py

            from litestar.status_codes import HTTP_200_OK
            from litestar.testing import TestClient

            from my_app.main import app


            def test_health_check():
                with TestClient(app=app) as client:
                    response = client.get("/health-check")
                    assert response.status_code == HTTP_200_OK
                    assert response.text == "healthy"

    .. tab-item:: Async
        :sync: async

        .. code-block:: python
            :caption: tests/test_health_check.py

            from litestar.status_codes import HTTP_200_OK
            from litestar.testing import AsyncTestClient

            from my_app.main import app


            async def test_health_check():
                async with AsyncTestClient(app=app) as client:
                    response = await client.get("/health-check")
                    assert response.status_code == HTTP_200_OK
                    assert response.text == "healthy"


Since we would probably need to use the client in multiple places, it is better to make it into a pytest fixture:


.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. code-block:: python
            :caption: tests/conftest.py

            import pytest

            from litestar.testing import TestClient

            from my_app.main import app


            @pytest.fixture(scope="function")
            def test_client() -> TestClient:
                return TestClient(app=app)


    .. tab-item:: Async
        :sync: async

        .. code-block:: python
            :caption: tests/conftest.py

            import pytest

            from litestar.testing import AsyncTestClient

            from my_app.main import app


            @pytest.fixture(scope="function")
            async def test_client() -> AsyncTestClient:
                return AsyncTestClient(app=app)


We would then be able to rewrite our test like so:

.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: /examples/testing/test_health_check_sync.py
            :caption: tests/test_health_check.py
            :language: python


    .. tab-item:: Async
        :sync: async

        .. literalinclude:: /examples/testing/test_health_check_async.py
            :caption: tests/test_health_check.py
            :language: python


Using sessions
++++++++++++++

If you are using :ref:`session middleware <usage/middleware/builtin-middleware:session middleware>` for session persistence
across requests, then you might want to inject or inspect session data outside a request. For this,
:class:`TestClient <.testing.TestClient>` provides two methods:

* :meth:`set_session_data <litestar.testing.TestClient.set_session_data>`
* :meth:`get_session_data <litestar.testing.TestClient.get_session_data>`

.. attention::

    - The Session Middleware must be enabled in Litestar app provided to the TestClient to use sessions.
    - If you are using the
      :class:`ClientSideSessionBackend <litestar.middleware.session.client_side.ClientSideSessionBackend>` you need to
      install the ``cryptography`` package. You can do so by installing ``litestar`` with the ``[cryptography]`` extra:

    .. tab-set::

        .. tab-item:: pip

            .. code-block:: bash
                :caption: Using pip

                python3 -m pip install litestar[cryptography]

        .. tab-item:: pipx

            .. code-block:: bash
                :caption: Using `pipx <https://pypa.github.io/pipx/>`_

                pipx install litestar[cryptography]

        .. tab-item:: pdm

            .. code-block:: bash
                :caption: Using `PDM <https://pdm.fming.dev/>`_

                pdm add litestar[cryptography]

        .. tab-item:: Poetry

            .. code-block:: bash
                :caption: Using `Poetry <https://python-poetry.org/>`_

                poetry add litestar[cryptography]

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


Using a blocking portal
+++++++++++++++++++++++

The :class:`TestClient <.testing.TestClient>` uses a feature of `anyio <https://anyio.readthedocs.io/en/stable/>`_
called a :class:`Blocking Portal <anyio:anyio.from_thread.BlockingPortal>`.

The :class:`Blocking Portal <anyio:anyio.from_thread.BlockingPortal>` allows :class:`TestClient <.testing.TestClient>`
to execute asynchronous functions using a synchronous call. :class:`TestClient <.testing.TestClient>` creates
a blocking portal to manage ``Litestar``'s async logic, and it allows
:class:`TestClient <.testing.TestClient>`'s API to remain fully synchronous.

Any tests that are using an instance of :class:`TestClient <.testing.TestClient>` can also
make use of the blocking portal to execute asynchronous functions without the test itself being asynchronous.

.. literalinclude:: /examples/testing/test_with_portal.py
   :caption: Using a blocking portal
   :language: python

Creating a test app
-------------------

Litestar also offers a helper function called :func:`create_test_client <litestar.testing.create_test_client>` which first creates
an instance of Litestar and then a test client using it. There are multiple use cases for this helper - when you need to check
generic logic that is decoupled from a specific Litestar app, or when you want to test endpoints in isolation.

You can pass to this helper all the kwargs accepted by
the litestar constructor, with the :attr:`~litestar.config.app.AppConfig.route_handlers` kwarg being **required**.
Yet unlike the Litestar app, which expects :attr:`~litestar.config.app.AppConfig.route_handlers` to be a :class:`list`,
here you can also pass individual values.

For example, you can do this:

.. code-block:: python
    :caption: Testing a health check endpoint by passing a list of route handlers to ``create_test_client``
        via ``my_app/tests/test_health_check.py``

    from litestar.status_codes import HTTP_200_OK
    from litestar.testing import create_test_client

    from my_app.main import health_check


    def test_health_check():
        with create_test_client(route_handlers=[health_check]) as client:
            response = client.get("/health-check")
            assert response.status_code == HTTP_200_OK
            assert response.text == "healthy"

But also this:

.. code-block:: python
    :caption: Testing a health check endpoint by passing a single route handler to ``create_test_client``
        via ``my_app/tests/test_health_check.py``

    from litestar.status_codes import HTTP_200_OK
    from litestar.testing import create_test_client

    from my_app.main import health_check


    def test_health_check():
        with create_test_client(route_handlers=health_check) as client:
            response = client.get("/health-check")
            assert response.status_code == HTTP_200_OK
            assert response.text == "healthy"


RequestFactory
--------------

Another helper is the :class:`RequestFactory <litestar.testing.RequestFactory>` class, which creates instances of
:class:`~litestar.connection.request.Request`. The use case for this helper is when
you need to test logic that expects to receive a request object.

For example, suppose we want to unit test a ``guard`` function in isolation.
To illustrate this, we will reuse the examples from the :doc:`route guards </usage/security/guards>` documentation:

.. code-block:: python
    :caption: Defining a guard function in ``my_app/guards.py`` that checks for a secret token

    from litestar import Request
    from litestar.exceptions import NotAuthorizedException
    from litestar.handlers.base import BaseRouteHandler


    def secret_token_guard(request: Request, route_handler: BaseRouteHandler) -> None:
        if (
            route_handler.opt.get("secret")
            and request.headers.get("Secret-Header", "")
            != route_handler.opt["secret"]
        ):
            raise NotAuthorizedException()

We already have our route handler in place:

.. code-block:: python
    :caption: Our route handler in ``my_app/main.py``

    from os import environ

    from litestar import get

    from my_app.guards import secret_token_guard


    @get(path="/secret", guards=[secret_token_guard], opt={"secret": environ.get("SECRET")})
    def secret_endpoint() -> None: ...

We could then test the guard function like so:

.. code-block:: python
    :caption: Testing the ``secret_token_guard`` function via ``my_app/tests/test_guards.py``

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


Using `polyfactory <https://github.com/litestar-org/polyfactory>`_
------------------------------------------------------------------

`Polyfactory <https://github.com/litestar-org/polyfactory>`_ offers an easy
and powerful way to generate mock data from pydantic models and dataclasses.

Suppose we have an API that talks to an external service and retrieves some data:

.. code-block:: python
    :caption: Example of a service that retrieves an item from an external source in ``my_app/main.py``

    from typing import Protocol, runtime_checkable

    from polyfactory.factories.pydantic import BaseModel
    from litestar import get


    class Item(BaseModel):
        name: str


    @runtime_checkable
    class Service(Protocol):
        def get(self) -> Item: ...


    @get(path="/item")
    def get_item(service: Service) -> Item:
        return service.get()


We could test the ``/item`` route like so:

.. code-block:: python
    :caption: Testing the ``/item`` route via ``tests/test_get_item.py``

    import pytest
    from my_app.main import Item, Service, get_item

    from litestar.di import Provide
    from litestar.status_codes import HTTP_200_OK
    from litestar.testing import create_test_client


    @pytest.fixture()
    def item():
        return Item(name="Chair")


    def test_get_item(item: Item):
        class MyService(Service):
            def get_one(self) -> Item:
                return item

        with create_test_client(route_handlers=get_item, dependencies={"service": Provide(lambda: MyService())}) as client:
            response = client.get("/item")
            assert response.status_code == HTTP_200_OK
            assert response.json() == item.dict()

While we can define the test data manually, as is done in the above, this can be quite cumbersome. That is
where `polyfactory <https://github.com/litestar-org/polyfactory>`_ library comes in. It generates mock data for
pydantic models and dataclasses based on type annotations. With it, we could rewrite the above example like so:

.. code-block:: python
    :caption: Example of using ``polyfactory`` to generate mock data for the ``Item`` model in ``my_app/main.py``

    from typing import Protocol, runtime_checkable

    import pytest
    from polyfactory.factories.pydantic_factory import ModelFactory
    from pydantic import BaseModel

    from litestar import get
    from litestar.di import Provide
    from litestar.status_codes import HTTP_200_OK
    from litestar.testing import create_test_client


    class Item(BaseModel):
        name: str


    @runtime_checkable
    class Service(Protocol):
        def get_one(self) -> Item: ...


    @get(path="/item")
    def get_item(service: Service) -> Item:
        return service.get_one()


    class ItemFactory(ModelFactory[Item]):
        model = Item


    @pytest.fixture()
    def item():
        return ItemFactory.build()


    def test_get_item(item: Item):
        class MyService(Service):
            def get_one(self) -> Item:
                return item

        with create_test_client(
            route_handlers=get_item,
            dependencies={"service": Provide(lambda: MyService())}
        ) as client:
            response = client.get("/item")
            assert response.status_code == HTTP_200_OK
            assert response.json() == item.dict()
