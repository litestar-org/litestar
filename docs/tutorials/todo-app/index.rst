A TODO application
==================

.. note::
    This tutorial is intended to familiarize you with the basic concepts of Litestar.
    If you have no prior experience with Litestar or web frameworks in general, this
    is the right place to start


The goal of this tutorial is to develop a TODO application with the following functionalities:

1. Create, update and delete TODO lists
2. Add to and delete items from TODO lists
3. Mark TODO items as *done*

This is not a whole lot of functionality, but enough to require most of the fundamental
working blocks of Litestar.

First steps
------------
Before we start building our TODO application, let's start with the basics.


Install Litestar
++++++++++++++++

To install Litestar, run ``pip install litestar[standard]``. This will
install Litestar and a few dependencies that we'll be making use of during this tutorial.
It will also install `uvicorn <https://www.uvicorn.org/>`_ -  a server that we can use
to serve our application.


Hello, world!
+++++++++++++

The most basic application we can implement is one that simply returns the string
"Hello, world!":


.. literalinclude:: examples/hello_world.py
    :language: python


Now save the contents of this example in a file called ``app.py`` and type
``litestar run`` in your terminal. This will serve the application locally on your
machine. Now visit http://127.0.0.1:8000/ in your browser:

.. image:: images/hello_world.png


.. toctree::
    :titlesonly:
    :hidden:

    0-application-basics
    1-todo.rst
