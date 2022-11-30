# Request Data

## Request body

The body of HTTP requests can be accessed using the special `data` parameter in a handler function.

```py
--8<-- "examples/request_data/request_data_1.py"
```


The type of `data` an be any supported type, including

- [dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [`TypedDict`s][typing.TypedDict]
- Pydantic models
- Arbitrary stdlib types
- Typed supported via [plugins](/usage/10-plugins/0-plugins-intro.md)


```py
--8<-- "examples/request_data/request_data_2.py"
```


## Validation and customizing OpenAPI documentation

With the help of [Body][starlite.params.Body], you have fine-grained control over the validation
of the request body, and can also customize the OpenAPI documentation:

```py
--8<-- "examples/request_data/request_data_3.py"
```


## Specifying a content-type

By default, Starlite will try to parse the request body as JSON. While this may be desired
in most cases, you might want to specify a different type. You can do so by passing a
[RequestEncodingType][starlite.enums.RequestEncodingType] to `Body`. This will also
help to generate the correct media-type in the OpenAPI schema.

### URL Encoded Form Data

To access data sent as [url-encoded form data](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST),
i.e. `application/x-www-form-urlencoded` Content-Type header, use [`Body`][starlite.params.Body] and specify
[`RequestEncodingType.URL_ENCODED`][starlite.enums.RequestEncodingType] as the `media_type`:

```py
--8<-- "examples/request_data/request_data_4.py"
```



!!! info
    URL encoded data is inherently less versatile than JSON data - for example, it cannot handle complex
    dictionaries and deeply nested data. It should only be used for simple data structures.

### MultiPart Form Data

You can access data uploaded using a request with a [`multipart/form-data`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST)
Content-Type header by specifying it in the [`Body`][starlite.params.Body] function:

```py
--8<-- "examples/request_data/request_data_5.py"
```


## File uploads

In case of files uploaded, Starlite transforms the results into an instance
of [`UploadFile`][starlite.datastructures.UploadFile] class, which offer a convenient
interface for working with files. Therefore, you need to type your file uploads accordingly.

To access a single file simply type `data` as `UploadFile`:

=== "Async"
    ```py
    --8<-- "examples/request_data/request_data_6.py"
    ```

=== "Sync"
    ```py
    --8<-- "examples/request_data/request_data_7.py"
    ```

    !!! tip "Technical details"
        `UploadFile.read` wraps [SpooledTemporaryFile][tempfile.SpooledTemporaryFile]
        so it can be used asynchronously. Inside of a synchronous function we don't need
        this wrapper, so we can use `SpooledTemporaryFile.read()` directly.


### Multiple files

To access multiple files with known filenames, you can use a pydantic model:

```py
--8<-- "examples/request_data/request_data_8.py"
```


### Files as a dictionary

If you do not care about parsing and validation and only want to access the form data as a dictionary, you can use a `dict` instead:

```py
--8<-- "examples/request_data/request_data_9.py"
```


### Files as a list

Finally, you can also access the files as a list without the filenames:

```py
--8<-- "examples/request_data/request_data_10.py"
```


## MessagePack data

To receive `MessagePack` data, you can either specify the appropriate `Content-Type`
with `Body`,  or set the `Content-Type` header of the request to `application/x-msgpack`.

```py title="msgpack_request.py"
--8<-- "examples/request_data/msgpack_request.py"
```