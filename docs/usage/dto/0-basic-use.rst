Basic Use
=========

Data Transfer Objects (DTOs) are a powerful feature in Litestar that help you control how data flows in and out of your 
route handlers. They act as intermediaries that transform, validate, and filter data between your application's internal
models and the external API.

Why use DTOs?
~~~~~~~~~~~~~

DTOs solve several common API development challenges:

- **Data Filtering**: Control which fields are exposed in API responses (e.g., hide sensitive user information)
- **Input Validation**: Ensure incoming data meets your requirements before processing
- **Data Transformation**: Convert between different data formats or structures
- **API Versioning**: Maintain stable API contracts while evolving internal models
- **Security**: Prevent accidental exposure of internal data structures

.. seealso::
    For a comprehensive, step-by-step tutorial, see the :doc:`DTO Tutorial </tutorials/dto-tutorial/index>`.

Basic Example: Controlling Response Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's start with a simple example that demonstrates why DTOs are useful. Consider a user management system where we have
a ``User`` model but want to control what information is exposed in our API responses.

.. literalinclude:: /examples/data_transfer_objects/basic_example_complete.py
    :caption: A complete example showing the problem DTOs solve
    :language: python

In this example, without DTOs, the ``create_user`` endpoint would expose all user data, including the password hash.
With ``UserResponseDTO``, we can safely return user data while excluding sensitive fields.

Let's explore how to implement DTOs in your route handlers step by step.

Defining DTOs on handlers
~~~~~~~~~~~~~~~~~~~~~~~~~

Now that you understand the value of DTOs, let's explore how to use them in your route handlers. There are two key 
parameters that control DTOs in Litestar:

- ``dto``: Controls how incoming request data is parsed and validated
- ``return_dto``: Controls how response data is serialized (optional)

The object provided to both of these parameters must be a class that conforms to the
:class:`AbstractDTO <litestar.dto.base_dto.AbstractDTO>` protocol.

Understanding these parameters
------------------------------

.. important::
    DTOs work in two directions:
    
    - **Inbound**: Convert request data (JSON, form data, etc.) into Python objects
    - **Outbound**: Convert Python objects back into response data (JSON, etc.)

The ``dto`` parameter
---------------------

The ``dto`` parameter tells Litestar how to handle incoming request data. When a client sends data to your endpoint,
the DTO converts that data into a Python object that gets injected into your handler as the ``data`` parameter.

Additionally, if no ``return_dto`` is declared on the handler, this DTO will also be used to encode the return data.

.. literalinclude:: /examples/data_transfer_objects/the_dto_parameter.py
    :caption: Using the ``dto`` Parameter
    :language: python

In this example:

1. A client sends JSON data to ``POST /users``
2. ``UserDTO`` converts the JSON into a ``User`` object
3. The ``User`` object is passed to the handler as the ``data`` parameter
4. Since no ``return_dto`` is specified, ``UserDTO`` is also used to convert the returned ``User`` back to JSON

The ``return_dto`` parameter
----------------------------

When you need different behavior for input and output, use the ``return_dto`` parameter. This is common when you want to
accept certain fields in requests but exclude different fields in responses.

.. literalinclude:: /examples/data_transfer_objects/the_return_dto_parameter.py
    :caption: Using the ``return_dto`` Parameter
    :language: python

In this example:

1. ``UserInputDTO`` handles incoming data (excludes ``id`` and ``internal_notes``)
2. ``UserResponseDTO`` handles outgoing data (only excludes ``internal_notes``)
3. This allows clients to omit the ``id`` (which is auto-generated) while still including it in responses

Overriding implicit ``return_dto``
----------------------------------

If a ``return_dto`` type is not declared for a handler, the type declared for the ``dto`` parameter is used for both
decoding and encoding request and response data. If this behavior is undesirable, it can be disabled by explicitly
setting the ``return_dto`` to ``None``.

.. literalinclude:: /examples/data_transfer_objects/overriding_implicit_return_dto.py
    :caption: Disable implicit ``return_dto`` behavior
    :language: python

In this example, we use ``UserDTO`` to decode request data, and convert it into the ``User`` type, but we want to manage
encoding the response data ourselves, and so we explicitly declare the ``return_dto`` as ``None``.

Defining DTOs on layers
~~~~~~~~~~~~~~~~~~~~~~~

DTOs can be defined on any :ref:`Layer <layered-architecture>` of the application. The DTO type applied is the one
defined in the ownership chain, closest to the handler in question.

.. literalinclude:: /examples/data_transfer_objects/defining_dtos_on_layers.py
    :caption: Controller defined DTOs
    :language: python

In this example, the ``User`` instance received by any handler that declares a ``data`` kwarg is converted by the
``UserWriteDTO`` type, and all handler return values are converted into an encodable type by ``UserReadDTO`` (except for
the ``delete()`` route, which has the ``return_dto`` disabled).

DTOs can similarly be defined on :class:`Routers <litestar.router.Router>` and
:class:`The application <litestar.app.Litestar>` itself.


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
