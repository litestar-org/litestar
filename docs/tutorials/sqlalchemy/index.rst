Improving the TODO app with SQLAlchemy
--------------------------------------

.. admonition:: Who is this tutorial for?
    :class: info

    This tutorial is aimed at developers who are already familiar with Litestar's core concepts such as route
    handlers and dependency injection.

    If you are new to Litestar, it is recommended to first follow the
    `Developing a basic TODO application <../todo-app>`_ tutorial.

Install SQLAlchemy
==================

To follow this tutorial, you will need SQLAlchemy installed. You can install it with ``pip install 'sqlalchemy[aiosqlite]'``, or let
Litestar install it for you by installing the ``sqlalchemy`` extra (e.g., ``pip install 'litestar[standard,sqlalchemy]' aiosqlite``).

What's in this tutorial?
========================

This tutorial builds on the `TODO app tutorial <../todo-app>`_ by adding a database backend using
`SQLAlchemy <https://www.sqlalchemy.org/>`_.

We start by comparing a refactored TODO app that leverages SQLAlchemy for data persistence to the TODO app from the
`TODO app tutorial <../todo-app>`_.

We will then gradually improve on the design of our app by utilising more of Litestar's features, such as dependency
injection, and plugins.

Contents
========

.. toctree::
    :titlesonly:

    0-introduction
    1-provide-session-with-di
    2-serialization-plugin
    3-init-plugin
    4-final-touches-and-recap
