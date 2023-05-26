Debugging
=========

Using the Python debugger
--------------------------

You can configure Litestar to drop into the :doc:`Python Debugger <python:library/pdb>`
when an exception occurs. This can be configured in different ways:

Configuring ``Litestar`` with the ``pdb_on_exception`` option
    .. code-block:: python

        app = Litestar(pdb_on_exception=True)


Running your app with the CLI and using the ``--pdb`` flag
    .. code-block:: shell

        litestar run --pdb

Using the ``LITESTAR_PDB`` environment variable
    ``LITESTAR_PDB=1``


Debugging with an IDE
---------------------

You can easily attach your IDEs debugger to your application, whether you're running it
via the CLI or a webserver like `uvicorn <https://www.uvicorn.org/>`_.

Intellij / PyCharm
++++++++++++++++++

Using the CLI
*************

1. Create a new debug configuration via ``Run`` > ``Edit Configurations``
2. Select ``Module name`` option and set it to ``litestar``
3. Add the ``run`` parameter and optionally additional parameters you want to pass
   to the CLI

   .. image:: /images/debugging/pycharm-config-cli.png

4. Run your application in the debugger via ``Run`` > ``Debug Litestar``

   .. image:: /images/debugging/pycharm-debug.png
        :align: center


.. important::
    Breakpoints inside route handlers might not work correctly when used in conjunction
    with the ``--reload`` and ``--web-concurrency`` parameters. If you want to use the
    CLI while making use of these options, you can attach the debugger manually to the
    running uvicorn process via ``Run`` > ``Attach to process``.


Using uvicorn
*************

1. Create a new debug configuration via ``Run`` > ``Edit Configurations``
2. Select ``Module name`` option and set it to ``uvicorn``
3. Add the ``app:app`` parameter (or the equivalent path to your application object)

   .. image:: /images/debugging/pycharm-config-uvicorn.png

4. Run your application in the debugger via ``Run`` > ``Debug Litestar``

   .. image:: /images/debugging/pycharm-debug.png
        :align: center


VS Code
+++++++


Using the CLI
*************


1. Open the debugging configurations via ``Run`` > ``Open configurations``
   .. image:: /images/debugging/vs-code-config.png
2. Add the following configuration:
    .. code-block:: json

        {
            "name": "Python: Litestar app",
            "type": "python",
            "request": "launch",
            "module": "litestar",
            "justMyCode": true,
            "args": ["run"]
        }

3. Run your application via the debugger via ``Run`` > ``Start debugging``
    .. image:: /images/debugging/vs-code-debug.png


Using uvicorn
**************

1. Open the debugging configurations via ``Run`` > ``Open configurations``
    .. image:: /images/debugging/vs-code-config.png
2. Add the following configuration:
    .. code-block:: json

        {
          "name": "Python: Litestar app",
          "type": "python",
          "request": "launch",
          "module": "uvicorn",
          "justMyCode": true,
          "args": ["app:app"]
        }

3. Run your application via the debugger via ``Run`` > ``Start debugging``
    .. image:: /images/debugging/vs-code-debug.png
