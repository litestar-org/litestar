Basic Use
=========

DTOs (Data Transfer Objects) control how data is transformed between your application and external interfaces.
They handle validation, serialization, and field filtering for both incoming requests and outgoing responses.

This guide shows how to apply DTOs to your route handlers using two main parameters:

- ``dto``: Processes incoming request data
- ``return_dto``: Processes outgoing response data

.. literalinclude:: /examples/data_transfer_objects/basic_example_complete.py
    :caption: Complete example showing DTO benefits
    :language: python

DTO parameters
~~~~~~~~~~~~~~

Apply DTOs to any :ref:`Layer <layered-architecture>` using these parameters:

``dto``
    Processes incoming request data and converts it to the handler's expected type.
    Also used for response encoding if no ``return_dto`` is specified.

``return_dto``
    Processes outgoing response data. If not provided, the ``dto`` parameter handles both
    request and response processing.

Applying DTOs to handlers
~~~~~~~~~~~~~~~~~~~~~~~~~

Use the ``dto`` parameter to process incoming data:

.. literalinclude:: /examples/data_transfer_objects/the_dto_parameter.py
    :caption: Using the ``dto`` parameter
    :language: python

Use ``return_dto`` to process response data differently from request data:

.. literalinclude:: /examples/data_transfer_objects/the_return_dto_parameter.py
    :caption: Using the ``return_dto`` parameter
    :language: python

Set ``return_dto=None`` to disable automatic response processing:

.. literalinclude:: /examples/data_transfer_objects/overriding_implicit_return_dto.py
    :caption: Disabling response DTO
    :language: python

Applying DTOs to layers
~~~~~~~~~~~~~~~~~~~~~~~

Define DTOs on any :ref:`Layer <layered-architecture>` (Controller, Router, or Application) to apply them
to all contained handlers:

.. literalinclude:: /examples/data_transfer_objects/defining_dtos_on_layers.py
    :caption: Controller-level DTOs
    :language: python


Improving performance with the codegen backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

    This feature was introduced in ``2.2.0`` and was hidden behind the ``DTO_CODEGEN``
    feature flag. As of ``2.8.0`` it is considered stable and is enabled by default.
    It can still be disabled selectively by using the
    ``DTOConfig(experimental_codegen_backend=False)`` override.

The DTO backend is the part that does the heavy lifting for all the DTO features. It
is responsible for the transforming, validation and parsing. Because of this,
it is also the part with the most significant performance impact. To reduce the overhead
introduced by the DTOs, the DTO codegen backend was introduced; A DTO backend that
increases efficiency by generating optimized Python code at runtime to perform all the
necessary operations.

Disabling the backend
---------------------

You can use ``experimental_codegen_backend=False``
to disable the codegen backend selectively:

.. code-block:: python

    from dataclasses import dataclass
    from litestar.dto import DTOConfig, DataclassDTO


    @dataclass
    class Foo:
        name: str


    class FooDTO(DataclassDTO[Foo]):
        config = DTOConfig(experimental_codegen_backend=False)

Enabling the backend
--------------------

.. note:: This is a historical document meant for Litestar versions prior to 2.8.0
    This backend was enabled by default since 2.8.0

.. warning:: ``ExperimentalFeatures.DTO_CODEGEN`` is deprecated and will be removed in 3.0.0

.. dropdown:: Enabling DTO codegen backend
    :icon: git-pull-request-closed

    You can enable this backend globally for all DTOs by passing the appropriate feature
    flag to your Litestar application:

    .. code-block:: python

        from litestar import Litestar
        from litestar.config.app import ExperimentalFeatures

        app = Litestar(experimental_features=[ExperimentalFeatures.DTO_CODEGEN])


    or selectively for individual DTOs:

    .. code-block:: python

        from dataclasses import dataclass
        from litestar.dto import DTOConfig, DataclassDTO


        @dataclass
        class Foo:
            name: str


        class FooDTO(DataclassDTO[Foo]):
            config = DTOConfig(experimental_codegen_backend=True)

    The same flag can be used to disable the backend selectively:

    .. code-block:: python

        from dataclasses import dataclass
        from litestar.dto import DTOConfig, DataclassDTO


        @dataclass
        class Foo:
            name: str


        class FooDTO(DataclassDTO[Foo]):
            config = DTOConfig(experimental_codegen_backend=False)


Performance improvements
------------------------

These are some preliminary numbers showing the performance increase for certain
operations:

=================================== ===========
operation                           improvement
=================================== ===========
JSON to Python                      ~2.5x
JSON to Python (collection)         ~3.5x
Python to Python                    ~2.5x
Python to Python (collection)       ~5x
Python to JSON                      ~5.3x
Python to JSON (collection)         ~5.4x
=================================== ===========


.. seealso::
    If you are interested in technical details, check out
    https://github.com/litestar-org/litestar/pull/2388
