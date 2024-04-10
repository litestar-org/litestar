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



Removal of ``StaticFileConfig``
-------------------------------

The ``StaticFilesConfig`` has been removed, alongside these related parameters and
functions:

- ``Litestar.static_files_config``
- ``Litestar.url_for_static_asset``
- ``Request.url_for_static_asset``

:func:`create_static_files_router` is a drop-in replacement for ``StaticFilesConfig``,
and can simply be added to the ``route_handlers`` like any other regular handler.

Usage of ``url_for_static_assets`` should be replaced with a ``url_for("static", ...)``
call.


Other Changes
-------------

Make more sections as they are appropriate :)
