Parameters
==========

.. _parameter-types:


Request parameters are parts of the request that can be injected into a handler function
or dependency. They allow type-coercion, validation, and will show up in the generated
OpenAPI schema.

There are for request parameter types supported, which can be specified in two different
forms:

+--------+----------------------------+---------------------------------------------------------------------------+
| Type   | Short form                 | :class:`~typing.Annotated` Form                                           |
+========+============================+===========================================================================+
| query  | :data:`.params.FromQuery`  | :class:`Annotated[\<type\>, QueryParameter()] <.params.QueryParameter>`   |
+--------+----------------------------+---------------------------------------------------------------------------+
| path   | :data:`.params.FromPath`   | :class:`Annotated[\<type\>, PathParameter()] <.params.PathParameter>`     |
+--------+----------------------------+---------------------------------------------------------------------------+
| header | :data:`.params.FromHeader` | :class:`Annotated[\<type\>, HeaderParameter()] <.params.HeaderParameter>` |
+--------+----------------------------+---------------------------------------------------------------------------+
| cookie | :data:`.params.FromCookie` | :class:`Annotated[\<type\>, CookieParameter()] <.params.CookieParameter>` |
+--------+----------------------------+---------------------------------------------------------------------------+



Parameter declarations
----------------------

Each parameter source has two equivalent declaration forms: a marker type alias for the
common case, and an :class:`~typing.Annotated` form for when extra configuration is
needed:

.. tab-set::

    .. tab-item:: Marker form

        .. code-block:: python

            from litestar import get
            from litestar.params import FromCookie, FromHeader, FromPath, FromQuery

            @get("/{user_id:int}")
            async def handler(
                user_id: FromPath[int],
                limit: FromQuery[int],
                token: FromHeader[str],
                session: FromCookie[str],
            ) -> None: ...

    .. tab-item:: Annotated form

        .. code-block:: python

            from typing_extensions import Annotated

            from litestar import get
            from litestar.params import (
                CookieParameter,
                HeaderParameter,
                PathParameter,
                QueryParameter,
            )

            @get("/{user_id:int}")
            async def handler(
                user_id: Annotated[int, PathParameter(ge=1)],
                limit: Annotated[int, QueryParameter(gt=0, le=100)],
                token: Annotated[str, HeaderParameter(name="X-API-KEY")],
                session: Annotated[str, CookieParameter(name="session-id")],
            ) -> None: ...

The two forms are equivalent: ``FromQuery[T]`` is just an alias for
``Annotated[T, QueryParameter()]``. Prefer the marker form when no extra configuration
is needed.

.. admonition:: Technical details
    :class: info

    These :term:`parameters <parameter>` will be parsed from the function signature and
    used to generate an internal data model. This model in turn will be used to validate
    the parameters and generate the OpenAPI schema


.. seealso::
    :doc:`/topics/explicit_declarations`


Optional, required and nullable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Just like function parameters in Python, request parameters can be required, optional or
have a default value.

- Parameters declared without any default are required
- Parameters declared with a default are optional
- Parameters declared with ``| None`` are *nullable*, i.e. the may take a ``None``
  value; they are still required, unless they are given a default value

Defaults work exactly like defaults in regular function parameters: If the value is
missing from the request, the handler is called with the default:

.. literalinclude:: /examples/parameters/query_params_default.py
    :language: python
    :caption: Defining a default value for a query parameter

Marking a parameter optional means the type itself permits :obj:`None`:

.. literalinclude:: /examples/parameters/query_params_optional.py
    :language: python
    :caption: Defining an optional query parameter


.. important::
    Path parameters are always required because they are part of the URL itself. You can
    only get a "missing" path parameter when the same handler is registered against
    :ref:`multiple paths <usage/routing/parameters:path parameters>`
    (e.g. ``["/items", "/items/{id:int}"]``), in which case the handler-side default
    fills in for the path without the slot.


Parameter types
---------------

Path parameters
~~~~~~~~~~~~~~~

Path :term:`parameters <parameter>` are declared as part of the ``path`` component of
the URL using the syntax ``{param_name:param_type}``. The handler function receives the
value via a parameter of the same name, declared with :data:`~.params.FromPath`:

.. literalinclude:: /examples/parameters/path_parameters_1.py
    :language: python
    :caption: Defining a path parameter in a route handler

There are two components to declaring a path parameter:

1. In the :class:`@get() <.handlers.get>` :term:`decorator`, the path component
   declares both the parameter's name (``user_id``) and type (:class:`int`)
2. In the handler signature, ``user_id`` is declared as
   :data:`FromPath[int] <.params.FromPath>`, which tells Litestar to inject the matching
   path value

Two characteristics are unique to path parameters:

- The URL slot defines the structurally required type via the ``:type`` suffix (see
  :ref:`usage/routing/parameters:supported path parameter types` below). Litestar
  coerces the captured string into this type before passing it to the handler, and the
  handler-side type annotation can request a further coercion
  (see :ref:`usage/routing/parameters:type coercion`).
