Configuring schema generation
-----------------------------

OpenAPI schema generation is enabled by default. To configure it you can pass an instance of
:class:`OpenAPIConfig <.openapi.OpenAPIConfig>` to the :class:`Litestar <litestar.app.Litestar>` class using the
``openapi_config`` kwarg:

.. code-block:: python

   from litestar import Litestar
   from litestar.openapi import OpenAPIConfig

   app = Litestar(
       route_handlers=[...], openapi_config=OpenAPIConfig(title="My API", version="1.0.0")
   )



Disabling schema generation
+++++++++++++++++++++++++++

If you wish to disable schema generation and not include the schema endpoints in your API, simply pass ``None`` as the
value for ``openapi_config``:

.. code-block:: python

   from litestar import Litestar

   app = Litestar(route_handlers=[...], openapi_config=None)



Configuring schema generation on a route handler
-------------------------------------------------

By default, an `operation <https://spec.openapis.org/oas/latest.html#operation-object>`_ schema is generated for all route
handlers. You can omit a route handler from the schema by setting ``include_in_schema=False``:

.. code-block:: python

   from litestar import get


   @get(path="/some-path", include_in_schema=False)
   def my_route_handler() -> None: ...

You can also modify the generated schema for the route handler using the following kwargs:


``tags``
    A list of strings that correlate to the `tag specification <https://spec.openapis.org/oas/latest.html#tag-object>`_.

``security``:
    A list of dictionaries that correlate to the
    `security requirements specification <https://spec.openapis.org/oas/latest.html#securityRequirementObject>`_. The
    values for this key are string keyed dictionaries with the values being a list of objects. An empty list
    (``security=[]``), on a handler, controller or router, lifts the requirements declared on the layers above it
    and in the :class:`OpenAPIConfig <.openapi.OpenAPIConfig>`.

``summary``
    Text used for the route's schema *summary* section.

``description``
    Text used for the route's schema *description* section.

``response_description``
    Text used for the route's response schema *description* section.

``operation_class``
    A subclass of :class:`Operation <.openapi.spec.operation.Operation>` which can be used to fully
    customize the `operation object <https://spec.openapis.org/oas/v3.1.0#operation-object>`_ for the handler.

``operation_id``
    A string or callable that returns a string, which servers as an identifier used for the route's schema *operationId*.

``deprecated``
    A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema. Defaults
    to ``False``.

``raises``
    A list of exception classes extending from ``litestar.HttpException``. This list should describe all
    exceptions raised within the route handler's function/method. The Litestar ``ValidationException`` will be added
    automatically for the schema if any validation is involved (e.g. there are parameters specified in the
    method/function). For custom exceptions, a `detail` class property should be defined, which will be integrated
    into the OpenAPI schema. If `detail` isn't specified and the exception's status code matches one
    from `stdlib status code <https://docs.python.org/3/library/http.html#http-status-codes>`_, a generic message
    will be applied.

``responses``
    A dictionary of additional status codes and a description of their expected content.
    The expected content should be based on a Pydantic model describing its structure. It can also include
    a description and the expected media type. For example:

.. note::

    `operation_id` will be prefixed with the method name when function is decorated with `HTTPRouteHandler` and multiple
    `http_method`. Will also be prefixed with path strings used in `Routers` and `Controllers` to make sure id is unique.

.. code-block:: python

   from datetime import datetime
   from typing import Optional

   from pydantic import BaseModel

   from litestar import get
   from litestar.openapi.datastructures import ResponseSpec


   class Item(BaseModel): ...


   class ItemNotFound(BaseModel):
       was_removed: bool
       removed_at: Optional[datetime]


   @get(
       path="/items/{pk:int}",
       responses={
           404: ResponseSpec(
               data_container=ItemNotFound, description="Item was removed or not found"
           )
       },
   )
   def retrieve_item(pk: int) -> Item: ...

You can also specify ``security`` and ``tags`` on higher level of the application, e.g. on a controller, router, or the
app instance itself. For example:

