For Django and Django REST Framework users
==========================================


General concepts
----------------

Layered configuration
~~~~~~~~~~~~~~~~~~~~~

Litestar uses a layered architecture. The parts used to group routes can also be used
to hierarchically organize an application. Settings and configuration like dependencies,
exception handlers, guards, middleware, response cookies and headers, lifecycle hooks,
OpenAPI configuration and many more can be defined on any layer, and will be merged
upon registration.

The layers in hierarchical order are
1. Application (``Litestar``)
2. ``Router`` / ``Controller`` (these are on the same level and can be arbitrarily nested)
3. Handler (``BaseRouteHandler``)

When the same configuration is set on multiple layers, the value set closest to the
handler takes precedence. Django has no direct equivalent: settings are global, middleware
is global, and DRF's ``permission_classes`` / ``authentication_classes`` / ``throttle_classes``
are configured per view. In Litestar these are configurable at every layer.


Library-agnostic modelling
~~~~~~~~~~~~~~~~~~~~~~~~~~

DRF uses ``Serializer`` and ``ModelSerializer`` for request validation, response
rendering, and database-to-response mapping; Django uses ``Form`` for HTML form workflows.
Litestar is mostly agnostic about the modelling library. Internally it uses
`msgspec <https://jcristharif.com/msgspec/>`_, and ships first-class support for
Pydantic, attrs, dataclasses, and ``TypedDict``\ s through its plugin system
(:class:`~litestar.plugins.SerializationPlugin` and
:class:`~litestar.plugins.OpenAPISchemaPlugin`). The body of a request is bound to a
``data`` parameter; the return annotation drives the response shape. DTOs sit on top
when the wire shape needs to diverge from the model (see
:ref:`onboarding/django:Serializers and DTOs`).


Application configuration
-------------------------

Django reads ``DJANGO_SETTINGS_MODULE`` and loads a ``settings.py`` module; DRF reads
the ``REST_FRAMEWORK`` dict from the same module. Litestar is configured through
keyword arguments on the :class:`~litestar.app.Litestar` constructor. There is no
settings-module convention, but usually the factory pattern is used, allowing to
configure applications dynamically.

.. tab-set::

    .. tab-item:: Django / DRF
        :sync: django

        .. code-block:: python

            # settings.py
            DEBUG = True
            INSTALLED_APPS = ["django.contrib.contenttypes", "rest_framework", "myapp"]
            MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]
            ROOT_URLCONF = "myapp.urls"
            DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "db.sqlite3"}}

            REST_FRAMEWORK = {
                "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
                "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
            }

    .. tab-item:: Litestar
        :sync: litestar

        .. code-block:: python

            from litestar import Litestar

            def create_app(debug: bool = False) -> Litestar:
                return Litestar(
                    route_handlers=[...],
                    middleware=[...],
                    plugins=[...],
                    openapi_config=...,
                    debug=debug,
                )

Plugins replace ``INSTALLED_APPS``: an ORM integration, a metrics integration, or a
custom feature ships as a plugin and is registered on the application through the
``plugins`` keyword. See :ref:`onboarding/django:Concepts without a direct equivalent`
for the broader mapping.


Route handlers
--------------

Django wires URL patterns through ``urls.py`` and references view callables or
class-based views; DRF adds ``APIView``, ``GenericAPIView``, and ``ViewSet`` on top.
Litestar uses an HTTP-method decorator on a function - or a method on a
:class:`~litestar.controller.Controller` - and registers handlers on a
:class:`~litestar.app.Litestar` or :class:`~litestar.router.Router` instance. The URL
pattern lives on the decorator, not in a separate file.

.. tab-set::

    .. tab-item:: Django
        :sync: django

        .. code-block:: python

            # views.py
            from django.http import JsonResponse

            def index(request):
                return JsonResponse({"hello": "world"})

            # urls.py
            from django.urls import path
            from . import views

            urlpatterns = [path("", views.index)]

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            # views.py
            from rest_framework.decorators import api_view
            from rest_framework.response import Response

            @api_view(["GET"])
            def index(request):
                return Response({"hello": "world"})

            # urls.py same as above

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/routing.py
            :language: python

.. tip::
    Router and Controllers can be arbitrarily nested, but disappear at runtime. When you
    register a controller or router on an application, they get reduced to standard,
    independent route handlers.

    For example

    .. code-block:: python

        class UserController(Controller):
            path = "/user"
            guards = [can_read_user]

            @get("{user_id:str}", guards=[can_read_user])
            async def get_user(self, user_id: FromPath[str]) -> User:
                ...

    is functionally equivalent to

    .. code-block:: python

        @get("/user/{user_id:str}", guards=[can_read_user])
        async def get_user(user_id: FromPath[str]) -> User:
            ...



.. seealso::

    * :ref:`Routing - Registering Routes <usage/routing/overview:registering routes>`


Controllers
~~~~~~~~~~~

DRF's ``APIView``, ``GenericAPIView`` and ``ViewSet`` group HTTP methods on a single
class. Litestar's :class:`~litestar.controller.Controller` does the same. Subclass
``Controller``, set ``path``, and decorate methods with the HTTP method decorators.
The difference is that DRF views dispatch by method name, while Litestar uses the same
decorator patterns as for standalone routes:

.. tab-set::

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            from rest_framework.views import APIView
            from rest_framework.response import Response

            class ItemView(APIView):
                def get(self, request, item_id):
                    return Response({"id": item_id})

                def post(self, request):
                    return Response(request.data, status=201)

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/controller.py
            :language: python

A ``Controller`` carries the same layered configuration as a ``Router``: dependencies,
guards, middleware, exception handlers, and OpenAPI tags can all be declared on the
class and inherited by its methods.

.. tip::
    Controllers are just a cosmetic layers on top of a router. Under the hood, a
    controller instance will be converted into a router when it's registered on the
    application


