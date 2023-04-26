SQLAlchemy Plugins
==================

We here at Litestar love the SQLAlchemy project. It has stood the test of time, is well documented, has a large
community, and first-class maintainers. For all of these reasons, is a great choice for any Python project that needs to
work with a relational database, and we are proud to support it.

Litestar comes with built-in support for `SQLAlchemy <https://docs.sqlalchemy.org/>`_ via
a suite of :class:`Plugins <.contrib.sqlalchemy.plugins>`.

Features
--------

* Managed `sessions <https://docs.sqlalchemy.org/en/20/orm/session.html>`_ (sync and async) including dependency injection
* Managed `engine <https://docs.sqlalchemy.org/en/20/core/engines.html>`_ (sync and async) including dependency injection
* Typed configuration objects
* Support for deserializing into, and serializing from, SQLAlchemy models.


.. toctree::
    :titlesonly:
    :hidden:

    0-getting-started
    1-data-modelling