.. code-block:: python

   from litestar import Litestar, get
   from litestar.openapi import OpenAPIConfig
   from litestar.openapi.spec import Components, SecurityScheme, Tag


   @get(
       "/public",
       tags=["public"],
       security=[{}],  # this endpoint is marked as having optional security
   )
   def public_path_handler() -> dict[str, str]:
       return {"hello": "world"}


   @get("/other", tags=["internal"], security=[{"apiKey": []}])
   def internal_path_handler() -> None: ...


   app = Litestar(
       route_handlers=[public_path_handler, internal_path_handler],
       openapi_config=OpenAPIConfig(
           title="my api",
           version="1.0.0",
           tags=[
               Tag(name="public", description="This endpoint is for external users"),
               Tag(name="internal", description="This endpoint is for internal users"),
           ],
           security=[{"BearerToken": []}],
           components=Components(
               security_schemes={
                   "BearerToken": SecurityScheme(
                       type="http",
                       scheme="bearer",
                   )
               },
           ),
       ),
   )


Customizing error responses
---------------------------

By default, the responses generated for the exceptions listed in a route handler's ``raises``, and the 400 response
added to operations that receive parameters or a request body, describe Litestar's default exception response: a JSON
object with ``status_code``, ``detail`` and ``extra``. If your application returns a different shape, for example
through ``exception_handlers``, set ``error_response`` to a
:class:`ResponseSpec <litestar.openapi.datastructures.ResponseSpec>` whose ``data_container`` is the model of your
error body:

.. code-block:: python

   from dataclasses import dataclass

   from litestar import Litestar
   from litestar.openapi import OpenAPIConfig
   from litestar.openapi.datastructures import ResponseSpec


   @dataclass
   class APIError:
       code: str
       message: str


   app = Litestar(
       route_handlers=[...],
       openapi_config=OpenAPIConfig(
           title="My API",
           version="1.0.0",
           error_response=ResponseSpec(APIError, media_type="application/problem+json"),
       ),
   )

Every generated error response then references that model's schema under the given media type. The description of
each response is still derived from its status code and exceptions, so the ``description`` of the spec is not used,
and examples are only generated when ``create_examples`` is enabled as well. An entry for the same status code in a
handler's ``responses`` takes precedence.

If every error is returned as :rfc:`9457` problem details, by using
:class:`ProblemDetailsPlugin <litestar.plugins.problem_details.ProblemDetailsPlugin>` with
``enable_for_all_http_exceptions=True``, document them with
``ResponseSpec(ProblemDetails, media_type="application/problem+json")``, where ``ProblemDetails`` is imported from
:mod:`litestar.plugins.problem_details`.

Generating an OpenAPI 3.2 document
----------------------------------

The generated document conforms to version 3.1 of the OpenAPI Specification by default. To generate an OpenAPI 3.2
document, set ``openapi_version``:

.. code-block:: python

   from litestar import Litestar
   from litestar.openapi import OpenAPIConfig

   app = Litestar(
       route_handlers=[...],
       openapi_config=OpenAPIConfig(title="My API", version="1.0.0", openapi_version="3.2.0"),
   )

With OpenAPI 3.2:

- Handlers of the ``QUERY`` HTTP method, created with :func:`query <litestar.handlers.query>`, are documented. An
  OpenAPI 3.1 document cannot describe them, so they are left out of it.
- The events of a handler returning :class:`ServerSentEvent <litestar.response.ServerSentEvent>`, and the items of a
  :class:`Stream <litestar.response.Stream>` of JSON Lines, are described with ``itemSchema``.
- The URI of the document can be set with ``self_uri``.
- The fields OpenAPI 3.2 added, such as ``Tag.parent``, ``Server.name`` or ``SecurityScheme.oauth2_metadata_url``,
  can be used. They are available on the classes in :mod:`litestar.openapi.spec` and are only valid in a 3.2 document.

.. note::

    Not all documentation UIs and client generators support OpenAPI 3.2 yet. Of the UIs Litestar provides, Swagger UI,
    Redoc and Scalar render OpenAPI 3.2 documents, including ``QUERY`` operations. Stoplight Elements renders them
    too, but leaves out ``QUERY`` operations.

Customizing component schema names
----------------------------------