.. seealso::

    * :doc:`/usage/routing/handlers`


Routers
~~~~~~~

Django's ``include("app.urls")`` and DRF's ``SimpleRouter().register(...)`` mount a
sub-tree of URLs under a prefix. Litestar's :class:`~litestar.router.Router` takes a
``path`` and a list of ``route_handlers``, which can themselves be handlers,
controllers, or other routers. Routers nest arbitrarily.

.. tab-set::

    .. tab-item:: Django
        :sync: django

        .. code-block:: python

            # myapp/urls.py
            from django.urls import path
            from . import views

            urlpatterns = [
                path("items/", views.list_items),
                path("items/<int:item_id>/", views.get_item),
            ]

            # project/urls.py
            from django.urls import include, path

            urlpatterns = [path("api/v1/", include("myapp.urls"))]

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            from rest_framework.routers import SimpleRouter

            router = SimpleRouter()
            router.register(r"items", ItemViewSet, basename="item")

            urlpatterns = [path("api/v1/", include(router.urls))]

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/routers.py
            :language: python



Application state
~~~~~~~~~~~~~~~~~

Django stores process-global state in module-level variables or on
``django.apps.apps``. Litestar exposes :class:`~litestar.datastructures.State`,
seeded on the application and available to dependencies through the ``state``
parameter and to handlers through ``request.app.state``. Per-request state lives on
``request.state`` instead and inherits from the application state

.. tab-set::

    .. tab-item:: Django
        :sync: django

        .. code-block:: python

            # myapp/apps.py
            from django.apps import AppConfig

            class MyAppConfig(AppConfig):
                def ready(self):
                    from .clients import init_redis
                    init_redis()

            # services.py
            from .clients import redis_client

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/state.py
            :language: python



Sync and async handlers
~~~~~~~~~~~~~~~~~~~~~~~

Django views and DRF views are synchronous by default; Django 4+ supports
``async def`` views through an in-process sync-to-async bridge. The bridge cuts
both ways: a sync view runs on a thread pool from the ASGI worker, an
``async def`` view runs on the event loop, and ORM / cache / middleware calls
made from an async view are wrapped in ``sync_to_async`` to bounce back to a
thread. DRF itself is still sync-only: serializers, throttles, and the
``APIView`` dispatch loop do not have async equivalents.

Litestar inverts the default. Handlers are ``async def`` and run directly on
the event loop. There is no implicit thread bridge: a blocking call in an
async handler blocks the worker. A ``def`` handler must declare which side it
runs on:

- ``sync_to_thread=True`` offloads the call to a thread pool; Use when
  porting blocking ORM code, file I/O, or a third-party library without async
  support.
- ``sync_to_thread=False`` runs the call inline on the event loop: reserved
  for short, non-blocking work where the offload would cost more than the
  call itself.

A bare ``def`` handler with neither flag emits a deprecation warning at
startup: the choice is load-bearing enough that the framework asks you to be
explicit.

.. tab-set::

    .. tab-item:: Django / DRF
        :sync: django

        .. code-block:: python

            def slow_view(request):
                time.sleep(0.01)  # implicitly runs in the request thread
                return JsonResponse({"hello": "world"})

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/sync_handler.py
            :language: python


Handlers and request data
-------------------------

DRF deserialises the body once on the view level and exposes ``request.data``,
``request.query_params``, ``request.GET``, ``request.POST``, ``request.FILES``, and
``request.COOKIES``; Django's ``HttpRequest`` exposes the lower-level versions of the
same. Litestar injects each piece through typed handler parameters using
:class:`~typing.Annotated` and ``From*`` markers, so the handler signature describes the
contract.


Path and query parameters
~~~~~~~~~~~~~~~~~~~~~~~~~

Django converts path parameters with the path-converter syntax (``<int:item_id>``)
and exposes them as positional arguments; query parameters come from
``request.GET.get(...)``. DRF exposes them through ``self.kwargs`` and
``request.query_params``. Litestar uses path-converter syntax in the decorator and
binds the values through :data:`~litestar.params.FromPath` and
:data:`~litestar.params.FromQuery`.

.. tab-set::

    .. tab-item:: Django
        :sync: django

        .. code-block:: python

            # urls.py
            path("items/<int:item_id>/", views.get_item)

            # views.py
            def get_item(request, item_id):
                limit = int(request.GET.get("limit", "10"))
                return JsonResponse({"id": item_id, "limit": limit})

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            class ItemView(APIView):
                def get(self, request, item_id):
                    limit = int(request.query_params.get("limit", "10"))
                    return Response({"id": item_id, "limit": limit})

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/parameters.py
            :language: python

To attach validation constraints or OpenAPI metadata, use the
:class:`~typing.Annotated` form with :class:`~litestar.params.PathParameter` and
:class:`~litestar.params.QueryParameter`:

.. tab-set::

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            class LimitSerializer(serializers.Serializer):
                limit = serializers.IntegerField(min_value=1, max_value=100)

            class ItemView(APIView):
                def get(self, request, item_id):
                    serializer = LimitSerializer(data=request.query_params)
                    serializer.is_valid(raise_exception=True)
                    ...

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/parameters_constrained.py
            :language: python

.. seealso::

    * :doc:`/usage/routing/parameters`


Header and cookie parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DRF reads headers from ``request.headers`` and cookies from ``request.COOKIES``.
Litestar binds them through :class:`~litestar.params.HeaderParameter` and
:class:`~litestar.params.CookieParameter` (or their generic forms
:data:`~litestar.params.FromHeader` and :data:`~litestar.params.FromCookie`). When
the cookie or header name does not match the Python parameter name, pass ``name=``
explicitly.

.. tab-set::

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            class SecureView(APIView):
                def get(self, request):
                    session_id = request.COOKIES["sessionid"]
                    api_key = request.headers["X-API-Key"]
                    return Response({"session": session_id, "api_key": api_key})

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/header_cookie_params.py
            :language: python


