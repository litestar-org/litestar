# Layered Parameters

As part of Starlite's "layered" architecture, you can declare parameters not only as part of individual route handler
functions, but also on other layers of the application:

```python
--8 < --"examples/parameters/layered_parameters.py"
```


In the above we declare parameters on the app, router and controller levels in addition to those declared in the route
handler. Let's look at these closer.

- `app_param` is a cookie param with the key `special-cookie`. We type it as `str` by passing this as an arg to
  the `Parameter` function. This is required for us to get typing in the OpenAPI docs. Additionally, this parameter is
  assumed to be required because it is not explicitly declared as `required=False`. This is important because the route
  handler function does not declare a parameter called `app_param` at all, but it will still require this param to be
  sent
  as part of the request of validation will fail.

- `router_param` is a header param with the key `MyHeader`. Because its declared as `required=False`, it will not fail
  validation if not present unless explicitly declared by a route handler - and in this case it is. Thus, it is actually
  required for the router handler function that declares it as an `str` and not an `Optional[str]`. If a string value is
  provided, it will be tested against the provided regex.

- `controller_param` is a query param with the key `controller_param`. It has an `lt=100` defined on the controller,
  which
  means the provided value must be less than 100. Yet the route handler re-declares it with an `lt=50`, which means for
  the route handler this value must be less than 50.

- Finally `local_param` is a route handler local query parameter, and `path_param` is a path parameter.

!!! note
    You cannot declare path parameters in different application layers. The reason for this is to ensure
    simplicity - otherwise parameter resolution becomes very difficult to do correctly.
