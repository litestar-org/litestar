SQLAlchemy Plugin
=================

Starlite comes with built-in support for `SQLAlchemy <https://docs.sqlalchemy.org/>`_ via
the :class:`SQLAlchemyPlugin <starlite.plugins.sql_alchemy.SQLAlchemyPlugin>`.

Features
--------


* Managed `sessions <https://docs.sqlalchemy.org/en/14/orm/session.html>`_ (sync and async) including dependency injection
* Automatic serialization of SQLAlchemy models powered pydantic
* Data validation based on SQLAlchemy models powered pydantic

.. seealso::

    The following examples use SQLAlchemy's "2.0 Style" introduced in SQLAlchemy 1.4.

    If you are unfamiliar with it, you can find a comprehensive migration guide in SQLAlchemy's
    documentation `here <https://docs.sqlalchemy.org/en/14/changelog/migration_14.html#what-s-new-in-sqlalchemy-1-4>`_,
    and `a handy table <https://docs.sqlalchemy.org/en/14/changelog/migration_20.html#migration-orm-usage>`_
    comparing the ORM usage

.. attention::

    The :class:`SQLAlchemyPlugin <starlite.plugins.sql_alchemy.SQLAlchemyPlugin>` supports only
    `mapped classes <https://docs.sqlalchemy.org/en/14/tutorial/metadata.html#declaring-mapped-classes>`_.
    `Tables <https://docs.sqlalchemy.org/en/14/tutorial/metadata.html#setting-up-metadata-with-table-objects>`_ are
    currently not supported since they are not easy to convert to pydantic models.

Basic Use
---------

You can simply pass an instance of :class:`SQLAlchemyPlugin` without passing config to the Starlite constructor. This will
extend support for serialization, deserialization and DTO creation for SQLAlchemy declarative models:

.. tab-set::

    .. tab-item:: Async
        :sync: async

        .. literalinclude:: /examples/plugins/sqlalchemy_plugin/sqlalchemy_async.py
            :caption: sqlalchemy_plugin.py
            :language: python


    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: /examples/plugins/sqlalchemy_plugin/sqlalchemy_sync.py
            :caption: sqlalchemy_plugin.py
            :language: python


.. admonition:: Using imperative mappings
    :class: info

    `Imperative mappings <https://docs.sqlalchemy.org/en/14/orm/mapping_styles.html#imperative-mapping>`_
    are supported as well, just make sure to use a mapped class instead of the table itself

    .. code-block:: python

        company_table = Table(
            "company",
            Base.registry.metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String),
            Column("worth", Float),
        )


        class Company:
            pass


        Base.registry.map_imperatively(Company, company_table)


Relationships
-------------

.. attention::

    Currently only to-one relationships are supported because of the way the SQLAlchemy plugin handles relationships.
    Since it recursively traverses relationships, a cyclic reference will result in an endless loop. To prevent this,
    these relationships will be type as :class:`typing.Any` in the pydantic model
    Relationships are typed as :class:`typing.Optional` in the pydantic model by default so sending incomplete models
    won't cause any issues.


Simple relationships
^^^^^^^^^^^^^^^^^^^^

Simple relationships can be handled by the plugin automatically:

.. literalinclude:: /examples/plugins/sqlalchemy_plugin/sqlalchemy_relationships.py
    :caption: sqlalchemy_relationships.py
    :language: python


.. admonition:: Example
    :class: tip

    Run the above with ``uvicorn sqlalchemy_relationships:app``, navigate your browser to
    `http://127.0.0.0:8000/user/1 <http://127.0.0.0:8000/user/1>`_
    and you will see:

    .. code-block:: json

        {
          "id": 1,
          "name": "Peter",
          "company_id": 1,
          "company": {
            "id": 1,
            "name": "Peter Co.",
            "worth": 0
          }
        }


To-Many relationships and circular references
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For to-many relationships or those that contain circular references you need to define the pydantic models yourself:

.. literalinclude:: /examples/plugins/sqlalchemy_plugin/sqlalchemy_relationships_to_many.py
    :caption: sqlalchemy_relationships_to_many
    :language: python


.. admonition:: Example
    :class: tip

    Run the above with ``uvicorn sqlalchemy_relationships_to_many:app``, navigate your browser to `http://127.0.0.0:8000/user/1`_
    and you will see:

    .. code-block:: json

        {
          "id": 1,
          "name": "Peter",
          "pets": [
            {
              "id": 1,
              "name": "Paul"
            }
          ]
        }


Configuration
-------------