JSON request body
~~~~~~~~~~~~~~~~~

DRF's parser populates ``request.data`` and a ``Serializer`` validates the dict into
a Python object. Litestar injects the validated body through a ``data`` parameter
typed against any supported model (dataclasses , msgspec :class:`msgspec.Struct`,
Pydantic model, attrs class). Validation runs before the handler is called; an invalid
body raises :class:`~litestar.exceptions.ValidationException` which produces a
`400 - Bad Request` response.

.. tab-set::

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            class ItemSerializer(serializers.Serializer):
                name = serializers.CharField()
                price = serializers.FloatField()

            class ItemView(APIView):
                def post(self, request):
                    serializer = ItemSerializer(data=request.data)
                    serializer.is_valid(raise_exception=True)
                    return Response(serializer.validated_data, status=201)

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/post_json.py
            :language: python

Field-level renaming, partial updates, and write-vs-read separation move to the
DTO layer. See :ref:`onboarding/django:Serializers and DTOs`.


Form data
~~~~~~~~~

Django's ``Form`` and DRF's ``MultiPartParser`` / ``FormParser`` populate
``request.POST``. Litestar uses the same ``data`` parameter with the
:data:`~litestar.params.URLEncodedBody` marker for form-encoded bodies, or
:data:`~litestar.params.MultipartBody` for multipart.

.. tab-set::

    .. tab-item:: Django
        :sync: django

        .. code-block:: python

            from django.views.decorators.http import require_POST

            @require_POST
            def login(request):
                username = request.POST["username"]
                password = request.POST["password"]
                return JsonResponse({"user": username})

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/form_data.py
            :language: python


File uploads
~~~~~~~~~~~~

Django exposes uploaded files through ``request.FILES`` (an ``UploadedFile`` per
field). Litestar uses :class:`~litestar.datastructures.UploadFile`, or
``list[UploadFile]`` for multiple files under the same field name, with
a :data:`~litestar.params.MultipartBody` marker:

.. tab-set::

    .. tab-item:: Django
        :sync: django

        .. code-block:: python

            def upload(request):
                files = request.FILES.getlist("data")
                return JsonResponse({"file_names": [f.name for f in files]})

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/uploads.py
            :language: python


Producing responses
-------------------

Django returns ``HttpResponse``, ``JsonResponse``, ``HttpResponseRedirect`` and so
on, with status and headers set explicitly. DRF wraps the body in
``Response(data, status=...)`` and renders through the configured renderer. Litestar
infers the response from the handler's return annotation; a returned dict, dataclass,
or model serialises to JSON, ``str`` returns ``text/plain``, and typed response
classes (:class:`~litestar.response.Response`, :class:`~litestar.response.Stream`,
:class:`~litestar.response.Template`, :class:`~litestar.response.Redirect`,
:class:`~litestar.response.File`) pick their own media type.


Default status codes
~~~~~~~~~~~~~~~~~~~~

Django defaults to ``200`` for every method; DRF defaults to ``200`` unless
``status=`` is passed. Litestar picks the default from the HTTP method: ``POST``
defaults to ``201 Created``, ``DELETE`` to ``204 No Content``, and everything else
to ``200``. Pass ``status_code=`` to the decorator to override.


Cookies and headers
~~~~~~~~~~~~~~~~~~~

Django sets cookies and headers on the response object
(``response.set_cookie(...)``, ``response["X-Foo"] = "bar"``). DRF works the same.
Litestar offers two paths: declare static values on the decorator with
``response_cookies=`` and ``response_headers=``, or return a
:class:`~litestar.response.Response` with ``cookies=`` and ``headers=`` when the
values depend on the request.

.. tip::
    Setting a static response header or cookie will automatically render it in the
    OpenAPI schema

.. tab-set::

    .. tab-item:: Django / DRF
        :sync: django

        .. code-block:: python

            def view(request):
                response = JsonResponse({"set": "dynamic"})
                response.set_cookie("my-cookie", "cookie-value")
                return response

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/cookies.py
            :language: python

.. seealso::

    * :ref:`Responses - Setting Response Cookies <usage/responses:setting response cookies>`


Serialization
~~~~~~~~~~~~~

DRF's ``Response(serializer.data)`` round-trips through the configured renderer
(JSON by default), with a separate HTML "browsable API" renderer for browsers.
Litestar drives serialisation off the handler return annotation. Structured types
serialise to JSON; ``str`` returns ``text/plain``; a typed response class picks its
own media type. ``media_type=`` on the decorator overrides the default.


Templates
~~~~~~~~~

Django's ``render(request, "template.html", context)`` and DRF's
``TemplateHTMLRenderer`` are the common cases. Litestar configures the engine once
on the application through :class:`~litestar.template.config.TemplateConfig` and
each handler returns a :class:`~litestar.response.Template`. The bundled engines are
Jinja, Mako, and MiniJinja; the engine slot accepts any implementation of the
template-engine protocol.

.. tab-set::

    .. tab-item:: Django
        :sync: django

        .. code-block:: python

            # settings.py
            TEMPLATES = [{
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [BASE_DIR / "templates"],
            }]

            # views.py
            from django.shortcuts import render

            def hello(request, name):
                return render(request, "hello.html", {"name": name})

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/templates.py
            :language: python

.. seealso::

    * :doc:`/usage/templating`


Streaming responses
~~~~~~~~~~~~~~~~~~~

Django uses ``StreamingHttpResponse(iterator)``; Litestar uses
:class:`~litestar.response.Stream`. Both wrap a sync or async iterator.

.. tab-set::

    .. tab-item:: Django
        :sync: django

        .. code-block:: python

            from django.http import StreamingHttpResponse

            def stream_numbers(request):
                def numbers():
                    for i in range(5):
                        yield f"{i}\n"
                return StreamingHttpResponse(numbers())

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/streaming.py
            :language: python


