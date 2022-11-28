# Query Parameters

Query parameters are defined as keyword arguments to handler functions. Every keyword argument
that is not otherwise specified (for example as a [path parameter](usage/3-parameters/0-path-parameters/))
will be interpreted as a query parameter.

```py
--8<-- "examples/parameters/query_params.py"
```

If you run the app, then visit http://localhost:8000/?param=hello in your browser,
you'll see the following result:

```json
{"param": "hello"}
```

!!! info "Technical details"
      These parameters will be parsed from the function signature and used to generate a pydantic model.
      This model in turn will be used to validate the parameters and generate the OpenAPI schema.

      This means that you can also use any pydantic type in the signature, and it will
      follow the same kind of validation and parsing as you would get from pydantic.

Query parameters come in three basic types:

1. Required
2. Required with a default value
3. Optional with a default value

Query parameters are **required** by default. If one such a parameter has no value,
a `ValidationException` will be raised.

## Settings defaults

```py
--8<-- "examples/parameters/query_params_default.py"
```

In this example, `param` will have the value `"hello"` if it's not specified in the request.

Now, visiting http://localhost:8000 in your browser, results in

```json
{"param": "hello"}
```

without having specified the parameter. If you instead go to http://localhost:8000?param=world,
you'll see that the default has been overwritten:

```json
{"param": "world"}
```


## Optional parameters

Instead of only setting a default value, it's also possible to make a query parameter
entirely optional.

```py
--8<--"examples/parameters/query_params_optional.py"
```

Here, we give a default value of `None`, but still declare the type of the query parameter
to be a string. This means "This parameter is not required. If it is given, it has to be a string.
If it is not given, it will have a default value of `None`"

To see this behaviour in action run the app and navigate your browser to: http://localhost:8000

You'll see that the result is now:

```json
{"param": null}
```

If the query parameter is specified (http://localhost:8000?param=goodbye) it will be:

```json
{"param": "goodbye"}
```

## Type coercion

It is possible to coerce query parameters into different types. A query starts out as a string,
but its values can be parsed into all kinds of types. Since this is done by pydantic,
everything that works there will work for query parameters as well.


```py
--8<-- "examples/parameters/query_params_types.py"
```

Check it out by visiting: http://localhost:8000?date=2022-11-28T13:22:06.916540&floating_number=0.1&number=42&strings=1&strings=2

```json
{
      "datetime": "2022-11-29T13:22:06",
      "int":42,
      "float":0.1,
      "list":["1","2"]
}
```


## Specifying alternative names and constraints

Sometimes you might want to "remap" query parameters to allow a different name in the URL
than what's being used in the handler function. This can be done by making use of [Parameter](reference/params/0-parameter/).

```py
--8<--"examples/parameters/query_params_remap.py"
```

Here, we remap from `snake_case` in the handler function to `camelCase` in the URL.
This means that for the URL `http://127.0.0.1:8000?camelCase=foo`, the value of `camelCase`
will be used for the value of the `snake_case` parameter.

`Parameter` also allows us to define additional constraints:

```py
--8<-- "examples/parameters/query_params_constraints.py"
```

In this case, `param` is validated to be an _integer larger than 5_.
