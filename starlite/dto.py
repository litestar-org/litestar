from dataclasses import is_dataclass
from typing import Any, Dict, ForwardRef, List, Optional, Tuple, Union, cast

from pydantic import BaseModel, create_model
from pydantic.fields import ModelField, Undefined
from typing_extensions import Type

from starlite.exceptions import ImproperlyConfiguredException
from starlite.plugins import PluginProtocol, get_plugin_for_value
from starlite.utils import convert_dataclass_to_model


class DTOFactory:
    def __init__(self, plugins: Optional[List[PluginProtocol]] = None):
        self.plugins = plugins or []

    def __call__(
        self,
        name: str,
        source: Any,
        exclude: Optional[List[str]] = None,
        field_mapping: Optional[Dict[str, Union[str, Tuple[str, Any]]]] = None,
    ) -> Type[BaseModel]:
        """
        Given a supported model class - either pydantic, dataclass or a class supported via plugins,
        create a DTO pydantic model class.

        An instance of the factory must first be created, passing any plugins to it.
        It can then be used to create a DTO by calling the instance like a function. Additionally, it can exclude (drop)
        attributes specifies in the 'exclude' list and remap field names and/or field types.

        For example, given a pydantic model

            class MyClass(BaseModel):
                first: int
                second: int

            MyClassDTO = DTOFactory()(MyClass, exclude=["first"], field_mapping={"second": ("third", float)})

        `MyClassDTO` is now equal to this:
            class MyClassDTO(BaseModel):
                third: float

        It can be used as a regular pydantic model:

            @post(path="/my-path)
            def create_obj(data: MyClassDTO) -> MyClass:
                ...

        This will affect parsing, validation and how OpenAPI schema is generated exactly like when using a pydantic model.

        Note: Although the value generated is a pydantic factory, because it is being generated programmaticaly,
        it's currently not possible to extend editor auto-complete for the DTO properties - it will be typed as a
        Pydantic BaseModel, but no attributes will be inferred in the editor.
        """
        fields: Dict[str, ModelField]
        exclude = exclude or []
        field_mapping = field_mapping or {}
        field_definitions: Dict[str, Tuple[Any, Any]] = {}
        if issubclass(source, BaseModel):
            source.update_forward_refs()
            fields = source.__fields__
        elif is_dataclass(source):
            fields = convert_dataclass_to_model(source).__fields__
        else:
            plugin = get_plugin_for_value(value=source, plugins=self.plugins)
            if not plugin:
                raise ImproperlyConfiguredException(
                    f"No supported plugin found for value {source} - cannot create value"
                )
            model = plugin.to_pydantic_model_class(model_class=source)
            fields = model.__fields__
        for field_name, model_field in fields.items():
            if field_name not in exclude:
                outer_type = model_field.outer_type_
                field_type = outer_type if not isinstance(outer_type, ForwardRef) else model_field.type_
                if field_name in field_mapping:
                    mapping = field_mapping[field_name]
                    if isinstance(mapping, tuple):
                        field_name, field_type = mapping
                    else:
                        field_name = mapping
                if model_field.field_info.default is not Undefined:
                    field_definitions[field_name] = (field_type, model_field.default)
                elif not model_field.allow_none:
                    field_definitions[field_name] = (field_type, ...)
                else:
                    field_definitions[field_name] = (field_type, None)
        return cast(Type[BaseModel], create_model(name, **field_definitions))  # type: ignore
