OpenAPI integration
===================

Starlite has first class OpenAPI support offering the following features:

- Automatic `OpenAPI 3.1.0 Schema <https://spec.openapis.org/oas/v3.1.0>`_ generation, which is available as both YAML
  and JSON.
- Builtin support for static documentation site generation using several different libraries.
- Simple configuration using pydantic based classes.

Pydantic-OpenAPI-schema
-----------------------

Starlite generates the `latest version of the OpenAPI specification <https://spec.openapis.org/oas/latest.html>`_ using
the `pydantic-openapi-schema <https://github.com/starlite-api/pydantic-openapi-schema>`_ library, which is bundled as part
of Starlite and is also maintained by the `starlite-api <https://github.com/starlite-api>`_ GitHub organization.

This library offers a full implementation of the OpenAPI specification as pydantic models, and is as such a powerful and
type correct foundation for schema generation using python.

.. seealso::

   The `pydantic-openapi-schema docs <https://starlite-api.github.io/pydantic-openapi-schema>`_ for a
   full reference regarding the library's API.



OpenAPI schema generation config
--------------------------------

OpenAPI schema generation is enabled by default. To configure it you can pass an instance of
:class:`OpenAPIConfig <starlite.config.OpenAPIConfig>` to the :class:`Starlite constructor <starlite.app.Starlite>`
using the ``openapi_config`` kwarg:

.. code-block:: python

   from starlite import Starlite, OpenAPIConfig

   app = Starlite(
       route_handlers=[...], openapi_config=OpenAPIConfig(title="My API", version="1.0.0")
   )



Disabling schema generation
+++++++++++++++++++++++++++

If you wish to disable schema generation and not include the schema endpoints in your API, simply pass ``None`` as the
value for ``openapi_config``:

.. code-block:: python

   from starlite import Starlite

   app = Starlite(route_handlers=[...], openapi_config=None)



Route handler OpenAPI configuration
------------------------------------

By default, an `operation <https://spec.openapis.org/oas/latest.html#operation-object>`_ schema is generated for all route
handlers. You can omit a route handler from the schema by setting ``include_in_schema=False``:

.. code-block:: python

   from starlite import get


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

``operation_id``
    An identifier used for the route's schema *operationId*. Defaults to the ``__name__`` attribute of the
    wrapped function.

``deprecated``
    A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema. Defaults
    to ``False``.

``raises``
    A list of exception classes extending from ``starlite.HttpException``. This list should describe all
    exceptions raised within the route handler's function/method. The Starlite ``ValidationException`` will be added
    automatically for the schema if any validation is involved (e.g. there are parameters specified in the
    method/function).

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

   from starlite import ResponseSpec, get


   class Item(BaseModel): ...


   class ItemNotFound(BaseModel):
       was_removed: bool
       removed_at: Optional[datetime]


   @get(
       path="/items/{pk:int}",
       responses={
           404: ResponseSpec(
               model=ItemNotFound, description="Item was removed or not found"
           )
       },
   )
   def retrieve_item(pk: int) -> Item: ...

You can also specify ``security`` and ``tags`` on higher level of the application, e.g. on a controller, router or the
app instance itself. For example:

.. code-block:: python

   from starlite import Starlite, OpenAPIConfig, get
   from pydantic_openapi_schema.v3_1_0 import Components, SecurityScheme, Tag


   @get(
       "/public",
       tags=["public"],
       security=[{}],  # this endpoint is marked as having optional security
   )
   def public_path_handler() -> dict[str, str]:
       return {"hello": "world"}


   @get("/other", tags=["internal"], security=[{"apiKey": []}])
   def internal_path_handler() -> None: ...


   app = Starlite(
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
               securitySchemes={
                   "BearerToken": SecurityScheme(
                       type="http",
                       scheme="bearer",
                   )
               },
           ),
       ),
   )



The OpenAPIController
---------------------

Starlite includes an :class:`OpenAPIController <starlite.openapi.controller.OpenAPIController>` class that is used as the
default controller in the :class:`OpenAPIConfig <.config.OpenAPIConfig>`.

This controller exposes the following endpoints:

