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
    values for this key are string keyed dictionaries with the values being a list of objects.

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


Model schemas
-------------

Litestar asks the library that validates a model to generate the model's schema, so the
document describes the data the server accepts and returns:

pydantic
    Subclasses of ``pydantic.BaseModel``, including ``RootModel``, and the dataclasses and
    ``TypedDict``\ s nested in them. Documenting a pydantic model requires pydantic 2.11 or
    later; with an older version, generating the document raises an
    :class:`~litestar.exceptions.ImproperlyConfiguredException` that names the requirement.

msgspec
    Dataclasses, including pydantic dataclasses since Litestar decodes them with msgspec,
    ``msgspec.Struct`` subclasses, ``TypedDict``\ s and attrs classes.

Enums, and types the library does not describe itself, such as
:class:`~litestar.datastructures.UploadFile` or arbitrary classes, are documented by
Litestar wherever they appear. An enum therefore has one component, shared by parameters
and by the models of both libraries.

Litestar generates the schema itself for:

- DTO transfer models, i.e. handlers with a ``dto`` or ``return_dto``. A pydantic model used
  as a field type of a transfer model, rather than as a nested transfer model, is still
  documented by pydantic.
- Models handled by a schema plugin you register, including a subclass of the built-in
  dataclass, ``Struct``, ``TypedDict`` or attrs schema plugin that overrides
  ``to_openapi_schema``.
- Models msgspec cannot decode, e.g. a dataclass with a field that is a union of two
  dataclasses.

What ``to_openapi_schema`` of a built-in schema plugin returns,
:class:`~litestar.plugins.pydantic.PydanticSchemaPlugin`,
:class:`~litestar.plugins.attrs.AttrsSchemaPlugin` and the dataclass, ``Struct`` and
``TypedDict`` plugins, is unspecified: it may be a placeholder reference that points at the
component once the document is built. A subclass calling ``super().to_openapi_schema()``, or a
schema plugin calling one of these plugins, may return that value unchanged or wrap it, e.g.
in a ``oneOf``, but must not read or change it; return your own schema instead.
``schema_creator.schema_registry.from_reference()`` raises
:class:`~litestar.exceptions.ImproperlyConfiguredException` for the placeholder, and
``schema_creator.schema_registry.component_for()`` returns ``None``.

A :class:`~litestar.params.KwargDefinition` on a field of a model a library documents sets
the field's ``title``, ``description`` and ``examples``. Its constraints, such as ``ge`` or
``max_length``, are not documented, since the server does not enforce them on these fields.
On a pydantic model, only the ``KwargDefinition`` of the field itself is read, not one nested
in the field type, such as ``list[Annotated[int, KwargDefinition(...)]]``, and values set with
``pydantic.Field`` take precedence.

To document deeply nested models, Litestar raises the interpreter's recursion limit to at least
10000 while a library generates schemas, and restores it afterwards. The limit is process-wide,
so it also applies to other threads during that time, usually the first request for the schema.


Request and response schemas
++++++++++++++++++++++++++++

A model can be documented differently in a request and in a response: a pydantic
``computed_field`` is only returned, an alias may only apply when validating, a ``Decimal``
is accepted as a number or a string but returned as a string. When the two schemas differ,
the model gets two components: ``<Name>-Input``, used by request bodies and parameters, and
``<Name>-Output``, used by responses. A model with the same schema in both directions, or
used in one direction only, has a single ``<Name>`` component. A model that contains a split
model is split as well, including a msgspec model that contains a pydantic model.

pydantic's ``json_schema_mode_override`` setting is ignored: requests are always documented as
validated and responses as serialized, which is what the server does.


Customizing pydantic model schemas
++++++++++++++++++++++++++++++++++

Use the options described in the
`pydantic JSON schema docs <https://docs.pydantic.dev/latest/concepts/json_schema/>`_: the
model docstring becomes the description, ``Field`` sets descriptions, constraints and
examples, ``json_schema_extra`` (a dict or a callable) adds keys to a model or field schema,
and ``WithJsonSchema`` replaces the schema of a type.

.. literalinclude:: /examples/openapi/customize_pydantic_model_schema.py
    :caption: Customizing a pydantic model schema
    :language: python

``Product`` is used in both directions and ``label`` only exists in responses, so the
document has a ``Product-Input`` and a ``Product-Output`` component. ``Product-Output`` looks
like this, and ``Product-Input`` is the same without ``label``:

