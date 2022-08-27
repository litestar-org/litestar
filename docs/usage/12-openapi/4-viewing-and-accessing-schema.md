# Viewing and Accessing Schema

Starlite comes with multiple integrations for documentation site generators. You can view and download your schema
using the endpoints exposed by the [OpenAPIController](3-openapi-controller.md).
For example, if you are running your app locally on `0.0.0.0:8000`, you would be able to:

- view your documentation in a Redoc site under `http://0.0.0.0:8000/schema/redoc`.
- view your documentation in a SwaggerUI site under `http://0.0.0.0:8000/schema/swagger`.
- view your documentation in a StopLight Elements site under `http://0.0.0.0:8000/schema/elements`.
- download your documentation as YAML using `http://0.0.0.0:8000/schema/openapi.yaml`.
- download your documentation as JSON using `http://0.0.0.0:8000/schema/openapi.json`.

## Accessing the OpenAPI Schema in Code

The OpenAPI schema is generated during the [Starlite][starlite.app.Starlite] app's init method. Once init is finished,
its accessible as `app.openapi_schema`. As such you can always access it inside route handlers, dependencies etc. by
access the request instance:

```python
from starlite import Request, get


@get(path="/")
def my_route_handler(request: Request) -> dict:
    schema = request.app.openapi_schema
    return schema.dict()
```
