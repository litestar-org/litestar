Events
======

Litestar supports a simple implementation of the event emitter / listener pattern:

.. code-block:: python
    :caption: Using Litestar events to decouple and organize async tasks

    from dataclasses import dataclass

    from db import user_repository

    from litestar import Litestar, Request, post
    from litestar.events import listener
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
        # emit an event to send a welcome email, but in a non-blocking fashion
        request.app.emit("user_created", email=data.email)


    app = Litestar(route_handlers=[create_user_handler], listeners=[send_welcome_email_handler])

The above example illustrates the power of this pattern: the :class:`post <.handlers.post>` handler for ``/users``,
we are emitting an event ``user_created``. This event is listened to by the ``send_welcome_email_handler`` function,
which sends a welcome email to the user but it allows us to perform async operations without blocking,
and without slowing down the response cycle.

Listening to Multiple Events
++++++++++++++++++++++++++++

Event listeners can listen to multiple events:

.. code-block:: python
    :caption: Listen to multiple events to send an email

    from litestar.events import listener
    from utils.email import send_email

    @listener("user_created", "password_changed")
    async def send_email_handler(email: str, message: str) -> None:
        # on user create or password change, send an email
        await send_email(email, message)

Using Multiple Listeners
++++++++++++++++++++++++

You can also listen to the same events using multiple listeners:

.. dropdown:: Example of using multiple listeners over many functions

    .. code-block:: python
        :caption: Using multiple listeners to send an email

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

In the provided example, when a user is deleted, two actions are triggered simultaneously by the ``user_deleted`` event.
The first action sends a farewell email to the user, while the second action creates an issue in a service management
system by sending an HTTP request.

This demonstrates how multiple listeners can respond to the same event with different side effects.

Passing Arguments to Listeners
++++++++++++++++++++++++++++++

The method :meth:`~litestar.events.BaseEventEmitterBackend.emit` has the following signature:

.. code-block:: python
    :caption: The ``emit`` method signature

    def emit(self, event_id: str, *args: Any, **kwargs: Any) -> None: ...

This means that it expects a string for ``event_id`` following by any number of positional and keyword arguments.
While this is highly flexible, it also means you need to ensure the listeners for a given event can handle
all the expected args and kwargs.

For example, the following would raise an exception in Python:

.. dropdown:: Example of mismatched arguments in event listeners

    .. code-block:: python
        :caption: Mismatched arguments in event listeners

        from dataclasses import dataclass

        from litestar import Request, post
        from litestar.events import listener

        from db import user_repository
        from utils.client import client
        from utils.email import send_farewell_email

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

The reason for this is that both listeners will receive two kwargs - ``email`` and ``reason``.
To avoid this, the previous example had ``**kwargs`` in both:

.. code-block:: python
    :caption: Using ``**kwargs`` to handle arbitrary keyword arguments in event listeners

    @listener("user_deleted")
    async def send_farewell_email_handler(email: str, **kwargs) -> None:
        await send_farewell_email(email)


    @listener("user_deleted")
    async def notify_customer_support(reason: str, **kwargs) -> None:
        await client.post("some-url", reason)

Creating Event Emitters
-----------------------

An "event emitter" is a class that inherits from :class:`~litestar.events.BaseEventEmitterBackend`,
which itself inherits from :obj:`~contextlib.AbstractAsyncContextManager`.

- :meth:`~litestar.events.BaseEventEmitterBackend.emit`: This is the method that performs the actual emitting
  logic.

Additionally, the abstract :meth:`~object.__aenter__` and :meth:`~object.__aexit__` methods from
:class:`~contextlib.AbstractAsyncContextManager` must be implemented, allowing the
emitter to be used as an :term:`asynchronous context manager`

By default Litestar uses the :class:`~litestar.events.SimpleEventEmitter`, which offers an in-memory async queue.

This solution works well if the system does not need to rely on complex behaviour, such as a retry mechanism,
persistence, or scheduling/cron. For these more complex use cases, users should implement their own backend
using either a database or or key store that supports events (Redis, Postgres, etc.), or a message broker, job queue,
or similar task queue technology.
