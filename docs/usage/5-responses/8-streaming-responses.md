# Streaming Responses

To return a streaming response use the [`Stream`][starlite.datastructures.Stream] class. The Stream class receives a single required kwarg - `iterator`:

```python
--8<-- "examples/responses/streaming_responses.py"
```

!!! note
    You can use different kinds of values of the `iterator` keyword - it can be a callable returning a sync or async
    generator. The generator itself. A sync or async iterator class, or and instance of this class.

## The Stream Class

`Stream` is a container class used to generate streaming responses and their respective OpenAPI documentation.
See the [API Reference][starlite.datastructures.Stream] for full details on the `Stream` class and the kwargs it accepts.