- Path parameters cannot be declared on application
  :ref:`layers <usage/applications:layered architecture>`

.. tip::
    You only need to declare the path :term:`parameter` in the function signature if the
    handler actually uses it. If the path parameter is part of the path but the function
    does not consume it, you can omit it from the signature; it will still be validated
    and added to the OpenAPI schema.


Supported path parameter types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following types are supported in the ``{name:type}`` slot:

* ``date``: Accepts date strings and time stamps.
* ``datetime``: Accepts date-time strings and time stamps.
* ``decimal``: Accepts decimal values and floats.
* :class:`float`: Accepts ints and floats.
* :class:`int`: Accepts ints and floats.
* :class:`path`: Accepts valid POSIX paths.
* :class:`str`: Accepts all string values.
* ``time``: Accepts time strings with optional timezone compatible with standard (Pydantic/Msgspec) datetime formats.
* ``timedelta``: Accepts duration strings compatible with the standard (Pydantic/Msgspec) timedelta formats.
* ``uuid``: Accepts all uuid values.

Query parameters
~~~~~~~~~~~~~~~~

Query :term:`parameters <parameter>` are declared as :term:`parameters <argument>` on
the handler function, typed with :data:`~.params.FromQuery` or
``Annotated[<type>, QueryParameter()]``.

.. literalinclude:: /examples/parameters/query_params.py
    :language: python
    :caption: Defining a query parameter in a route handler


Header parameters
~~~~~~~~~~~~~~~~~

Header :term:`parameters <parameter>` are declared with :data:`~.params.FromHeader` or
``Annotated[<type>, HeaderParameter()]``. The handler-side parameter name is used as the
header name by default; HTTP headers are matched case-insensitively, so
``token: FromHeader[str]`` matches both ``Token`` and ``token`` on the wire.

In practice, most headers you care about have names that are not valid Python
identifiers (e.g. ``X-API-KEY``, ``Content-Type``). In those cases, switch to
:class:`~typing.Annotated` and set ``name=`` on :class:`~.params.HeaderParameter`:

.. code-block:: python

    from typing_extensions import Annotated

    from litestar.params import HeaderParameter


    async def handler(token: Annotated[str, HeaderParameter(name="X-API-KEY")]) -> None: ...

Cookie parameters
~~~~~~~~~~~~~~~~~

Cookie :term:`parameters <parameter>` are declared with
:data:`~.params.FromCookie` or ``Annotated[<type>, CookieParameter()]``. The handler-side
parameter name is used as the cookie name by default:

.. code-block:: python

    from typing_extensions import Annotated

    from litestar.params import CookieParameter


    async def handler(session: Annotated[str, CookieParameter(name="session-id")]) -> None: ...

A combined example showing both header and cookie parameters alongside a path parameter:

.. literalinclude:: /examples/parameters/header_and_cookie_parameters.py
    :language: python
    :caption: Defining header and cookie parameters


Type coercion
-------------

Every parameter starts life on the wire as a string (or for path parameters, a string captured by the URL slot).
Litestar coerces that raw value into the inner type of the marker (``FromQuery[int]``, ``FromHeader[float]``,
``FromPath[datetime]``, …) before passing it to the handler:

.. literalinclude:: /examples/parameters/query_params_types.py
    :language: python
    :caption: Coercing query parameters into different types

Path parameters additionally support coercion via the path-slot type itself. The handler-side type does not need to
match the slot type one-to-one — if the slot captures an :class:`int` and the handler asks for a
:class:`~datetime.datetime`, Litestar applies the second conversion:

.. literalinclude:: /examples/parameters/path_parameters_2.py
    :language: python
    :caption: Coercing a path parameter into a different type

The same conversion rules apply to header and cookie parameters: ``FromHeader[int]`` will parse the header value as
an integer, ``FromCookie[datetime]`` will parse the cookie as a datetime, and so on.


Aliasing
--------

By default, the name of the function parameter is used to retrieve the parameter data
from the request. To decouple the two, for example to receive ``camelCase`` query keys
while keeping ``snake_case`` Python parameter names, or to declare an ``X-``-prefixed
header, pass ``name="..."`` to the matching specifier class:

.. literalinclude:: /examples/parameters/query_params_remap.py
    :language: python
    :caption: Remapping a query parameter to a different URL name

A request to ``http://127.0.0.1:8000?camelCase=foo`` will be received as
``snake_case="foo"`` inside the handler.

The same pattern applies to
:class:`~.params.HeaderParameter`,:class:`~.params.CookieParameter` and
:class:`~.params.PathParameter`.


Validation constraints
----------------------

All parameters can be given certain validation constraints, that will be validated when
a request is received, and represented in the OpenAPI schema.

Currently supported constraints are: ``gt``, ``ge``, ``lt``, ``le``, ``multiple_of``,
``min_length``, ``max_length``, ``min_items``, ``max_items``, and ``pattern``. A
value that does not satisfy the constraint raises
:exc:`~.exceptions.http_exceptions.ValidationException`:

.. literalinclude:: /examples/parameters/query_params_constraints.py
    :language: python
    :caption: Constraining a query parameter to integers larger than 5


OpenAPI metadata
----------------

Parameters can extend or alter their OpenAPI schema, e.g. to customize their title, add
a description or examples:

.. literalinclude:: /examples/parameters/path_parameters_3.py
    :language: python
    :caption: Adding  OpenAPI metadata to a path parameter


Customizing enum schemas
------------------------

By default, the OpenAPI schema generated for an enum-typed parameter uses the enum's
docstring for the description section of the schema. Overriding the description via
:attr:`~.params.KwargDefinition.description` would change it for every parameter sharing
that enum, because only one schema is generated per enum. To get distinct descriptions,
also pass :attr:`~.params.KwargDefinition.schema_component_key` so a separate schema
component is generated per parameter:

.. literalinclude:: /examples/parameters/query_params_enum.py
    :language: python
    :caption: Distinct OpenAPI components for parameters sharing the same enum type

In the above example, the schema for ``q1`` references a "q1" schema component with
description "This is q1"; the schema for ``q2`` references the shared "MyEnum" component
with description "My enum accepts two values"; and the schema for ``q3`` references a
"q3" component with description "This is q3".

Without the :attr:`~.params.KwargDefinition.schema_component_key` arguments on
``q1`` and ``q3``, all three would share the same "MyEnum" component with description
"This is q1" — whichever description was processed first wins.


Layered Parameters
------------------

As part of Litestar's :ref:`layered architecture <usage/applications:layered architecture>`, you can declare
:term:`parameters <parameter>` not only on individual route handler functions, but also on other layers of the
application:

.. literalinclude:: /examples/parameters/layered_parameters.py
    :language: python
    :caption: Declaring parameters on different layers of the application

In the above we declare :term:`parameters <parameter>` on the :class:`Litestar app <.app.Litestar>`,
:class:`router <.router.Router>`, and :class:`controller <.controller.Controller>` layers in addition to those
declared in the route handler. Examine these more closely:

* ``app_param`` is a cookie parameter with the key ``special-cookie``, declared via
  :class:`~.params.CookieParameter` on the :class:`Litestar app <.app.Litestar>` with ``annotation=str``.
  ``required=False`` makes it optional; without that argument it would be required by default.

  Because the route handler function does not declare ``app_param`` at all, the parameter is still extracted and
  validated at the application level even though the handler never sees it.

* ``router_param`` is a header parameter with the key ``MyHeader``, declared via :class:`~.params.HeaderParameter`
  on the router. It is declared ``required=False`` on the router, so it does not fail validation if absent — unless
  the handler explicitly opts in by re-declaring it (as this one does).

  The handler types it as :class:`FromHeader[str] <.params.FromHeader>` (rather than ``str | None``), making it
  required at the handler level. If a value *is* provided, it is also tested against the router-declared regex.

* ``controller_param`` is a query parameter with the key ``controller_param``, declared via
  :class:`~.params.QueryParameter` on the controller with ``lt=100`` (value must be less than 100). The handler
  redeclares it with ``Annotated[int, QueryParameter(lt=50)]``, tightening the constraint to less than 50 for this
  particular route.

* ``local_param`` is a route-handler-local :ref:`query parameter <usage/routing/parameters:query parameters>`
  (``FromQuery[str]``), and ``path_param`` is a :ref:`path parameter <usage/routing/parameters:path parameters>`
  (``FromPath[int]``).


.. _deprecated-parameter-styles:

Deprecated declaration styles
-----------------------------

Earlier 2.x releases accepted several other ways of declaring handler parameters. These continue to work for the
remainder of the 2.x line, but they now emit a :class:`~.exceptions.LitestarDeprecationWarning` and will be removed
in 3.0.

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - Deprecated
      - Use instead
    * - ``def h(name: str)`` *(implicit query parameter)*
      - ``def h(name: FromQuery[str])``
    * - ``def h(user_id: int)`` *(implicit path parameter)*
      - ``def h(user_id: FromPath[int])``
    * - ``Annotated[str, Parameter(query="alias")]``
      - ``Annotated[str, QueryParameter(name="alias")]``
    * - ``Annotated[str, Parameter(header="X-API-KEY")]``
      - ``Annotated[str, HeaderParameter(name="X-API-KEY")]``
    * - ``Annotated[str, Parameter(cookie="session")]``
      - ``Annotated[str, CookieParameter(name="session")]``
    * - ``name: str = Parameter(...)`` *(default-value style)*
      - ``name: Annotated[str, QueryParameter(...)]``

The :func:`~.params.Parameter` function itself is **not** removed and can still be used to attach pure metadata
(``description``, ``gt``, etc.) when wrapped in :class:`~typing.Annotated`. Only its ``header``, ``cookie``, and
``query`` keyword arguments are deprecated — passing any of those emits a :exc:`DeprecationWarning` independently of
the handler-level warning.
