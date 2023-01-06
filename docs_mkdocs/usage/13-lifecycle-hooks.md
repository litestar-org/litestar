# Life Cycle Hooks

Life cycle hooks allow the execution of a callable at a certain point during the request-response
cycle. The hooks available are:

| Name                                | Runs                               |
|-------------------------------------|------------------------------------|
| [`before_request`](#before-request) | Before the router handler function |
| [`after_request`](#after-request)   | After the route handler function   |
| [`after_response`](#after-response) | After the response has been sent   |


## Before Request

The `before_request` hook runs immediately before calling the route handler function. It
can be any callable accepting a [`Request`][starlite.Request] as its first parameter
and returns either `None` or a value that can be used in a response.
If a value is returned, the router handler for this request will be bypassed.

```py
--8<-- "examples/lifecycle_hooks/before_request.py"
```

## After Request

The `after_request` hook runs after the route handler returned and the response object
has been resolved. It can be any callable which takes a [`Response`][starlite.Response]
instance as its first parameter, and returns a `Response` instance. The `Response`
instance returned does not necessarily have to be the one that was received.

```py
--8<-- "examples/lifecycle_hooks/after_request.py"
```

## After Response

The `after_response` hook runs after the response has been returned by the server.
It can be any callable accepting a [`Request`][starlite.Request] as its first parameter
and does not return any value.

This hook is meant for data post-processing, transmission of data to third party
services, gathering of metrics etc.

```py
--8<-- "examples/lifecycle_hooks/after_response.py"
```

!!! info "Explanation"
    Since the request has already been returned by the time the `after_response` is called,
    the updated state of `COUNTER` is not reflected in the response.


## Layered hooks


!!! info "Layered architecture"
    Life cycle hooks are part of Starlite's layered architecture, which means you can
    set them on every layer of the application. If you set hooks on multiple layers,
    the layer closest to the route handler will take precedence.

    You can read more about this here:
    [Layered architecture](/starlite/usage/0-the-starlite-app#layered-architecture)


```py
--8<-- "examples/lifecycle_hooks/layered_hooks.py"
```