URL lookup
~~~~~~~~~~

Django's ``reverse("view-name", kwargs=...)`` and the ``{% url %}`` template tag
build URLs from named patterns; DRF adds ``reverse("api-detail", request=request)``
to include the absolute URL. Litestar exposes
:meth:`~litestar.app.Litestar.route_reverse` on the application and
:meth:`~litestar.connection.ASGIConnection.url_for` on the request. Handlers name
themselves through ``name=`` on the decorator.

.. tab-set::

    .. tab-item:: Django
        :sync: django

        .. code-block:: python

            # urls.py
            path("", views.index, name="index")

            # views.py
            from django.shortcuts import redirect
            from django.urls import reverse

            def go_home(request):
                return redirect(reverse("index"))

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/url_reverse.py
            :language: python


Serializers and DTOs
--------------------

DRF's ``Serializer`` and ``ModelSerializer`` carry three concerns: validating
inbound data, rendering outbound data, and mapping between the wire shape and the
ORM model. Litestar splits these. Model libraries (dataclasses, msgspec, Pydantic,
attrs) handle validation and basic shape, applied through the ``data`` parameter
and the return annotation. **DTOs** decouple the wire shape from the internal model
when the two should differ: an inbound payload that excludes server-managed fields,
a response that renames fields, a partial update that accepts a subset of the
model. Litestar ships :class:`~litestar.dto.dataclass_dto.DataclassDTO`,
:class:`~litestar.dto.msgspec_dto.MsgspecDTO`, ``PydanticDTO``, and
``SQLAlchemyDTO`` (for ORM models).

The basic case: excluding a server-set field from inbound payloads:

.. tab-set::

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            class UserSerializer(serializers.ModelSerializer):
                class Meta:
                    model = User
                    fields = ["id", "name", "email"]
                    read_only_fields = ["id"]

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/dto_basic.py
            :language: python

The :class:`~litestar.dto.data_structures.DTOData` wrapper holds the
parsed-and-validated input; ``create_instance(**overrides)`` materialises it into the
model with server-managed fields filled in.

For ORM-backed models, ``SQLAlchemyDTO`` understands the mapped class and lets the
same configuration drive both the inbound and outbound shape. The DTO is attached
to the handler through ``dto=`` (for the request body) and ``return_dto=`` (for the
response):

.. tab-set::

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            class ItemSerializer(serializers.ModelSerializer):
                class Meta:
                    model = Item
                    fields = ["id", "name", "price"]
                    read_only_fields = ["id"]

            class ItemView(generics.CreateAPIView):
                serializer_class = ItemSerializer

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/dto_sqlalchemy.py
            :language: python

DRF's ``partial=True`` on the serializer is mirrored by
``DTOConfig(partial=True)`` on a write DTO: optional fields become permitted,
required fields become optional.

The same shape used for input is rarely the right shape for output; the DTO lets
one model definition produce both, with the differences declared as configuration
rather than written twice.

.. admonition:: info

    DTOs also serve as the adapter for types Litestar would not otherwise know how
    to serialise, and do not offer serialization methods by themselves;
    A SQLAlchemy ``DeclarativeBase`` subclass is not a dataclass and has no msgspec or
    Pydantic schema, but ``SQLAlchemyDTO`` reads the mapped columns and produces a wire
    schema from them, by representing the model as an abstract shape Litestar *can*
    understand. The same pattern extends to other libraries: any DTO subclass that
    understands a model type can adopt it. This is how Litestar stays
    modelling-library-agnostic while still letting you return an ORM instance directly
    from a handler.

.. seealso::

    * :doc:`/usage/dto/index`


Dependency injection
--------------------

DRF threads request-scoped state through ``self.request``, ``self.kwargs``, and
``self.get_serializer_context()``; everything else (database clients, service
classes, configuration) is typically reached through module-level imports.
Litestar has a first-class dependency-injection container. Dependencies are
declared as a mapping from parameter name to provider, attached to the
``dependencies`` keyword on any layer. Async callables work directly as providers;
synchronous callables are wrapped in :class:`~litestar.di.Provide`.

Inner layers override outer ones, so a router-scoped dependency replaces an
application-scoped one of the same name, and a handler-scoped one replaces both.

.. tab-set::

    .. tab-item:: Django / DRF
        :sync: django

        .. code-block:: python

            # services.py
            payments = PaymentService()

            # views.py
            from .services import payments

            class ChargeView(APIView):
                def get(self, request):
                    user_id = request.user.id
                    return Response({"user_id": user_id, "result": payments.charge(100)})

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/dependency_injection.py
            :language: python

.. tip::
    Dependencies are part of Litestar's layered architecture, so these can be declared
    on applications, routers, controllers or route handlers.

.. seealso::

    * :doc:`/usage/dependency-injection`


Exceptions and error responses
------------------------------

Django raises ``Http404``, ``PermissionDenied``, and ``SuspiciousOperation``; DRF
adds ``APIException``, ``NotFound``, ``ValidationError``, ``PermissionDenied``, and
the ``EXCEPTION_HANDLER`` setting that maps them to JSON responses. Litestar exports
:class:`~litestar.exceptions.HTTPException` and concrete subclasses
(:class:`~litestar.exceptions.NotFoundException`,
:class:`~litestar.exceptions.PermissionDeniedException`,
:class:`~litestar.exceptions.ValidationException`,
:class:`~litestar.exceptions.NotAuthorizedException`). The status code is a keyword
argument (``status_code=``), and a positional argument to ``HTTPException`` is
appended to ``detail``.

.. tab-set::

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            from rest_framework.exceptions import NotFound

            class ItemView(APIView):
                def get(self, request, item_id):
                    if item_id != 1:
                        raise NotFound(detail=f"item {item_id} does not exist")
                    return Response({"id": item_id})

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/exceptions.py
            :language: python


