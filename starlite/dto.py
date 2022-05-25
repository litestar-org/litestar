from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar, Union, cast

from pydantic import BaseConfig, BaseModel, create_model
from pydantic.fields import SHAPE_SINGLETON, ModelField, Undefined
from pydantic.generics import GenericModel
from typing_extensions import ClassVar, Type

from starlite.exceptions import ImproperlyConfiguredException
from starlite.plugins import PluginProtocol, get_plugin_for_value
from starlite.utils import convert_dataclass_to_model


def get_field_type(model_field: ModelField) -> Any:
    """Given a model field instance, return the correct type"""
    outer_type = model_field.outer_type_
    inner_type = model_field.type_
    if "ForwardRef" not in repr(outer_type):
        return outer_type
    if model_field.shape == SHAPE_SINGLETON:
        return inner_type
    # This might be too simplistic
    return List[inner_type]  # type: ignore


T = TypeVar("T")


class DTO(GenericModel, Generic[T]):
    class Config(BaseConfig):
        arbitrary_types_allowed = True

    dto_source_model: ClassVar[Any]
    dto_field_mapping: ClassVar[Dict[str, str]]
    dto_source_plugin: ClassVar[Optional[PluginProtocol]] = None

    @classmethod
    def from_model_instance(cls, model_instance: T) -> "DTO[T]":
        """
        Given an instance of the source model, create an instance of the given DTO subclass
        """
        if cls.dto_source_plugin is not None and cls.dto_source_plugin.is_plugin_supported_type(model_instance):
            values = cls.dto_source_plugin.to_dict(model_instance=model_instance)
        elif isinstance(model_instance, BaseModel):
            values = model_instance.dict()
        else:
            values = asdict(model_instance)
        for dto_key, original_key in cls.dto_field_mapping.items():
            value = values.pop(original_key)
            values[dto_key] = value
        return cls(**values)

    def to_model_instance(self) -> T:
        """
        Convert the DTO instance into an instance of the original class from which the DTO was created
        """
        values = self.dict()
        for dto_key, original_key in self.dto_field_mapping.items():
            value = values.pop(dto_key)
            values[original_key] = value
        if self.dto_source_plugin is not None and self.dto_source_plugin.is_plugin_supported_type(
            self.dto_source_model
        ):
            return cast(T, self.dto_source_plugin.from_dict(model_class=self.dto_source_model, **values))
        # we are dealing with a pydantic model or dataclass
        return cast(T, self.dto_source_model(**values))


class DTOFactory:
    def __init__(self, plugins: Optional[List[PluginProtocol]] = None):
        self.plugins = plugins or []

    def __call__(
        self,
        name: str,
        source: Type[T],
        exclude: Optional[List[str]] = None,
        field_mapping: Optional[Dict[str, Union[str, Tuple[str, Any]]]] = None,
        field_definitions: Optional[Dict[str, Tuple[Any, Any]]] = None,
    ) -> Type[DTO[T]]:
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
        field_definitions = field_definitions or {}
        plugin = None
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
                field_type = get_field_type(model_field=model_field)
                if field_name in field_mapping:
                    mapping = field_mapping[field_name]
                    if isinstance(mapping, tuple):
                        field_name, field_type = mapping
                    else:
                        field_name = mapping
                    if model_field.field_info.default not in (Undefined, None, ...):
                        field_definitions[field_name] = (field_type, model_field.default)
                    elif model_field.required or not model_field.allow_none:
                        field_definitions[field_name] = (field_type, ...)
                    else:
                        field_definitions[field_name] = (field_type, None)
                else:
                    # prevents losing Optional
                    field_type = Optional[field_type] if model_field.allow_none else field_type
                    field_definitions[field_name] = (field_type, model_field.field_info)
        dto = cast(Type[DTO[T]], create_model(name, __base__=DTO, **field_definitions))  # type: ignore
        dto.dto_source_model = source
        dto.dto_source_plugin = plugin
        dto.dto_field_mapping = {}
        for key, value in field_mapping.items():
            if not isinstance(value, str):
                value = value[0]
            dto.dto_field_mapping[value] = key
        return dto
