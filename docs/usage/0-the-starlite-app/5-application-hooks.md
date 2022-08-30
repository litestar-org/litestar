# Application Hooks

Starlite includes several application level hooks that allow users to run their own sync or async callables. While you
are free to use these hooks as you see fit, the design intention behin them is to allow for easy instrumentation for
observability (monitoring, tracing, logging etc.).

Hooks:

- `before_startup` and `after_startup`: A sync or async callable that receives the Starlite application as an argument
  and run during the ASGI startup event. The callable is invoked either before or after the list of callables defined in
  the `on_startup` list of callables.

```py title="Before and After Startup Hooks"
--8<-- "examples/application_hooks/startup_hooks.py"
```

- `before_shutdown` and `after_shutdown`: A sync or async callable that receives the Starlite application as an argument
  and run during the ASGI shutdown event. The callable is invoked either before or after the list of callables defined in
  the `on_shutdown` list of callables.