Custom exception handlers
~~~~~~~~~~~~~~~~~~~~~~~~~

DRF replaces the global exception handler through the ``EXCEPTION_HANDLER`` setting
that points to a single callable. Django's ``handler404`` and ``handler500``
project-level variables point to views for two status codes. Litestar accepts a
mapping from exception class or status code to a handler callable through
``exception_handlers={...}`` on any layer.

.. tip::
    Exception handling is part of Litestar's layered architecture, so these can be
    declared on applications, routers, controllers or route handlers.

.. tab-set::

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            # settings.py
            REST_FRAMEWORK = {"EXCEPTION_HANDLER": "myapp.exceptions.handler"}

            # exceptions.py
            from rest_framework.views import exception_handler

            def handler(exc, context):
                if isinstance(exc, ItemNotFoundError):
                    return Response({"detail": "item not found"}, status=404)
                return exception_handler(exc, context)

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/custom_exception_handler.py
            :language: python

.. seealso::

    * :ref:`usage/exceptions:exception handling`


Authentication and authorization
--------------------------------

DRF separates *authentication* (who is the caller) from *permissions* (is the caller
allowed to perform this action). Litestar separates them the same way: authentication
middleware sets ``connection.user`` and ``connection.auth``; **guards** decide whether
a request reaches the handler.


Authentication
~~~~~~~~~~~~~~

DRF's authentication classes (``SessionAuthentication``, ``TokenAuthentication``,
``JWTAuthentication``) inspect each request and populate ``request.user``. Litestar
uses authentication middleware. Subclass
:class:`~litestar.middleware.authentication.AbstractAuthenticationMiddleware` for
custom schemes, or use the bundled ``JWTAuth`` /
:class:`~litestar.security.session_auth.SessionAuth` configs that ship a middleware
and OpenAPI security scheme together.

.. tab-set::

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            class BearerAuthentication(BaseAuthentication):
                def authenticate(self, request):
                    header = request.headers.get("Authorization", "")
                    if header != "Bearer secret":
                        raise AuthenticationFailed()
                    return (AnonymousUser(), header)

            class IndexView(APIView):
                authentication_classes = [BearerAuthentication]

                def get(self, request):
                    return Response({"hello": "world"})

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/authentication.py
            :language: python

For session-cookie auth or JWT, register the corresponding config through
``on_app_init``; see :doc:`/usage/security/index`.

.. seealso::

    * :doc:`/usage/security/index`
    * :doc:`/usage/security/jwt`


Guards
~~~~~~

DRF's ``permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]`` runs a list of
permission callables that return ``True`` / ``False`` per request. Litestar's
*guards* are callables that receive the :class:`~litestar.connection.ASGIConnection`
and the :class:`~litestar.handlers.BaseRouteHandler`; raising an exception aborts
the request.

.. admonition:: Info

    A guard is a callable that receives the :class:`~litestar.connection.ASGIConnection`
    and the :class:`~litestar.handlers.BaseRouteHandler`; raising an exception here
    aborts the request.

.. tip::
    Guards are part of Litestar's layered architecture, so these can be declared on
    applications, routers, controllers or route handlers.

.. tab-set::

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            class IsAdmin(BasePermission):
                def has_permission(self, request, view):
                    return request.headers.get("X-Role") == "admin"

            class AdminViewSet(viewsets.ViewSet):
                permission_classes = [IsAdmin]
                ...

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/guards.py
            :language: python


CSRF
~~~~

Django's ``CsrfViewMiddleware`` reads the ``csrftoken`` cookie and validates the
``X-CSRFToken`` header on unsafe methods. DRF inherits this behavior for
session-authenticated views. Litestar provides
:class:`~litestar.config.csrf.CSRFConfig` passed through ``csrf_config=`` on the
application; the default cookie and header names match Django's convention.

.. tab-set::

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/csrf.py
            :language: python


Middleware
----------

Django's ``MIDDLEWARE`` setting lists dotted-path classes implementing
``__init__(get_response)`` and ``__call__(request)``. Litestar middleware is
ASGI-based: subclass :class:`~litestar.middleware.ASGIMiddleware` and implement
:meth:`~litestar.middleware.ASGIMiddleware.handle`, which receives ``scope``,
``receive``, ``send``, and a ``next_app`` callable. ``next_app`` is the rest of the
ASGI stack. Calling it dispatches to the next middleware or the route handler.

Pure ASGI middleware (a callable wrapping an ASGI app and returning a wrapped ASGI
app) works in any ASGI framework, so existing ASGI middleware ports over without
change.

.. tab-set::

    .. tab-item:: Django
        :sync: django

        .. code-block:: python

            # middleware.py
            import time

            class ProcessTimeMiddleware:
                def __init__(self, get_response):
                    self.get_response = get_response

                def __call__(self, request):
                    start = time.monotonic()
                    response = self.get_response(request)
                    response["X-Process-Time"] = f"{time.monotonic() - start:.4f}"
                    return response

            # settings.py
            MIDDLEWARE = [..., "myapp.middleware.ProcessTimeMiddleware"]

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/middleware.py
            :language: python

Django middleware applies to every request that enters the WSGI / ASGI stack;
opting routes out means restructuring the middleware itself or splitting URL
patterns. Litestar middleware can be excluded per route, in two ways:

- By setting ``scopes`` on the middleware, it can restricted to ``http`` or ``websocket`` requests
- By setting ``exclude_path_pattern`` on the middleware, it can be excluded from any handler matching
- ``exclude_opt_key`` names a key in the handler's ``opt`` dict; handlers that
  set that key to a truthy value skip the middleware