You can configure the Plugin using the :class:`SQLAlchemyConfig <starlite.plugins.sql_alchemy.SQLAlchemyConfig>` object.

Testing With SQLAlchemy
-----------------------

In a real environment, route handlers can query database using SQLAlchemy. Normally, when writing tests, I/O resources
are not used so any dependent libraries that require I/O connection cannot work with your code. If your service
establishes I/O connection with the database on startup, to initialize a test environment, these I/O connections are
mocked and return values are patched with test values.

Starlite injects `session <https://docs.sqlalchemy.org/en/14/orm/session.html>`_ (sync and async) instance of
SQLAlchemy into the route handler as a :ref:`dependency <usage/dependency-injection:dependency injection>`. Route
handlers use this instance to make and send queries to the database. As you cannot send real queries for tests, the
:class:`Session` or :class:`AsyncSession` class has to be mocked and the return values of its methods are patched
accordingly. Let's demonstrate how to write tests for a starlite app that is using
:class:`SQLAlchemyPlugin <starlite.plugins.sql_alchemy.SQLAlchemyPlugin>` with an example below:

.. tab-set::

    .. tab-item:: Starlite app
        :sync: starlite

        .. literalinclude:: /examples/plugins/testing_with_sqlalchemy/sqla_basic_app.py
            :language: python

    .. tab-item:: Tests
        :sync: tests

        .. literalinclude:: /examples/plugins/sqlalchemy_plugin/testing_with_sqlalchemy/tests_for_sqla_basic_app.py
            :language: python


Let's breakdown what's happening here:

.. code-block:: python

    @pytest.fixture(scope="session")
    def app(self) -> Starlite:
        return Starlite(
            route_handlers=[CompanyController],
            dependencies={"async_session": Provide(lambda: self.async_session_mock)},
        )


We cannot use ``app`` instance from the source because it will trigger I/O hooks that are used during the runtime. Our
purpose is to isolate the app from I/O resources for tests. We can simply create a fixture for a new Starlite instance
that only registers route handlers that we want to test.

Furthermore, in the source, the dependency ``async_session`` is registered by
:class:`SQLAlchemyPlugin` but because we are not using a database for tests, this plugin is not required here. Instead,
create a "pseudo" dependency with the same name as used in the source. Notice that :class:`Provide` is taking a callable
that returns a :class:`MagicMock` with the spec of :class:`AsyncSession`? This is intended because we want Starlite to
inject this mock into the async_session dependency of the route handler. The tests will patch the return value of the
methods of this mock accordingly.

.. code-block:: python

    @pytest.fixture(autouse=True)
    def auto_configure_async_session_mock(
        self, request: "FixtureRequest"
    ) -> Generator[None, None, None]:
        mockers: Dict[str:Any] = getattr(request, "param", None) or {
            "scalars.return_value": mock.create_autospec(ScalarResult, instance=True)
        }
        self.async_session_mock.configure_mock(**mockers)
        yield
        self.async_session_mock.reset_mock(return_value=True, side_effect=True)


As all of the route handlers in the code above are using ``AsyncSession.scalars`` method to make queries, this fixture
automatically patches the return value of scalars method. ``scalars`` is a coroutine which returns an instance of
:class:`ScalarResult` when it is awaited which is why the return value of scalars method is a mock of
:class:`ScalarResult` with the autospec of its instance. Remember that our purpose is not to test the code of the
library. By mocking its classes, we are preventing them to run their complex code that deals with the I/O but to our
code, it is as if they are actually running.

The fixture accepts parametrized values if you want to configure mock with the return values of methods other than
scalars. Like this:

.. code-block:: python

    from sqlalchemy.engine.result import Result


    @pytest.mark.parameterize(
        "auto_configure_async_session_mock",
        [{"execute.return_value": mock.create_autospec(Result, instance=True)}],
        indirect=True,
    )
    def test_my_route_handler() -> None:
        ...

After each test, the fixture resets the mock for the next test to make sure that previously set attributes are not
reused.

.. code-block:: python

    async def test_get_company_by_id(self, async_test_client: AsyncTestClient) -> None:
        ...
        self.async_session_mock.configure_mock(
            **{"scalars.return_value.one_or_none.return_value": company}
        )
        ...

The test cases then set return value of methods ``one_or_none`` and ``all`` according to their use case.

.. code-block:: python

    async def test_get_all_companies(
        self, companies, async_test_client: AsyncTestClient
    ) -> None:
        self.async_session_mock.configure_mock(
            **{"scalars.return_value.all.return_value": companies}
        )
