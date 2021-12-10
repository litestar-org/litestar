from pydantic.fields import ModelField


def set_field_optional(field: ModelField) -> ModelField:
    """Given a model field, set it to optional and update all sub_fields recursively"""
    field.required = False
    field.allow_none = True
    if field.sub_fields:
        for index, sub_field in enumerate(field.sub_fields):
            field.sub_fields[index] = set_field_optional(field=sub_field)
    return field