Models are documented once in the ``components/schemas`` section of the schema and referenced wherever they are used.
A component is named after its type, followed by the names of its type arguments if the type is a parametrized
generic: ``Page[Item]`` becomes ``Page_Item``. If two different types end up with the same name, the names are told
apart by the modules the types are defined in.
Different types that also share their module, such as classes created by a factory function, share one component if
their schemas are equal, including the schemas of the classes they refer to, and are numbered in the order they are
registered otherwise:
``Thing``, ``Thing_2``. The numbers can change when route handlers are registered in a different order.

To use different names, pass a callable to the ``schema_component_name_creator`` parameter of
:class:`OpenAPIConfig <.openapi.OpenAPIConfig>`. It receives the
:class:`FieldDefinition <litestar.typing.FieldDefinition>` of the type and returns the name:

.. code-block:: python

   from litestar import Litestar
   from litestar.openapi import OpenAPIConfig
   from litestar.typing import FieldDefinition


   def create_component_name(field_definition: FieldDefinition) -> str:
       name = field_definition.annotation.__name__
       type_arguments = "".join(t.annotation.__name__ for t in field_definition.inner_types)
       return f"{type_arguments}{name}"  # Page[Item] -> ItemPage


   app = Litestar(
       route_handlers=[...],
       openapi_config=OpenAPIConfig(
           title="My API",
           version="1.0.0",
           schema_component_name_creator=create_component_name,
       ),
   )

The name of a single usage of a type can be set with ``schema_component_key``, e.g.
``Annotated[Item, Body(schema_component_key="NewItem")]``. That usage then gets a component of its own.

Accessing the OpenAPI schema in code
------------------------------------

The OpenAPI schema is generated during the :class:`Litestar <litestar.app.Litestar>` app's init method. Once init is finished,
its accessible as ``app.openapi_schema``. As such you can always access it inside route handlers, dependencies, etc. by
access the request instance:

.. code-block:: python

   from litestar import Request, get


   @get(path="/")
   def my_route_handler(request: Request) -> dict:
       schema = request.app.openapi_schema
       return schema.to_schema()


Adding specification extensions to a schema
-------------------------------------------

The ``schema_extra`` of a parameter, a request body or a field sets attributes of the generated
:class:`~litestar.openapi.spec.Schema`. A key that starts with ``x-`` is emitted as a
`specification extension <https://spec.openapis.org/oas/v3.1.0#specification-extensions>`_ of that schema, and so is
an ``x-`` key in the ``json_schema_extra`` of a Pydantic field:

.. code-block:: python

   from typing import Annotated

   from litestar import get
   from litestar.params import QueryParameter


   @get("/")
   async def handler(limit: Annotated[int, QueryParameter(schema_extra={"x-internal": True})] = 10) -> None: ...

The parameter is documented with the schema ``{"type": "integer", "default": 10, "x-internal": true}``. For a type
documented as a component, the extension is added next to the reference and the shared component is unchanged. Any
other key that is not an attribute of ``Schema`` raises a :exc:`ValueError`. A schema built in code holds its
extensions in ``Schema.extensions``.

Customizing Pydantic model schemas
----------------------------------

You can customize the OpenAPI schemas generated for pydantic models by following the guidelines in
the `Pydantic docs <https://docs.pydantic.dev/latest/usage/json_schema/>`_.

Additionally, you can affect how pydantic models are translated into OpenAPI ``components`` by settings a special dunder
attribute on the model called ``__schema_name__``:

.. literalinclude:: /examples/openapi/customize_pydantic_model_name.py
    :caption: Customize Components Example
    :language: python


The above will result in an OpenAPI schema object that looks like this:

.. code-block:: json

   {
       "openapi": "3.1.0",
       "info": {"title": "Litestar API", "version": "1.0.0"},
       "servers": [{"url": "/"}],
       "paths": {
           "/id": {
               "get": {
                   "operationId": "Retrieve Id Handler",
                   "responses": {
                       "200": {
                           "description": "Request fulfilled, document follows",
                           "headers": {},
                           "content": {
                               "application/json": {
                                   "schema": {
                                       "$ref": "#/components/schemas/IdContainer"
                                   }
                               }
                           }
                       }
                   },
                   "deprecated": false
               }
           }
       },
       "components": {
           "schemas": {
               "IdContainer": {
                   "properties": {
                       "id": {"type": "string", "format": "uuid", "title": "Id"}
                   },
                   "type": "object",
                   "required": ["id"],
                   "title": "IdContainer"
               }
           }
       }
   }