.. code-block:: python

    class AuthMiddleware(ASGIMiddleware):
        exclude = ["/health", "^/internal/"]
        exclude_opt_key = "no_auth"

    @get("/login", no_auth=True)
    async def login() -> dict[str, str]:
        ...

.. seealso::

    * :doc:`/usage/middleware/creating-middleware`


Signals and lifecycle hooks
---------------------------

Django signals (``pre_save``, ``post_save``, ``request_started``,
``request_finished``, and custom ``Signal`` instances) are an in-process
publish/subscribe bus that mixes request lifecycle with domain events.
Litestar exposes the request-lifecycle slice as **per-request hooks**:
``before_request``, ``after_request``, ``after_response``, and
``after_exception``, declared on any layer. They run on the request task and
can read or mutate the request and response.

The request-finished case maps to ``after_response``:

.. tab-set::

    .. tab-item:: Django
        :sync: django

        .. code-block:: python

            from django.core.signals import request_finished
            from django.dispatch import receiver

            @receiver(request_finished)
            def log_request(sender, **kwargs):
                ...

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/lifecycle_hooks.py
            :language: python

Domain events (``post_save``, custom ``Signal`` instances) have no
first-party Litestar equivalent. For in-process fan-out, call the service
function directly from the handler (or from a dependency it injects). For
cross-process fan-out, publish to a message broker (Redis pub/sub, NATS,
RabbitMQ) through a client wired up on the application.


Background tasks
----------------

Django 6 ships ``django.tasks``, a first-party task-queue interface with a
pluggable backend (in-memory, immediate, database, and third-party Celery /
RQ adapters). Tasks are declared with the ``@task`` decorator and submitted
through ``.enqueue(...)``. On earlier versions there was no first-party
option; Celery, RQ, django-q, and Huey covered the same ground.

Litestar's :class:`~litestar.background_tasks.BackgroundTask` (or
:class:`~litestar.background_tasks.BackgroundTasks` collection) runs a
callable after the response body has been sent, attached to a
:class:`~litestar.response.Response` through ``background=``. The two address
different needs: ``django.tasks`` is a durable queue, ``BackgroundTask`` is
in-process work that should not block the response.

.. tab-set::

    .. tab-item:: Django
        :sync: django

        .. code-block:: python

            # tasks.py
            from django.tasks import task

            @task()
            def send_welcome_email(email: str) -> None:
                ...

            # views.py
            from .tasks import send_welcome_email

            def signup(request):
                email = request.POST["email"]
                send_welcome_email.enqueue(email)
                return JsonResponse({"status": "queued"}, status=201)

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/background_tasks.py
            :language: python

A ``BackgroundTask`` is not a job queue: it has no durability, no scheduling,
no retries, and no cross-process fan-out. If the worker process dies before
the task finishes, the task is lost. For durable jobs reach for an external
queue.

.. seealso::

    * :ref:`usage/responses:background tasks`


Database access
---------------

Litestar is ORM-agnostic. There is no built-in ORM and no required
integration: SQLAlchemy, Tortoise, Piccolo, Peewee, an async driver, or raw
SQL all work without framework cooperation. A handler that opens a connection,
runs a query, and returns a dict is a complete Litestar handler.

The fullest first-party integration is the optional
:class:`~advanced_alchemy.extensions.litestar.SQLAlchemyPlugin`, built on
`advanced-alchemy <https://docs.advanced-alchemy.litestar.dev>`_. The plugin
manages the engine and session lifecycle, injects an ``AsyncSession`` per
request through the ``db_session`` dependency, ships a repository, and,
through :class:`~advanced_alchemy.extensions.litestar.SQLAlchemyDTO`, serialises
mapped models to JSON natively. Returning an ORM instance directly from a
handler works because the DTO reads the mapped columns and emits the schema
that Litestar uses for OpenAPI and the response body. No ``ModelSerializer``
equivalent is needed.

Other ORMs follow the same shape minus the plugin: register a startup hook
that opens the engine, provide a session-yielding dependency, and either
return data the model library already serialises (dataclasses, msgspec,
Pydantic) or write a thin DTO for the model type.

.. tab-set::

    .. tab-item:: Django + DRF
        :sync: django

        .. code-block:: python

            # models.py
            from django.db import models

            class Item(models.Model):
                name = models.CharField(max_length=100)

            # serializers.py
            class ItemSerializer(serializers.ModelSerializer):
                class Meta:
                    model = Item
                    fields = ["id", "name"]

            # views.py
            class ItemViewSet(viewsets.ModelViewSet):
                queryset = Item.objects.all()
                serializer_class = ItemSerializer

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/database_sqlalchemy.py
            :language: python

Schema migrations move to Alembic (a SQLAlchemy project) rather than ``manage.py
makemigrations`` / ``migrate``. The plugin can run Alembic from the Litestar CLI.


.. seealso::

    * :doc:`/usage/databases/sqlalchemy/index`


Sessions
--------

Django's ``django.contrib.sessions`` writes a session cookie and stores data in a
configurable backend (database, cache, file, or signed cookie). Litestar's
:class:`~litestar.middleware.session.server_side.ServerSideSessionConfig` writes
the session through a pluggable :class:`~litestar.stores.base.Store` (memory, file,
redis, valkey); :class:`~litestar.middleware.session.client_side.CookieBackendConfig`
keeps the data in a signed cookie. The middleware exposes
``request.session`` as a dict.

.. tab-set::

    .. tab-item:: Django
        :sync: django

        .. code-block:: python

            def login(request):
                request.session["user"] = "alice"

            def whoami(request):
                return JsonResponse({"user": request.session.get("user")})

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/sessions.py
            :language: python


Static files
------------

Django needs ``django.contrib.staticfiles`` in ``INSTALLED_APPS``, a
``STATICFILES_DIRS`` setting, and a ``collectstatic`` step before deployment.
Litestar registers a static-file router through
:func:`~litestar.static_files.create_static_files_router`. The same configuration
serves files in development and production; there is no separate collection step.

