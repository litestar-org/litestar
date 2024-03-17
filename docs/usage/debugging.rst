Debugging
=========

Using the Python debugger
--------------------------

You can configure Litestar to drop into the :doc:`Python Debugger <python:library/pdb>`
when an exception occurs. This can be configured in different ways:

#. Configuring :class:`~litestar.app.Litestar` with the :paramref:`~litestar.app.Litestar.pdb_on_exception` option

    .. code-block:: python
        :caption: Using the :paramref:`~litestar.app.Litestar.pdb_on_exception` parameter

        app = Litestar(pdb_on_exception=True)

#. Using the ``--pdb`` flag when running your application via the CLI

    .. code-block:: shell
        :caption: Using the ``--pdb`` flag

        litestar run --pdb
#. Setting the ``LITESTAR_PDB`` environment variable
    ``LITESTAR_PDB=1``

Debugging with an IDE
---------------------

You can easily attach your IDEs debugger to your application, whether you are running it
via the CLI or a webserver like `uvicorn <https://www.uvicorn.org/>`_.

Intellij / PyCharm
++++++++++++++++++

Using the CLI
*************

.. dropdown:: Click to see the steps

        #. Create a new debug configuration via ``Run`` > ``Edit Configurations``
        #. Select ``Module name`` option and set it to ``litestar``
        #. Add the ``run`` parameter and optionally additional parameters you want to pass
           to the CLI

           .. image:: /images/debugging/pycharm-config-cli.png

        #. Run your application in the debugger via ``Run`` > ``Debug Litestar``

           .. image:: /images/debugging/pycharm-debug.png
                :align: center

.. important:: Breakpoints inside route handlers might not work correctly when used in conjunction
    with the ``--reload`` and ``--web-concurrency`` parameters. If you want to use the
    CLI while making use of these options, you can attach the debugger manually to the
    running uvicorn process via ``Run`` > ``Attach to process``.

Using uvicorn
*************

.. dropdown:: Click to see the steps

        #. Create a new debug configuration via ``Run`` > ``Edit Configurations``
        #. Select ``Module name`` option and set it to ``uvicorn``
        #. Add the ``app:app`` parameter (or the equivalent path to your application object)

           .. image:: /images/debugging/pycharm-config-uvicorn.png

        #. Run your application in the debugger via ``Run`` > ``Debug Litestar``

           .. image:: /images/debugging/pycharm-debug.png
                :align: center

VS Code
+++++++

Using the CLI
*************

.. dropdown:: Click to see the steps

        #. Add a new debugging configuration via ``Run`` > ``Add configuration``
            .. image:: /images/debugging/vs-code-add-config.png
                :align: center
        #. From the ``Select a debug configuration`` dialog, select ``Module``
            .. image:: /images/debugging/vs-code-select-config.png
        #. Enter ``litestar`` as the module name
            .. image:: /images/debugging/vs-code-config-litestar.png
        #. In the opened JSON file, alter the configuration as follows:
            .. code-block:: json
                :caption: Configuring the debugger to run your application via the CLI

                {
                    "name": "Python: Litestar app",
                    "type": "python",
                    "request": "launch",
                    "module": "litestar",
                    "justMyCode": true,
                    "args": ["run"]
                }

        #. Run your application via the debugger via ``Run`` > ``Start debugging``
            .. image:: /images/debugging/vs-code-debug.png
                :align: center

Using uvicorn
**************

.. dropdown:: Click to see the steps

        #. Add a new debugging configuration via ``Run`` > ``Add configuration``
            .. image:: /images/debugging/vs-code-add-config.png
                :align: center
        #. From the ``Select a debug configuration`` dialog, select ``Module``
            .. image:: /images/debugging/vs-code-select-config.png
        #. Enter ``uvicorn`` as the module name
            .. image:: /images/debugging/vs-code-config-litestar.png
        #. In the opened JSON file, alter the configuration as follows:
            .. code-block:: json
                :caption: Configuring the debugger to run your application via uvicorn

                {
                    "name": "Python: Litestar app",
                    "type": "python",
                    "request": "launch",
                    "module": "uvicorn",
                    "justMyCode": true,
                    "args": ["app:app"]
                }

        #. Run your application via the debugger via ``Run`` > ``Start debugging``
            .. image:: /images/debugging/vs-code-debug.png
                :align: center
