.. py:currentmodule:: litestar


What's changed in 3.0?
======================

This document is an overview of the changes between version **2.11.x** and **3.0**.
For a detailed list of all changes, including changes between versions leading up to the
3.0 release, consult the :doc:`/release-notes/changelog`.

.. note:: The **2.11** release line is unaffected by this change

Imports
-------

+----------------------------------------------------+------------------------------------------------------------------------+
| ``2.11``                                           | ``3.x``                                                                |
+====================================================+========================================================================+
| **SECTION**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
+ Put your shit here from v2                         | Put your shit here from v3                                             |
+----------------------------------------------------+------------------------------------------------------------------------+


Implicit Optional Default Parameters
------------------------------------

In v2, if a handler was typed with an optional parameter it would be implicitly given a default value of ``None``. For
example, if the following handler is called with no query parameter, the value ``None`` would be passed in to the
handler for the ``param`` parameter:

.. code-block:: python

    @get("/")
    def my_handler(param: int | None) -> ...:
        ...

This legacy behavior originates from our history of using Pydantic v1 models to represent handler signatures. In v3, we
no longer make this implicit conversion. If you want to have a default value of ``None`` for an optional parameter, you
must explicitly set it:

.. code-block:: python

    @get("/")
    def my_handler(param: int | None = None) -> ...:
        ...
