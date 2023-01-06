# The Dependency Function

## Dependency validation

By default, injected dependency values are validated by Starlite, for example, this application will raise an
internal server error:

```py title="Dependency validation error"
--8<-- "examples/dependency_injection/dependency_validation_error.py"
```

Dependency validation can be toggled using the [`Dependency`][starlite.params.Dependency] function.

```py title="Dependency validation error"
--8<-- "examples/dependency_injection/dependency_skip_validation.py"
```

This may be useful for reasons of efficiency, or if pydantic cannot validate a certain type, but use with caution!

## Dependency function as a marker

The [`Dependency`][starlite.params.Dependency] function can also be used as a marker that gives us a bit more detail
about your application.

### Exclude dependencies with default values from OpenAPI docs

Depending on your application design, it is possible to have a dependency declared in a handler or
[`Provide`][starlite.datastructures.Provide] function that has a default value. If the dependency isn't provided for
the route, the default should be used by the function.

```py title="Dependency with default value"
--8<-- "examples/dependency_injection/dependency_default_value_no_dependency_fn.py"
```

This doesn't fail, but due to the way the application determines parameter types, this is inferred to be a query
parameter:

<img alt="Dependency query parameter" src="../images/dependency_query_parameter.png" width="auto" height="auto">

By declaring the parameter to be a dependency, Starlite knows to exclude it from the docs:

```py title="Dependency with default value"
--8<-- "examples/dependency_injection/dependency_default_value_with_dependency_fn.py"
```

### Early detection if a dependency isn't provided

The other side of the same coin is when a dependency isn't provided, and no default is specified. Without the dependency
marker, the parameter is assumed to be a query parameter and the route will most likely fail when accessed.

If the parameter is marked as a dependency, this allows us to fail early instead:

```py title="Dependency not provided error"
--8<-- "examples/dependency_injection/dependency_non_optional_not_provided.py"
```
