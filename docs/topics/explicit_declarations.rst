Explicit parameter declarations
===============================

Litestar embraces and enforces explicit declarations of handler / dependency parameters.
This articles aims to explain the motivations behind this decision, and address common
questions and objections regarding its downsides.


What? Explicit declarations?
----------------------------

Simply put, in Litestar, an explicit parameter declaration is any handler or dependency
function parameter, marked with a *marker* such as :class:`~litestar.params.FromQuery`,
e.g.

.. code-block:: python

    @get("/")
    async def handler(name: FromQuery[str]) -> str:
        return name


.. seealso::
    :doc:`/usage/routing/parameters`



Historical background
---------------------

Previous versions of Litestar allowed implicit parameters, i.e. parameter sources were
decided via inference. Specifically, this was possible for path, query, and dependency
parameters.

.. code-block:: python
    :caption: Declaring a query parameter 'message'

    @get("/")
    async def handler(message: str) -> str:
        return message

Here, because ``message`` is not "consumed" by other sources, would implicitly become a
query parameter.

This was influenced by the design of other frameworks such as FastAPI or DRF, and aimed
to provide convenience when writing.

However, it gets tricky quickly. For example, if the same route handler would be
included in a router with a path parameter with the name ``message``, the path parameter
would win, and ``message`` wouldn't be a query parameter anymore.

This means that the inferred parameter source is context dependant.

There are upsides to this, for example, one could argue that this is a practical
application of the
`Inversion of Control <https://en.wikipedia.org/wiki/Inversion_of_control>`_ pattern via
dependency injection; The callee declaring the parameter does not need to know anything
about the context it's being called from, it simply declares its dependencies, leaving
it up to the caller how to provide them.

This though still holds true with explicit declarations: The callee simply declares
additional information, i.e. the kind of parameter it requires, which in most cases is
not a purely cosmetic difference, but carries meaning: A ``x-api-key`` header is not
equivalent to a query parameter of the same name.


Motivation
----------


Easy to read over easy to write
+++++++++++++++++++++++++++++++

Spelling out additional symbols for each declaration is more typing work, there's no
arguing with that. Since "code is read much more often than it is written", and most of
a developer's time is spent understanding and reasoning about code [1]_, it should
follow that a library should first and foremost be easy to comprehend.

Therefore, when designing Litestar's explicit parameter declarations, the goal was that
to design them in such a way that "any reader, even if unfamiliar with the framework can
understand their meaning looking at the declarations alone and perhaps their docstrings
for nuance".

**Easy to write**

.. code-block:: python
    :caption: This is easy to write!

    @get("/")
    async def handler(
        data: dict[str, str],
        limit: int,
        page: Annotated[int, Parameter(ge=1)],
        db_session: AsyncSession,
    ) -> None:
        ...

This is easy to write, or rather, easy to type. However, there's not much information
available to a reader. Where do ``data`` and all the other parameters come from? One
could infer from ``limit`` and ``page`` that they're probably query parameters, but as
discussed in `Historical background`_, that could also be context dependant.


**Easy to read**

.. code-block:: python
    :caption: This is easy to read

    @get("/")
    async def handler(
        data: JSONBody[dict[str, str]],
        limit: Annotated[int, QueryParameter()],
        page: Annotated[int, QueryParameter(ge=1)],
        db_session: NamedDependency[AsyncSession],
    ) -> None:
        ...

This is much more verbose, but it's also packed with information:

- ``data: JSONBody[dict[str, str]]`` tells us:
   - This is the request body
   - The request body is in JSON
- ``limit: Annotated[int, QueryParameter()]``: This *is* a query parameter
- ``page: Annotated[int, QueryParameter(ge=1)]``: Another query parameter
- ``db_session: NamedDependency[AsyncSession]`` It's a dependency with a name


Avoiding errors
+++++++++++++++

An explicit approach brings the significant benefit of being able to fail early; If a
parameter has no declared source, Litestar can immediately raise an error about this,
preventing time consuming runtime debugging.

For example, a very common, and sometimes surprising, error with the inference based
approach was a ``missing required query parameter 'xxx'``, if a dependency was not
provided. Why? Because whether a parameter is interpreted as a dependency or a query
parameter depends on the presence of a dependency provider. If no provider is present,
the parameter would get interpreted as a query parameter, and, if given no default,
marked as required.

.. code-block:: python

    @get("/")
    async def get_page(db_session: AsyncSession) -> None:
        ...

    router_a = Router("/a", [get_page], dependencies={"db_session": provide_session})
    router_b = Router("/b", [get_page])

Calling ``/a`` would work as expected, but calling ``/b`` would result in a
``400 - Bad Request`` with the info ``missing required query parameter 'db_session'``.


Documenting intent
++++++++++++++++++

When using implicit declarations, the intent is also implicitly documented, i.e. not.
Intent not expressed by the code usually goes one of two ways: Either it is documented
in comments, or eventually forgotten. Through the use of explicit declarations, intent
is *always* encoded right at the site of use, and not separate comment needs to be added
and kept up to date.


.. [1] https://web.archive.org/web/20250619090027/https://cacm.acm.org/research/from-code-complexity-metrics-to-program-comprehension/
