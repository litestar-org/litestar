Providing the session with DI
-----------------------------


In our original script, we had to repeat the logic to construct a session instance for every request type. This is not
very `DRY <https://en.wikipedia.org/wiki/Don%27t_repeat_yourself>`_.

In this section, we'll use dependency injection to centralize the session creation logic and make it available to all
handlers.

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_session_di.py
    :language: python
    :linenos:
    :emphasize-lines: 49-59,84-85,89-91,96-97,105

In the previous example, the database session is created within each HTTP route handler function. In this script we use
dependency injection to decouple creation of the session from the route handlers.

This script introduces a new async generator function called ``provide_transaction()`` that creates a new SQLAlchemy
session, begins a transaction, and handles any integrity errors that might raise from within the transaction.

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_session_di.py
    :language: python
    :linenos:
    :lines: 50-59

That function is declared as a dependency to the Litestar application, using the name ``transaction``.

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_session_di.py
    :language: python
    :linenos:
    :lines: 103-107
    :emphasize-lines: 3

In the route handlers, the database session is injected by adding a parameter named ``transaction`` and marking it with
:data:`~litestar.di.NamedDependency`. The marker tells Litestar to supply the value from the ``transaction`` dependency
at runtime, matching the parameter name against the dependency key.


.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_session_di.py
    :language: python
    :linenos:
    :lines: 83-86
    :emphasize-lines: 2

One final improvement in this script is exception handling. In the previous version, a
:class:`litestar.exceptions.ClientException` is raised inside the ``add_item()`` handler if there's an integrity error
raised during the insertion of the new TODO item. In our latest revision, we've been able to centralize this handling
to occur inside the ``provide_transaction()`` function.

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_session_di.py
    :language: python
    :linenos:
    :lines: 49-59
    :emphasize-lines: 3,6-10

This change broadens the scope of exception handling to any operation that uses the database session, not just the
insertion of new items.

Compare handlers before and after DI
====================================

Just for fun, lets compare the sets of application handlers before and after we introduced dependency injection for our
session object:

.. tab-set::

   .. tab-item:: After

        .. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_session_di.py
            :language: python
            :linenos:
            :lines: 83-107

   .. tab-item:: Before

        .. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_no_plugins.py
            :language: python
            :linenos:
            :lines: 70-101

Much better!

Next steps
==========

One of the niceties that we've lost is the ability to receive and return data to/from our handlers as instances of our
data model. In the original TODO application, we modelled with Python dataclasses which are natively supported for
(de)serialization by Litestar. In the next section, we will look at how we can get this functionality back!
