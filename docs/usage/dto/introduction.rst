What is a Data Transfer Object?
===============================

A Data Transfer Object (or DTO for short) is a simple object that is used by Starlite to transfer data from the client
:class:`connection <.connection.Request>` to a :class:`route handler <.handlers.HTTPRouteHandler>`,
and back again.

To Starlite, a DTO is any type that implements :class:`AbstractDTOInterface <.dto.AbstractDTOInterface>`. Before
examining the components of this interface, we'll examine the different ways that a DTO can be defined to handle
connection data.

DTO Usage
---------
In the following examples, we'll assume that we have a DTO called ``MyDTO``, that implements the
:class:`AbstractDTOInterface <.dto.AbstractDTOInterface>` for a data type called ``MyDataType``.

Decorator Parameters
~~~~~~~~~~~~~~~~~~~~

The most basic way to declare a DTO type for a route handler is to use the ``data_dto`` and ``return_dto`` parameters of
the :attr:`HTTPRouteHandler <.handlers.HTTPRouteHandler>` decorator.

.. code-block:: python

    @post(data_dto=MyDTO, return_dto=MyDTO)
    def my_handler(data: MyDataType) -> MyDataType:
        ...

In this example, Starlite uses ``MyDTO`` to convert the raw connection data into an instance of ``MyDataType`` and then
injects that into the handler. The handler then returns an instance of ``MyDataType``, which is then converted back into
raw connection data using ``MyDTO``.

In this example, both ``data_dto`` and ``return_dto`` are set to the same type, but they can be set to different types
to control differences in how data should be received from, and presented to clients.

Layered Declarations
~~~~~~~~~~~~~~~~~~~~

The DTO parameters for a route are resolved through the application layer hierarchy, so DTO types can be declared at any
layer of the application, where the type that is declared closest to the route handler will be used.

.. code-block:: python

    class MyController(Controller):
        data_dto = MyDTO
        return_dto = MyDTO

        @post()
        def my_handler(data: MyDataType) -> MyDataType:
            ...

        @get()
        def my_other_handler() -> MyDataType:
            ...

For the ``my_handler()`` route handler, there is no functional difference between this example and the previous one, the
same DTO type is applied for both the ``data`` kwarg and the return value.

However, in this example, the ``return_dto`` that is declared on the controller, is also used to convert the return
value of the ``my_other_handler()`` route handler.

``data_dto`` and ``return_dto`` can also be declared on :class:`routers <.router.Router>` and on the
:class:`application <.app.Starlite>` itself.

Handler Annotations
~~~~~~~~~~~~~~~~~~~

Finally, subclasses of :class:`AbstractDTOInterface <.dto.AbstractDTOInterface>` can be used to annotate the handler
function itself.

.. code-block:: python

    @post()
    def my_handler(data: MyDTO) -> MyDTO:
        ...

Here, the DTO type is received as the ``data`` kwarg into the handler, and returned by it. Starlite will handle the
rest.