.. code-block:: json

   {
       "properties": {
           "name": {
               "type": "string",
               "maxLength": 50,
               "title": "Name",
               "description": "Display name"
           },
           "sku": {
               "type": "string",
               "pattern": "^[A-Z]{3}-[0-9]{4}$",
               "title": "Sku"
           },
           "price": {
               "type": "integer",
               "exclusiveMinimum": 0,
               "title": "Price",
               "description": "Price in cents"
           },
           "label": {"type": "string", "title": "Label", "readOnly": true}
       },
       "type": "object",
       "required": ["name", "sku", "price", "label"],
       "title": "Product",
       "description": "A product in the catalogue.",
       "examples": [{"name": "Chair", "price": 4900, "sku": "CHR-0001"}]
   }

To document a model with a schema pydantic does not generate, register a schema plugin for
it, or subclass :class:`~litestar.plugins.pydantic.PydanticSchemaPlugin` and override
``to_openapi_schema``: return your own schema, or the value of
``super().to_openapi_schema()`` unchanged to keep pydantic's component. A schema the subclass returns
for a model is also used where the model is nested in a pydantic model.

pydantic's schema also differs from the schema Litestar generates for other types in these
ways:

- Properties carry pydantic's titles, e.g. ``"title": "Name"``.
- ``model_config["example"]`` is not read; use ``json_schema_extra={"examples": [...]}``.
- Request schemas list the keys validation accepts: the alias, the alias or the field name
  with ``validate_by_name`` (or ``populate_by_name``), or only the field name with
  ``validate_by_alias=False``. This also applies to the dataclasses and ``TypedDict``\ s
  nested in a model. Response schemas use aliases if the ``prefer_alias`` option of
  :class:`~litestar.plugins.pydantic.PydanticPlugin` or
  :class:`~litestar.plugins.pydantic.PydanticInitPlugin` is set.
- ``bytes`` is a string, with ``format: base64url`` if the model's ``val_json_bytes`` or
  ``ser_json_bytes`` setting is ``base64``.
- pydantic types have pydantic's schema inside and outside a model:

  - ``AnyUrl`` has ``format: uri`` and ``minLength: 1``, and ``HttpUrl`` also
    ``maxLength: 2083``.
  - ``IPvAnyAddress``, ``IPvAnyInterface`` and ``IPvAnyNetwork`` are strings with
    ``format: ipvanyaddress``, ``ipvanyinterface`` and ``ipvanynetwork``.
  - ``NameEmail`` has ``format: name-email``.
  - ``SecretStr`` and ``SecretBytes`` are ``writeOnly`` strings with ``format: password``.
  - ``ByteSize`` is a non-negative integer, or in request schemas also a size string such
    as ``"1kb"``.
  - ``Json[T]`` inside a model is a string with ``contentMediaType: application/json`` in
    requests and ``T`` in responses; outside a model it is documented as ``T``, the type the
    server decodes.
- A dataclass used inside a pydantic model and directly by a handler has two components,
  one generated by pydantic and one by msgspec, e.g. ``Address`` and ``Address_2``.
- A field type pydantic cannot describe, e.g. a custom type with a plain
  ``__get_pydantic_core_schema__``, is documented by the schema plugin you register for it.
  Without one, it is documented as any value, with one
  :class:`~litestar.exceptions.LitestarWarning` naming the model and field.

.. note::

   Outside a model, the server rejects pydantic types other than ``Json`` as request
   parameters or bodies, so use them inside a model.

.. note::

   - A field that contains both a type pydantic cannot describe and a subclass of it with the
     same pydantic core schema, e.g. ``tuple[Money, SubMoney]``, documents both as any value,
     with a :class:`~litestar.exceptions.LitestarWarning`, since the two cannot be told apart.
   - A generic class pydantic hands back to Litestar, such as a generic ``Struct``, gets one
     component per parametrisation, e.g. ``Page_int_``. A field that contains several
     parametrisations of the same class, e.g. ``Union[Page[int], Page[str]]``, or
     ``tuple[PageOf[Item], Page[int]]`` where ``PageOf`` is a generic alias of ``Page``,
     references a component of the bare class ``Page`` instead.
   - ``PastDate`` and similar types have no description.


Customizing msgspec model schemas
+++++++++++++++++++++++++++++++++

Use the options described in the
`msgspec JSON schema docs <https://jcristharif.com/msgspec/jsonschema.html>`_: the class
docstring becomes the description, ``msgspec.Meta`` sets constraints, ``title``,
``description`` and ``examples``, and ``Meta(extra_json_schema=...)`` adds keys to the
schema.

.. literalinclude:: /examples/openapi/customize_msgspec_model_schema.py
    :caption: Customizing a msgspec model schema
    :language: python

