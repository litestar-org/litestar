FAQ & Common Recipes
====================

This section contains answers to frequently asked questions and common recipes
for solving typical problems.

.. contents:: Table of Contents
    :local:
    :depth: 2

How do I see stack traces in error responses?
---------------------------------------------

By default, Litestar returns minimal error information in production for security
reasons. To see full stack traces during development:

**Option 1: Enable debug mode**

.. code-block:: python

    from litestar import Litestar

    app = Litestar(
        route_handlers=[...],
        debug=True,  # Enables detailed error responses
    )

When ``debug=True``, exceptions will include full stack traces in the response.

.. warning::
    Never enable debug mode in production as it can expose sensitive information.

**Option 2: Use the CLI debug flag**

When running your application with the Litestar CLI:

.. code-block:: bash

    litestar run --debug

.. note::
    This FAQ section is a work in progress. Contributions are welcome!
