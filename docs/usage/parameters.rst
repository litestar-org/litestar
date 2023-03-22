Parameters
===========

Path Parameters
---------------

Path parameters are parameters declared as part of the ``path`` component of the URL. They are declared using a simple
syntax ``{param_name:param_type}`` :

.. literalinclude:: /examples/parameters/path_parameters_1.py
    :language: python



In the above there are two components:

1. The path parameter is defined in the ``@get`` decorator, which declares both the parameter's name ``user_id``) and type ``int``.
2. The decorated function ``get_user`` defines a parameter with the same name as the parameter defined in the ``path`` kwarg.

The correlation of parameter name ensures that the value of the path parameter will be injected into the function when
it's called.

Supported Path Parameter Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Currently, the following types are supported:


* ``date``: Accepts date strings and time stamps.
* ``datetime``: Accepts date-time strings and time stamps.
* ``decimal``: Accepts decimal values and floats.
* ``float``: Accepts ints and floats.
* ``int``: Accepts ints and floats.
* ``path``: Accepts valid POSIX paths.
* ``str``: Accepts all string values.
* ``time``: Accepts time strings with optional timezone compatible with pydantic formats.
* ``timedelta``: Accepts duration strings compatible with the pydantic formats.
* ``uuid``: Accepts all uuid values.

The types declared in the path parameter and the function do not need to match 1:1 - as long as parameter inside the
function declaration is typed with a "higher" type to which the lower type can be coerced, this is fine. For example,
consider this:

.. literalinclude:: /examples/parameters/path_parameters_2.py
    :language: python



The parameter defined inside the ``path`` kwarg is typed as :class:`int` , because the value passed as part of the request will be
a timestamp in milliseconds without any decimals. The parameter in the function declaration though is typed
as :class:`datetime.datetime`. This works because the int value will be passed to a pydantic model representing the function
signature, which will coerce the int into a datetime. Thus, when the function is called it will be called with a
datetime typed parameter.

.. note::

    You only need to define the parameter in the function declaration if it's actually used inside the function. If the
    path parameter is part of the path, but the function doesn't use it, it's fine to omit it. It will still be validated
    and added to the openapi schema correctly.


Extra validation and documentation for path params
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to add validation or enhance the OpenAPI documentation generated for a given path parameter, you can do
so using the `the parameter function`_:

.. literalinclude:: /examples/parameters/path_parameters_3.py
    :language: python


In the above example, :class:`Parameter <.params.Parameter>` is used to restrict the value of ``version`` to a range
between 1 and 10, and then set the ``title``, ``description``, ``examples`` and ``externalDocs`` sections of the
OpenAPI schema.


Query Parameters
----------------

Query parameters are defined as keyword arguments to handler functions. Every keyword argument
that is not otherwise specified (for example as a :ref:`path parameter <usage/parameters:path parameters>`)
will be interpreted as a query parameter.

.. literalinclude:: /examples/parameters/query_params.py
    :language: python


.. admonition:: Technical details
    :class: info

    These parameters will be parsed from the function signature and used to generate a pydantic model.
    This model in turn will be used to validate the parameters and generate the OpenAPI schema.

    This means that you can also use any pydantic type in the signature, and it will
    follow the same kind of validation and parsing as you would get from pydantic.

Query parameters come in three basic types:


- Required
- Required with a default value
- Optional with a default value

Query parameters are **required** by default. If one such a parameter has no value,
a :class:`ValidationException <.exceptions.http_exceptions.ValidationException>` will be raised.

Settings defaults
~~~~~~~~~~~~~~~~~~

In this example, ``param`` will have the value ``"hello"`` if it's not specified in the request.
If it's passed as a query parameter however, it will be overwritten:

.. literalinclude:: /examples/parameters/query_params_default.py
    :language: python


Optional parameters
~~~~~~~~~~~~~~~~~~~

Instead of only setting a default value, it's also possible to make a query parameter
entirely optional.