.. tab-set::

    .. tab-item:: Django
        :sync: django

        .. code-block:: python

            # settings.py
            STATIC_URL = "/static/"
            STATICFILES_DIRS = [BASE_DIR / "assets"]

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/static_files.py
            :language: python


WebSockets and channels
-----------------------

Django has no first-party WebSocket support; Django Channels adds an ASGI worker, a
routing system, consumer classes, and a ``channel_layer`` for pub/sub. Litestar
offers WebSockets as a built-in primitive. There are three handler styles:

- :func:`~litestar.handlers.websocket`: raw
  `ASGI WebSocket <https://asgi.readthedocs.io/en/latest/specs/www.html#websocket>`_
  handling; same semantics as a Channels ``AsyncWebsocketConsumer``.
- :func:`~litestar.handlers.websocket_listener`: per-message callback that takes and
  returns typed values; the framework handles accept, the receive loop, and
  serialisation.
- :func:`~litestar.handlers.websocket_stream`: async generator that pushes messages
  to the WebSocket; the framework handles accept, the receive loop, and
  serialisation.

.. tab-set::

    .. tab-item:: Django Channels
        :sync: django

        .. code-block:: python

            from channels.generic.websocket import AsyncJsonWebsocketConsumer

            class EchoConsumer(AsyncJsonWebsocketConsumer):
                async def connect(self):
                    await self.accept()

                async def receive_json(self, content):
                    await self.send_json({"echo": content["message"]})

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/websockets.py
            :language: python

For broadcast and pub/sub patterns (the ``channel_layer.group_send`` case)
Litestar provides the :doc:`channels </usage/channels>` plugin. It handles
per-channel subscriptions, message history, and inter-process fan-out through a
pluggable backend (memory, redis, asyncpg, psycopg), and can generate WebSocket
route handlers that publish incoming events to subscribed clients.

.. tab-set::

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/channels.py
            :language: python

.. seealso::

    * :doc:`/usage/websockets`
    * :doc:`/usage/channels`


Rate limiting
-------------

DRF's ``throttle_classes`` (``UserRateThrottle``, ``AnonRateThrottle``,
``ScopedRateThrottle``) limits per user, IP, or named scope through a cache backend.
Litestar's :class:`~litestar.middleware.rate_limit.RateLimitConfig` installs
:class:`~litestar.middleware.rate_limit.RateLimitMiddleware` with a pluggable store.

.. tab-set::

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            # settings.py
            REST_FRAMEWORK = {
                "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.UserRateThrottle"],
                "DEFAULT_THROTTLE_RATES": {"user": "60/minute"},
            }

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/rate_limiting.py
            :language: python


Testing
-------

Django's ``TestCase`` + ``Client`` and DRF's ``APITestCase`` + ``APIClient`` send
requests to the WSGI app in-process. Litestar ships
:class:`~litestar.testing.TestClient` (sync) and
:class:`~litestar.testing.AsyncTestClient` (async), both built on ``httpx``. For
unit-level handler tests, :func:`~litestar.testing.create_test_client` and
:func:`~litestar.testing.create_async_test_client` take the same arguments as
:class:`Litestar` and return a configured client.

.. tab-set::

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            from rest_framework.test import APITestCase

            class HelloTests(APITestCase):
                def test_index(self):
                    response = self.client.get("/")
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json(), {"hello": "world"})

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/test_handler.py
            :language: python

.. seealso::

    * :doc:`/usage/testing`


OpenAPI and the browsable API
-----------------------------

DRF generates an OpenAPI schema from view-and-serializer introspection and renders
an HTML "browsable API" for sessioned users. Litestar generates OpenAPI from
handler signatures and return types and serves multiple UIs out of the box: Swagger,
ReDoc, Scalar, RapiDoc, Stoplight Elements. Per-handler metadata sits on the
decorator (``tags``, ``summary``, ``description``, ``operation_id``); application-wide
options live on :class:`~litestar.openapi.config.OpenAPIConfig`, passed as
``openapi_config=`` to the application.

.. tab-set::

    .. tab-item:: DRF
        :sync: drf

        .. code-block:: python

            from drf_spectacular.utils import extend_schema

            class ItemView(APIView):
                @extend_schema(
                    tags=["items"],
                    summary="Retrieve an item",
                    description="Look up a single item by its numeric identifier.",
                    operation_id="get_item_by_id",
                )
                def get(self, request, item_id):
                    return Response({"id": item_id})

    .. tab-item:: Litestar
        :sync: litestar

        .. literalinclude:: /examples/onboarding/django/openapi.py
            :language: python

.. seealso::

    * :doc:`/usage/openapi/index`



Concepts without a direct equivalent
------------------------------------

A handful of Django features have no first-party Litestar counterpart.

**Django admin.** Litestar does not ship an admin interface. Community projects
such as `Starlette-Admin <https://jowilf.github.io/starlette-admin/>`_ and
`SQLAdmin <https://aminalaee.dev/sqladmin/>`_ work with any ASGI framework and can
be mounted on a Litestar app.

**Management commands (** ``manage.py`` **).** Litestar has no equivalent of
``django-admin`` / ``manage.py``, but plugins can register subcommands on the
``litestar`` CLI through the :class:`~litestar.plugins.CLIPluginProtocol`; for
one-off scripts, a plain ``click`` or ``typer`` script is the idiomatic choice.

**Apps and** ``AppConfig`` **.** Litestar has no per-app module system. The plugin
protocols (:class:`~litestar.plugins.InitPluginProtocol`,
:class:`~litestar.plugins.SerializationPluginProtocol`,
:class:`~litestar.plugins.OpenAPISchemaPluginProtocol`,
:class:`~litestar.plugins.CLIPluginProtocol`,
:class:`~litestar.plugins.DIPlugin`) cover the same ground: package up a feature
set (handlers, middleware, dependencies, CLI commands, schema customisations) and
register it on the application.

