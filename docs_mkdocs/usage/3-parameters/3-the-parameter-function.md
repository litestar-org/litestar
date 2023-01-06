# The Parameter Function

`Parameter` is a wrapper on top of the
pydantic [Field function](https://pydantic-docs.helpmanual.io/usage/schema/#field-customization) that extends it with a
set of Starlite specific kwargs. As such, you can use most of the kwargs of _Field_ with Parameter and have the same
parsing and validation. The additional kwargs accepted by `Parameter` are passed to the resulting pydantic `FieldInfo`
as an `extra`dictionary and have no effect on the working of pydantic itself.

See the [API Reference][starlite.params.Parameter] for full details on the `Parameter` function and the kwargs it accepts.