``/schema/openapi.yaml``
    allowing for download of the OpenAPI schema as YAML.

``/schema/openapi.json``
    allowing for download of the OpenAPI schema as JSON.

``/schema/redoc``
    Serves the docs using `Redoc <https://github.com/Redocly/redoc>`_.

``/schema/swagger``
    Serves the docs using `Swagger-UI <https://swagger.io/docs/open-source-tools/swagger-ui>`_.

``/schema/elements``
    Serves the docs using `Stoplight Elements <https://github.com/stoplightio/elements>`_.

Additionally, the root ``/schema/`` path is accessible, serving the site that is configured as the default in
the :class:`OpenAPIConfig <starlite.config.OpenAPIConfig>`.

Subclassing OpenAPIController
+++++++++++++++++++++++++++++

You can use your own subclass of :class:`OpenAPIController <starlite.openapi.controller.OpenAPIController>` by setting it as
then controller to use in the :class:`OpenAPIConfig <starlite.config.OpenAPIConfig>` ``openapi_controller`` kwarg.

For example, lets say we wanted to change the base path of the OpenAPI related endpoints from ``/schema`` to
``/api-docs``, in this case we'd the following:

.. code-block:: python

   from starlite import Starlite, OpenAPIController, OpenAPIConfig


   class MyOpenAPIController(OpenAPIController):
       path = "/api-docs"


   app = Starlite(
       route_handlers=[...],
       openapi_config=OpenAPIConfig(
           title="My API", version="1.0.0", openapi_controller=MyOpenAPIController
       ),
   )



CDN and offline file support
----------------------------

You can change the default download paths for JS and CSS bundles as well as google fonts by subclassing
:class:`OpenAPIController <starlite.openapi.controller.OpenAPIController>`  and setting any of the following class variables:

.. code-block:: python

   from starlite import Starlite, OpenAPIController, OpenAPIConfig


   class MyOpenAPIController(OpenAPIController):
       path = "/api-docs"
       redoc_google_fonts = False
       redoc_js_url = "https://offline_location/redoc.standalone.js"
       swagger_css_url = "https://offline_location/swagger-ui-css"
       swagger_ui_bundle_js_url = "https://offline_location/swagger-ui-bundle.js"
       swagger_ui_standalone_preset_js_url = (
           "https://offline_location/swagger-ui-standalone-preset.js"
       )
       stoplight_elements_css_url = "https://offline_location/spotlight-styles.mins.css"
       stoplight_elements_js_url = (
           "https://offline_location/spotlight-web-components.min.js"
       )


   app = Starlite(
       route_handlers=[...],
       openapi_config=OpenAPIConfig(
           title="My API", version="1.0.0", openapi_controller=MyOpenAPIController
       ),
   )



Accessing the OpenAPI schema in code
------------------------------------

The OpenAPI schema is generated during the :class:`Starlite <starlite.app.Starlite>` app's init method. Once init is finished,
its accessible as ``app.openapi_schema``. As such you can always access it inside route handlers, dependencies etc. by
access the request instance:

.. code-block:: python

   from starlite import Request, get


   @get(path="/")
   def my_route_handler(request: Request) -> dict:
       schema = request.app.openapi_schema
       return schema.dict()



Customizing Pydantic model schemas
----------------------------------

You can customize the OpenAPI schemas generated for pydantic models by following the guidelines in
the `pydantic docs <https://pydantic-docs.helpmanual.io/usage/schema/>`_.

Additionally, you can affect how pydantic models are translated into OpenAPI ``components`` by settings a special dunder
attribute on the model called ``__schema_name__``:

.. literalinclude:: /examples/openapi/customize_pydantic_model_name.py
    :caption: Customize Components Example
    :language: python


The above will result in an OpenAPI schema object that looks like this:

.. code-block:: json

   {
       "openapi": "3.1.0",
       "info": {"title": "Starlite API", "version": "1.0.0"},
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
                                   "media_type_schema": {
                                       "ref": "#/components/schemas/IdContainer"
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
                       "id": {"type": "string", "schema_format": "uuid", "title": "Id"}
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
