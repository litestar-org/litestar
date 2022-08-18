# Middlewares and Exceptions

When an exception is raised by a route handler or dependency and is then transformed into a response by
an [exception handler](17-exceptions#exception-handling), middlewares are still applied to it. The one limitation on
this though are the two exceptions that can be raised by the ASGI router - `404 Not Found` and `405 Method Not Allowed`.
These exceptions are raised before the middleware stack is called, and are only handled by exceptions handlers defined
on the Starlite app instance itself. Thus, if you need to modify the responses generated for these exceptions, you will
need to define a custom exception handler on the app instance level.