.. attention::

   If you use multiple pydantic models that use the same name in the schema, you will need to use the `__schema_name__`
   dunder to ensure each has a unique name in the schema, otherwise the schema components will be ambivalent.



Customizing ``Operation`` class
-------------------------------

You can customize the `operation object <https://spec.openapis.org/oas/v3.1.0#operation-object>`_ used for a path in
the generated OpenAPI schemas by creating a subclass of :class:`Operation <.openapi.spec.operation.Operation>`.

This option can be helpful in situations where request data needs to be manually parsed as
Litestar will not know how to create the OpenAPI operation data by default.

.. literalinclude:: /examples/openapi/customize_operation_class.py
    :caption: Customize Components Example
    :language: python


The above example will result in an OpenAPI schema object that looks like this:

.. code-block:: json

    {
        "info": { "title": "Litestar API", "version": "1.0.0" },
        "openapi": "3.0.3",
        "servers": [{ "url": "/" }],
        "paths": {
            "/": {
                "post": {
                    "tags": ["ok"],
                    "summary": "Route",
                    "description": "Requires OK, Returns OK",
                    "operationId": "Route",
                    "requestBody": {
                        "content": {
                            "text": {
                                "schema": { "type": "string", "title": "Body", "example": "OK" }
                            }
                        },
                        "description": "OK is the only accepted value",
                        "required": false
                    },
                    "responses": {
                        "201": {
                            "description": "Document created, URL follows",
                            "headers": {}
                        }
                    },
                    "deprecated": false,
                    "x-codeSamples": [
                        {
                            "lang": "Python",
                            "source": "import requests; requests.get('localhost/example')",
                            "label": "Python"
                        },
                        {
                            "lang": "cURL",
                            "source": "curl -XGET localhost/example",
                            "label": "curl"
                        }
                    ]
                }
            }
        },
        "components": { "schemas": {} }
    }

.. attention::

   OpenAPI Vendor Extension fields need to start with `x-` and should not be processed with the default field name
   converter. To work around this, Litestar will honor an `alias` field provided to the
   `dataclass.field <https://docs.python.org/3/library/dataclasses.html#dataclasses.field>`_ metadata
   when generating the field name in the schema.


Generating examples
-------------------

Litestar can automatically generate examples for the ``example`` section of a schema.
To enable this feature, you'll need to have the
`polyfactory <https://polyfactory.litestar.dev/>`_ library installed, which is included
as a package extra under ``litestar[polyfactory`` and ``litestar[full]``.

Once installed, you can turn on example generation via the OpenAPI config:

.. literalinclude:: /examples/openapi/customize_pydantic_model_name.py
    :language: python


Lenient decoding of request data
--------------------------------

The schema generated for a type describes its canonical JSON representation. When Litestar decodes request data, it
also accepts other representations of some scalar types and converts them to the annotated type. Such a value does
not validate against the generated schema, but the request is accepted. The most common cases are listed below; the
list is not exhaustive:

.. list-table::
   :header-rows: 1

   * - Annotated type
     - Documented as
     - Also accepted
   * - :class:`int` and enums with integer values
     - ``integer``
     - A string of digits, such as ``"1"``
   * - :class:`float`
     - ``number``
     - A numeric string, such as ``"1.5"``
   * - :class:`bool`
     - ``boolean``
     - The numbers ``1`` and ``0``, and strings such as ``"true"`` or ``"1"``
   * - :class:`datetime.datetime`
     - ``string`` with the ``date-time`` format
     - A number, read as a Unix timestamp in seconds
   * - :class:`datetime.timedelta`
     - ``string`` with the ``duration`` format
     - A number, read as a number of seconds
   * - :class:`uuid.UUID`
     - ``string`` with the ``uuid`` format
     - The 32 hexadecimal digits without dashes

Pydantic models additionally accept a number for :class:`datetime.time`, read as seconds since midnight.

This is intended behaviour, and the schema is deliberately not widened to describe these inputs: doing so would turn
every scalar into a union in generated clients. A client that sends what the schema documents is unaffected.
