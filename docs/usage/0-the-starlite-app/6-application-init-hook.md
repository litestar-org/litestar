# Application Init Hook

Starlite includes a hook for intercepting the arguments passed to the [Starlite][starlite.app.Starlite] constructor,
before they are used to instantiate the application.

Handlers can be passed to the `on_app_init` parameter on construction of the application, and in turn, each will receive
an instance of [AppConfig][starlite.config.app.AppConfig] and must return an instance of same.

This hook is useful for applying common configuration between applications, and for use by developers who may wish to
develop third-party application configuration systems.

!!! Note
    `on_app_init` handlers cannot be `async def` functions, as they are called within `Starlite.__init__()`, outside of
    an async context.

```py title="After Exception Hook"
--8<-- "examples/application_hooks/on_app_init.py"
```