``Stock`` is only returned, so the document has a single ``Stock`` component:

.. code-block:: json

   {
       "properties": {
           "sku": {
               "type": "string",
               "pattern": "^[A-Z]{3}-[0-9]{4}$",
               "examples": ["CHR-0001"]
           },
           "quantity": {
               "type": "integer",
               "minimum": 0,
               "description": "Units in the warehouse"
           },
           "warehouse": {
               "anyOf": [{"type": "string"}, {"type": "null"}],
               "deprecated": true
           }
       },
       "type": "object",
       "required": ["sku", "quantity"],
       "title": "Stock",
       "description": "Stock level of a product."
   }

Litestar changes msgspec's schema for these types:

- ``Decimal`` is a number or a string with ``format: decimal`` in requests, and a string with
  ``format: decimal`` in responses.
- ``datetime`` and ``time`` have ``format: date-time`` and ``format: time``.
- Field defaults are encoded with the application's ``type_encoders``; a default that needs
  a router- or handler-level encoder is left out, and so is a default set with
  ``pydantic.Field`` on a pydantic dataclass field.

For both libraries, ``set`` and ``frozenset`` are arrays without ``uniqueItems``, since the
server removes duplicates instead of rejecting them. A schema plugin you register is used for
the types the library hands back to Litestar, not for the types it describes itself, such as
a ``datetime`` or ``UUID`` field.


Naming components
+++++++++++++++++

A component is named after its class. Each library makes the names of its own models
unique: two models named ``Item`` in the modules ``app.a`` and ``app.b`` become
``app.a.Item`` and ``app.b.Item``. Classes with the same module and qualified name, such as
classes built by a factory function, cannot be told apart by name, so the second one gets a
``_2`` suffix; so does a name already used by another component, for example by a model of
the other library.

Set ``__schema_name__`` on a class to choose the name of its component wherever the class
appears. It also sets the component's title, unless a pydantic model sets
``model_config["title"]``. Litestar reads it from the class itself, so subclasses do not
inherit it. A split model keeps the suffixes, e.g. ``IdContainer-Input``.

.. literalinclude:: /examples/openapi/customize_pydantic_model_name.py
    :caption: Customize Components Example
    :language: python

The above results in this component:

.. code-block:: json

   {
       "IdContainer": {
           "properties": {
               "id": {"type": "string", "format": "uuid", "title": "Id"}
           },
           "type": "object",
           "required": ["id"],
           "title": "IdContainer"
       }
   }

:attr:`~.params.KwargDefinition.schema_component_key` on a request body or parameter gives
that use site its own copy of the component, under the given key. The key gets the
``-Input`` and ``-Output`` suffixes only when it is used in both directions on a split model:

.. code-block:: python

   from typing import Annotated

   from litestar import post
   from litestar.params import Body


   @post("/ids")
   async def create_id(data: Annotated[IdModel, Body(schema_component_key="NewId")]) -> None: ...

Two classes or use sites with the same explicit name, from ``__schema_name__`` or
``schema_component_key``, or an explicit name that is also the name of another Litestar
component such as an enum, raise :class:`~litestar.exceptions.ImproperlyConfiguredException`.
A model whose automatic name is taken gets the suffix instead.


Unsupported keys
++++++++++++++++

In a schema a library generates, keys added through pydantic's ``json_schema_extra`` on a
model or a field, or msgspec's ``Meta(extra_json_schema=...)`` on a field, are kept only if
they are JSON schema keywords Litestar can convert. Other keys, such as specification
extensions (``x-*``), ``$comment``, ``nullable``, ``externalDocs`` or ``xml``, are left out
of the document, with one :class:`~litestar.exceptions.LitestarWarning` per model and key.
In a schema Litestar generates itself, such as that of a DTO transfer model or a model
msgspec cannot decode, such a key in a field's ``json_schema_extra`` raises a
``ValueError``, while a model-level ``json_schema_extra`` and msgspec's
``extra_json_schema`` are ignored.



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

.. literalinclude:: /examples/openapi/generating_examples.py
    :language: python

For a pydantic or msgspec model, the generated examples are added where the model is used,
next to a reference to its component, not to the component itself:

.. code-block:: json

   {"allOf": [{"$ref": "#/components/schemas/Pet"}], "examples": [{"name": "Rex"}]}

The component only carries the examples declared through the model's library. In a request,
a pydantic model's example uses the keys validation accepts and leaves out computed fields;
if the model's validation rejects every dump of the example, the request has no example.