Here, we give a default value of ``None`` , but still declare the type of the query parameter
to be a string. This means that this parameter is not required. If it is given, it has to be a string.
If it is not given, it will have a default value of ``None``

.. literalinclude:: /examples/parameters/query_params_optional.py
    :language: python


Type coercion
-------------

It is possible to coerce query parameters into different types. A query starts out as a string,
but its values can be parsed into all kinds of types. Since this is done by pydantic,
everything that works there will work for query parameters as well.

.. literalinclude:: /examples/parameters/query_params_types.py
    :language: python



Specifying alternative names and constraints
--------------------------------------------

Sometimes you might want to "remap" query parameters to allow a different name in the URL
than what's being used in the handler function. This can be done by making use of
:func:`Parameter <.params.Parameter>`.

.. literalinclude:: /examples/parameters/query_params_remap.py
    :language: python


Here, we remap from ``snake_case`` in the handler function to ``camelCase`` in the URL.
This means that for the URL ``http://127.0.0.1:8000?camelCase=foo`` , the value of ``camelCase``
will be used for the value of the ``snake_case`` parameter.

``Parameter`` also allows us to define additional constraints:

.. literalinclude:: /examples/parameters/query_params_constraints.py
    :language: python


In this case, ``param`` is validated to be an *integer larger than 5*.



Header and Cookie Parameters
----------------------------

Unlike *Query* parameters, *Header* and *Cookie* parameters have to be declared using
`the parameter function`_ , for example:

.. literalinclude:: /examples/parameters/header_and_cookie_parameters.py
    :language: python



As you can see in the above, header parameters are declared using the ``header`` kwargs and cookie parameters using
the ``cookie`` kwarg. Aside form this difference they work the same as query parameters.



The Parameter Function
-----------------------

:class:`Parameter <.params.Parameter>` is a wrapper on top of the
pydantic `Field function <https://pydantic-docs.helpmanual.io/usage/schema/#field-customization>`_ that extends it with a
set of Starlite specific kwargs. As such, you can use most of the kwargs of *Field* with Parameter and have the same
parsing and validation. The additional kwargs accepted by ``Parameter`` are passed to the resulting pydantic ``FieldInfo``
as an ``extra`` dictionary and have no effect on the working of pydantic itself.



Layered Parameters
-------------------

As part of Starlite's "layered" architecture, you can declare parameters not only as part of individual route handler
functions, but also on other layers of the application:

.. literalinclude:: /examples/parameters/layered_parameters.py
    :language: python



In the above we declare parameters on the app, router and controller levels in addition to those declared in the route
handler. Let's look at these closer.


* ``app_param`` is a cookie param with the key ``special-cookie``. We type it as ``str`` by passing this as an arg to
  the ``Parameter`` function. This is required for us to get typing in the OpenAPI docs. Additionally, this parameter is
  assumed to be required because it is not explicitly declared as ``required=False``. This is important because the route
  handler function does not declare a parameter called ``app_param`` at all, but it will still require this param to be
  sent as part of the request of validation will fail.
* ``router_param`` is a header param with the key ``MyHeader``. Because its declared as ``required=False`` , it will not fail
  validation if not present unless explicitly declared by a route handler - and in this case it is. Thus, it is actually
  required for the router handler function that declares it as an ``str`` and not an ``Optional[str]``. If a string value is
  provided, it will be tested against the provided regex.
* ``controller_param`` is a query param with the key ``controller_param``. It has an ``lt=100`` defined on the controller,
  which
  means the provided value must be less than 100. Yet the route handler re-declares it with an ``lt=50`` , which means for
  the route handler this value must be less than 50.
* ``local_param`` is a route handler local query parameter, and ``path_param`` is a path parameter.

.. note::

   You cannot declare path parameters in different application layers. The reason for this is to ensure
   simplicity - otherwise parameter resolution becomes very difficult to do correctly.
