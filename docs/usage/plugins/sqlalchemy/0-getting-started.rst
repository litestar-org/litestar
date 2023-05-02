Getting Started
---------------

To demonstrate working with `SQLAlchemy <https://docs.sqlalchemy.org/>`_ in a Litestar application, we will re-develop
the `TODO Application <tutorials/todo-app/3-assembling-the-app.html#final-application>`_ from the Litestar tutorial, but
using SQLAlchemy for our data modelling.

Installation
~~~~~~~~~~~~

You will need to install SQLAlchemy alongside Litestar to follow along. You can do this by running
``pip install litestar[standard,sqlalchemy]``. This will install Litestar, SQLAlchemy, and
`uvicorn <https://www.uvicorn.org/>`_.
