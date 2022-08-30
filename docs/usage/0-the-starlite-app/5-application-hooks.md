# Application Hooks

Starlite includes several application level hooks that allow users to run their own sync or async callables. While you
are free to use these hooks as you see fit, the design intention behin them is to allow for easy instrumentation for
observability (monitoring, tracing, logging etc.).

Hooks:

## Before / After Startup

The `before_startup` and `after_startup` hooks take a [sync or async callable][starlite.types.LifeSpanHookHandler] that
receives the Starlite application as an argument and run during the ASGI startup event. The callable is invoked
respectively before or after the list of callables defined in the `on_startup` list of callables.

```py title="Before and After Startup Hooks"
--8<-- "examples/application_hooks/startup_hooks.py"
```

## Before / After Shutdown

The `before_shutdown` and `after_shutdown` are basically identical, with the difference being that the
[callable they receive][starlite.types.LifeSpanHookHandler] in callable is invoked respectively before or after the
list of callables defined in the `on_shutdown` list of callables.

```py title="Before and After Shutdown Hooks"
--8<-- "examples/application_hooks/shutdown_hooks.py"
```

## After Exception

The `after_exception` take a [sync or async callable][starlite.types.AfterExceptionHookHandler] that is called with
three arguments: the `exception` that occurred, the ASGI `scope` of the request or websocket connection and the
application `state`.

```py title="After Exception Hooks"
--8<-- "examples/application_hooks/after_exception_hook.py"
```

!!! important
    This hook is not meant to handle exceptions - it just receives them to allow for side effects.
    To handle exceptions you should define [exception handlers](../17-exceptions.md#exception-handling).
