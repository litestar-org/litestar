# Data Transfer Objects (DTOs)
<!-- markdownlint-disable MD052 -->

Starlite includes a [`DTOFactory`][starlite.dto.DTOFactory] class that allows you to create DTOs from pydantic models,
dataclasses, [`TypedDict`][typing.TypedDict], and any other class supported via plugins.

An instance of the factory must first be created, optionally passing plugins to it as a kwarg. It can then be used to
create a [`DTO`][starlite.dto.DTO] by calling the instance like a function. Additionally, it can exclude (drop)
attributes, remap field names and field types, and add new fields.

The created [`DTO`][starlite.dto.DTO] can be used for data parsing, validation and OpenAPI schema generation like a
regularly declared pydantic model.

!!! important
    Although the value generated is a pydantic factory, because it is being generated programmatically, it's
    currently impossible to extend editor auto-complete for the DTO properties - it will be typed as `DTO[T]`,
    with T being a generic argument representing the original model used to create the DTO.

!!! note
    MyPy doesn't support using types defined using `Type[]` as a type, and MyPy will regard these as invalid types.
    There is currently no way to circumvent this (not even with a plugin) except using a # type: ignore comment.

The [`DTOFactory`][starlite.dto.DTOFactory] class supports [plugins](../10-plugins/0-plugins-intro.md), for example, this
is how it could be used with an SQLAlchemy declarative class using the
[SQLAlchemyPlugin](../10-plugins/1-sql-alchemy-plugin.md):

```py title="Declaring a DTO"
--8<-- "examples/data_transfer_objects/dto_basic.py"
```

The created `CompanyDTO` is equal to this pydantic model declaration:

```python
from pydantic import BaseModel


class CompanyDTO(BaseModel):
    id: int
    name: str
    worth: float
```

You can now use it in route handler functions as you would any other pydantic model. The one caveat though is lack of
editor completion and mypy support - this requires the implementation of a mypy plugin, which is planned for the future.

## Excluding Fields

You can exclude any field in the original model class from the [`DTO`][starlite.dto.DTO]:

```py title="Excluding fields"
--8<-- "examples/data_transfer_objects/dto_exclude_fields.py"
```

The generated `MyClassDTO` is equal to this model declaration:

```python
from pydantic import BaseModel


class MyClassDTO(BaseModel):
    second: int
```

## Remapping Fields

You can remap fields in two ways:

1. you can switch change their keys:

```py title="Remapping fields"
--8<-- "examples/data_transfer_objects/dto_remap_fields.py"
```

The generated `MyClassDTO` is equal to this model declaration:

```python
from pydantic import BaseModel


class MyClassDTO(BaseModel):
    second: int
    third: int
```

You can remap name and type. To do this use a tuple instead of a string for the object value:

```py title="Remapping fields with types"
--8<-- "examples/data_transfer_objects/dto_remap_fields_with_types.py"
```

The generated `MyClassDTO` is equal to this model declaration:

```python
from pydantic import BaseModel


class MyClassDTO(BaseModel):
    third: int
    fourth: float
```

## Add New Fields

You add fields that do not exist in the original model by passing in a `field_definitions` dictionary. This dictionary
should have field names as keys, and a tuple following the format supported by the
[pydantic create_model helper](https://pydantic-docs.helpmanual.io/usage/models/#dynamic-model-creation):

1. For required fields use a tuple of type + ellipsis, for example `(str, ...)`.
2. For optional fields use a tuple of type + `None`, for example `(str, None)`
3. To set a default value use a tuple of type + default value, for example `(str, "Hello World")`

```py title="Add new fields"
--8<-- "examples/data_transfer_objects/dto_add_new_fields.py"
```

The generated `MyClassDTO` is equal to this model declaration:

```python
from pydantic import BaseModel


class MyClassDTO(BaseModel):
    first: int
    second: int
    third: str
```

## DTO Methods

### DTO.from_model_instance()

Once you create a DTO class you can use its class method [`from_model_instance()`][starlite.dto.DTO.from_model_instance]
to create an instance from an existing instance of the model from which the DTO was generated:

```py title="DTO.from_model_instance()"
--8<-- "examples/data_transfer_objects/dto_from_model_instance.py"
```

In the above, `dto_instance` is a validated pydantic model instance.

### DTO.to_model_instance()

When you have an instance of a [`DTO`][starlite.dto.DTO] model, you can convert it into a model instance using the
[`to_model_instance()`][starlite.dto.DTO.to_model_instance] method:

```py title="DTO.to_model_instance()"
--8<-- "examples/data_transfer_objects/dto_to_model_instance.py"
```

In the above `company_instance` is an instance of the SQLAlchemy declarative class `Company`. It is correctly typed as
`Company` because the [`DTO`][starlite.dto.DTO] class uses generic to store this data.

!!! important
    If you exclude keys or add additional fields, you should make sure this does not cause an error when trying to
    generate a model class from a dto instance. For example, if you exclude required fields from a pydantic model and try
    to create an instance from a dto that doesn't have these, a validation error will be raised.

## Automatic Conversion on Response

When you use a DTO as a return type in a route handler, if the returned data is a model or a dict, it will be converted to the DTO automatically:

```py title="DTO automatic conversion"
--8<-- "examples/data_transfer_objects/dto_auto_conversion.py"
```

In the above, when requesting route of a company, the `secret` attribute will not be included in the response. And it also works when returning a list of companies.
