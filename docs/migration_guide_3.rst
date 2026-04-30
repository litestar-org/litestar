:orphan:

Removal of Deprecated msgspec Contrib Namespace
===============================================

The deprecated msgspec contrib namespace has been removed in this release.

How to Migrate
--------------

Existing code that imports ``MsgspecDTO`` from the deprecated contrib namespace must be updated to use the new canonical location.

The canonical replacement for ``MsgspecDTO`` is now located at ``litestar.dto.MsgspecDTO``.

You can import it directly from ``litestar.dto``:

.. code-block:: python

    from litestar.dto import MsgspecDTO
