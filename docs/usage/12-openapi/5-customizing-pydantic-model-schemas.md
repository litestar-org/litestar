# Customizing Pydantic Model Schemas

You can customize the OpenAPI schemas generated for pydantic models by following the guidelines in
the [pydantic docs](https://pydantic-docs.helpmanual.io/usage/schema/).

Additionally, you can affect how pydantic models are translated into OpenAPI `components` by settings a special dunder attribute on the model called `__schema_name__`:

```py title="Customize Components Example"
--8<-- "examples/openapi/customize_pydantic_model_name.py"
```

The above will result in an OpenAPI schema object that looks like this:

```json
{
    "openapi": "3.1.0",
    "info": {"title": "Starlite API", "version": "1.0.0"},
    "servers": [{"url": "/"}],
    "paths": {
        "/id": {
            "get": {
                "operationId": "Retrieve Id Handler",
                "responses": {
                    "200": {
                        "description": "Request fulfilled, document follows",
                        "headers": {},
                        "content": {
                            "application/json": {
                                "media_type_schema": {
                                    "ref": "#/components/schemas/IdContainer"
                                }
                            }
                        },
                    }
                },
                "deprecated": False,
            }
        }
    },
    "components": {
        "schemas": {
            "IdContainer": {
                "properties": {
                    "id": {"type": "string", "schema_format": "uuid", "title": "Id"}
                },
                "type": "object",
                "required": ["id"],
                "title": "IdContainer",
            }
        }
    },
}
```
