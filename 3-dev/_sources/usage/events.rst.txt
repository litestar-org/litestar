Events
======

Litestar supports a simple implementation of the event emitter / listener pattern:

.. code-block:: python

    from dataclasses import dataclass

    from litestar import Request, post
    from litestar.events import listener
    from litestar import Litestar

    from db import user_repository
    from utils.email import send_welcome_mail


    @listener("user_created")
    async def send_welcome_email_handler(email: str) -> None:
        # do something here to send an email
        await send_welcome_mail(email)


    @dataclass
    class CreateUserDTO:
        first_name: str
        last_name: str
        email: str


    @post("/users")
    async def create_user_handler(data: UserDTO, request: Request) -> None:
        # do something here to create a new user
        # e.g. insert the user into a database
        await user_repository.insert(data)

        # assuming we have now inserted a user, we want to send a welcome email.
        # To do this in a none-blocking fashion, we will emit an event to a listener, which will send the email,
        # using a different async block than the one where we are returning a response.
        request.app.emit("user_created", email=data.email)


    app = Litestar(
        route_handlers=[create_user_handler], listeners=[send_welcome_email_handler]
    )


The above example illustrates the power of this pattern - it allows us to perform async operations without blocking,
and without slowing down the response cycle.

Listening to Multiple Events
++++++++++++++++++++++++++++

Event listeners can listen to multiple events:

.. code-block:: python

    from litestar.events import listener


    @listener("user_created", "password_changed")
    async def send_email_handler(email: str, message: str) -> None:
        # do something here to send an email

        await send_email(email, message)




Using Multiple Listeners
++++++++++++++++++++++++

You can also listen to the same events using multiple listeners:

.. code-block:: python

    from uuid import UUID
    from dataclasses import dataclass

    from litestar import Request, post
    from litestar.events import listener

    from db import user_repository
    from utils.client import client
    from utils.email import send_farewell_email


    @listener("user_deleted")
    async def send_farewell_email_handler(email: str, **kwargs) -> None:
        # do something here to send an email
        await send_farewell_email(email)


    @listener("user_deleted")
    async def notify_customer_support(reason: str, **kwargs) -> None:
        # do something here to send an email
        await client.post("some-url", reason)


    @dataclass
    class DeleteUserDTO:
        email: str
        reason: str


    @post("/users")
    async def delete_user_handler(data: UserDTO, request: Request) -> None:
        await user_repository.delete({"email": email})
        request.app.emit("user_deleted", email=data.email, reason="deleted")



In the above example we are performing two side effect for the same event, one sends the user an email, and the other
sending an HTTP request to a service management system to create an issue.

Passing Arguments to Listeners
++++++++++++++++++++++++++++++

The method :meth:`emit <litestar.events.BaseEventEmitterBackend.emit>` has the following signature:

.. code-block:: python

    def emit(self, event_id: str, *args: Any, **kwargs: Any) -> None: ...



This means that it expects a string for ``event_id`` following by any number of positional and keyword arguments. While
this is highly flexible, it also means you need to ensure the listeners for a given event can handle all the expected args
and kwargs.

For example, the following would raise an exception in python:

.. code-block:: python

    @listener("user_deleted")
    async def send_farewell_email_handler(email: str) -> None:
        await send_farewell_email(email)


    @listener("user_deleted")
    async def notify_customer_support(reason: str) -> None:
        # do something here to send an email
        await client.post("some-url", reason)


    @dataclass
    class DeleteUserDTO:
        email: str
        reason: str


    @post("/users")
    async def delete_user_handler(data: UserDTO, request: Request) -> None:
        await user_repository.delete({"email": email})
        request.app.emit("user_deleted", email=data.email, reason="deleted")



The reason for this is that both listeners will receive two kwargs - ``email`` and ``reason``. To avoid this, the previous example
had ``**kwargs`` in both:

.. code-block:: python

    @listener("user_deleted")
    async def send_farewell_email_handler(email: str, **kwargs) -> None:
        await send_farewell_email(email)


    @listener("user_deleted")
    async def notify_customer_support(reason: str, **kwargs) -> None:
        await client.post("some-url", reason)



Creating Event Emitters
-----------------------

An "event emitter" is a class that inherits from
:class:`BaseEventEmitterBackend <litestar.events.BaseEventEmitterBackend>`, which
itself inherits from :obj:`contextlib.AbstractAsyncContextManager`.

- :meth:`emit <litestar.events.BaseEventEmitterBackend.emit>`: This is the method that performs the actual emitting
  logic.

Additionally, the abstract ``__aenter__`` and ``__aexit__`` methods from
:obj:`contextlib.AbstractAsyncContextManager` must be implemented, allowing the
emitter to be used as an async context manager.

By default Litestar uses the
:class:`SimpleEventEmitter <litestar.events.SimpleEventEmitter>`, which offers an
in-memory async queue.

This solution works well if the system does not need to rely on complex behaviour, such as a retry
mechanism, persistence, or scheduling/cron. For these more complex use cases, users should implement their own backend
using either a DB/Key store that supports events (Redis, Postgres, etc.), or a message broker, job queue, or task queue
technology.