**Django Forms (HTML).** Litestar does not include HTML-rendering form scaffolding.
For HTML-form-driven UIs, render forms with the template engine and validate the
posted body with a DTO or model library.

**``get_object_or_404`` and model managers.** No first-party equivalent. The
SQLAlchemy repository's ``get_one_or_none`` paired with a raised
:class:`~litestar.exceptions.NotFoundException` is the typical pattern.


Further reading
---------------

These are not the only differences. The following pages cover features the guide
did not explore in depth:

- :doc:`/usage/dto/index`
- :doc:`/usage/security/index`
- :doc:`/usage/channels`
- :doc:`/usage/plugins/index`
- :doc:`/usage/openapi/index`


.. _django-migration-quick-reference:

Quick reference
---------------

A lookup table for the most common translations.

+--------------------------------+------------------------------------------+-------------------------------------------+
| Concept                        | Django / DRF                             | Litestar                                  |
+================================+==========================================+===========================================+
| Route declaration              | ``path("", views.index)`` in urls.py     | ``@get("/")`` + ``Litestar([handler])``   |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Class-based view               | ``APIView`` / ``ViewSet``                | ``Controller`` subclass                   |
+--------------------------------+------------------------------------------+-------------------------------------------+
| URL include                    | ``include("app.urls")``                  | ``Router(path=..., route_handlers=[...])``|
+--------------------------------+------------------------------------------+-------------------------------------------+
| Application config             | ``settings.py``                          | ``Litestar(...)`` constructor             |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Synchronous handler            | sync by default                          | ``@get(sync_to_thread=True)``             |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Path parameter                 | ``<int:item_id>`` + view kwarg           | ``{item_id:int}`` + ``FromPath[int]``     |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Query parameter                | ``request.GET.get("x")``                 | ``FromQuery[T]``                          |
+--------------------------------+------------------------------------------+-------------------------------------------+
| JSON body                      | ``serializer = S(data=request.data)``    | ``data: Item``                            |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Form data                      | ``request.POST``                         | ``Body(media_type=URL_ENCODED)``          |
+--------------------------------+------------------------------------------+-------------------------------------------+
| File upload                    | ``request.FILES["data"]``                | ``UploadFile`` + ``Body(MULTI_PART)``     |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Serializer                     | ``ModelSerializer``                      | DTO (``SQLAlchemyDTO``, ``DataclassDTO``) |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Default POST status            | ``200``                                  | ``201``                                   |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Default DELETE status          | ``200``                                  | ``204``                                   |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Cookies                        | ``response.set_cookie(...)``             | ``response_cookies=[Cookie(...)]``        |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Templates                      | ``render(request, "...", ctx)``          | ``Template()`` + ``TemplateConfig``       |
+--------------------------------+------------------------------------------+-------------------------------------------+
| URL reverse                    | ``reverse("name", kwargs={...})``        | ``request.url_for("name", ...)``          |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Exception                      | ``Http404``, ``raise NotFound(...)``     | ``raise NotFoundException(...)``          |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Exception handler              | ``EXCEPTION_HANDLER`` setting            | ``exception_handlers={Exc: handler}``     |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Authentication                 | ``authentication_classes = [...]``       | auth middleware or ``JWTAuth``            |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Permissions                    | ``permission_classes = [...]``           | ``guards=[...]``                          |
+--------------------------------+------------------------------------------+-------------------------------------------+
| CSRF                           | ``CsrfViewMiddleware``                   | ``csrf_config=CSRFConfig(...)``           |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Middleware                     | ``MIDDLEWARE = [...]``                   | ``ASGIMiddleware`` subclass               |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Per-request hook               | ``request_finished`` signal              | ``after_response=fn``                     |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Domain event                   | ``post_save`` signal                     | ``@listener`` + ``app.emit``              |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Background task                | Celery ``task.delay(...)``               | ``Response(background=BackgroundTask)``   |
+--------------------------------+------------------------------------------+-------------------------------------------+
| ORM                            | Django ORM                               | SQLAlchemy + ``SQLAlchemyPlugin``         |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Migrations                     | ``manage.py makemigrations``             | Alembic                                   |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Sessions                       | ``django.contrib.sessions``              | ``ServerSideSessionConfig`` + store       |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Static files                   | ``staticfiles`` + ``collectstatic``      | ``create_static_files_router(...)``       |
+--------------------------------+------------------------------------------+-------------------------------------------+
| WebSockets                     | Django Channels consumer                 | ``@websocket_listener("/ws")``            |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Pub/sub                        | Channels ``channel_layer.group_send``    | ``ChannelsPlugin``                        |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Throttling                     | ``throttle_classes = [...]``             | ``RateLimitConfig(...)``                  |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Test client                    | ``APIClient`` / ``Client``               | ``TestClient`` / ``create_test_client``   |
+--------------------------------+------------------------------------------+-------------------------------------------+
| OpenAPI schema                 | drf-spectacular / ``@extend_schema``     | per-decorator keywords + ``OpenAPIConfig``|
+--------------------------------+------------------------------------------+-------------------------------------------+
| Browsable API                  | DRF HTML renderer                        | Swagger / ReDoc / Scalar / RapiDoc        |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Pagination                     | ``pagination_class = ...``               | ``OffsetPagination[T]`` return type       |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Admin                          | ``django.contrib.admin``                 | no equivalent (Starlette-Admin, SQLAdmin) |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Management commands            | ``manage.py``                            | no equivalent (Click / Typer scripts)     |
+--------------------------------+------------------------------------------+-------------------------------------------+
| Apps                           | ``AppConfig`` / ``INSTALLED_APPS``       | plugins                                   |
+--------------------------------+------------------------------------------+-------------------------------------------+
