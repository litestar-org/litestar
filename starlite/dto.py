from dataclasses import asdict, is_dataclass
from inspect import isawaitable
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from pydantic import BaseConfig, BaseModel, create_model
from pydantic.fields import SHAPE_SINGLETON, ModelField, Undefined
from pydantic.generics import GenericModel
from pydantic_factories import ModelFactory

from starlite.exceptions import ImproperlyConfiguredException
from starlite.plugins import PluginProtocol, get_plugin_for_value
from starlite.utils import convert_dataclass_to_model, is_async_callable

if TYPE_CHECKING:
    from typing import Awaitable


def get_field_type(model_field: ModelField) -> Any:
    """Given a model field instance, return the correct type.

    Args:
        model_field (ModelField): `pydantic.fields.ModelField`

    Returns:
        Type of field.
    """
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
    def _from_value_mapping(cls, mapping: Dict[str, Any]) -> "DTO[T]":
        for dto_key, original_key in cls.dto_field_mapping.items():
            value = mapping.pop(original_key)
            mapping[dto_key] = value
        return cls(**mapping)

    @classmethod
    def from_model_instance(cls, model_instance: T) -> "DTO[T]":
        """Given an instance of the source model, create an instance of the
        given DTO subclass.

        Args:
            model_instance (T): instance of source model.

        Returns:
            Instance of the [`DTO`][starlite.dto.DTO] subclass.
        """
        if cls.dto_source_plugin is not None and cls.dto_source_plugin.is_plugin_supported_type(model_instance):
            result = cls.dto_source_plugin.to_dict(model_instance=model_instance)
            if isawaitable(result):
                raise ImproperlyConfiguredException(
                    f"plugin {type(cls.dto_source_plugin).__name__} to_dict method is async. "
                    f"Use 'DTO.from_model_instance_async instead'",
                )
            values = cast("Dict[str, Any]", result)
        elif isinstance(model_instance, BaseModel):
            values = model_instance.dict()
        else:
            values = asdict(model_instance)
        return cls._from_value_mapping(mapping=values)

    @classmethod
    async def from_model_instance_async(cls, model_instance: T) -> "DTO[T]":
        """Given an instance of the source model, create an instance of the
        given DTO subclass asynchronously.

        Args:
            model_instance (T): instance of source model.

        Returns:
            Instance of the [`DTO`][starlite.dto.DTO] subclass.
        """
        if (
            cls.dto_source_plugin is not None
            and cls.dto_source_plugin.is_plugin_supported_type(model_instance)
            and is_async_callable(cls.dto_source_plugin.to_dict)
        ):
            values = await cast(
                "Awaitable[Dict[str, Any]]", cls.dto_source_plugin.to_dict(model_instance=model_instance)
            )
            return cls._from_value_mapping(mapping=values)
        return cls.from_model_instance(model_instance=model_instance)

    def to_model_instance(self) -> T:
        """Convert the DTO instance into an instance of the original class from
        which the DTO was created.

        Returns:
            Instance of source model type.
        """
        values = self.dict()
        for dto_key, original_key in self.dto_field_mapping.items():
            value = values.pop(dto_key)
            values[original_key] = value
        if self.dto_source_plugin is not None and self.dto_source_plugin.is_plugin_supported_type(
            self.dto_source_model
        ):
            return cast("T", self.dto_source_plugin.from_dict(model_class=self.dto_source_model, **values))
        # we are dealing with a pydantic model or dataclass
        return cast("T", self.dto_source_model(**values))


class DTOFactory:
    def __init__(self, plugins: Optional[List[PluginProtocol]] = None) -> None:
        """Create [`DTO`][starlite.dto.DTO] types from pydantic models,
        dataclasses and other types supported via plugins.

        Args:
            plugins (list[PluginProtocol] | None): Plugins used to support `DTO` construction from arbitrary types.
        """
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

        ```python
        class MyClass(BaseModel):
            first: int
            second: int


        MyClassDTO = DTOFactory()(
            MyClass, exclude=["first"], field_mapping={"second": ("third", float)}
        )
        ```

        `MyClassDTO` is now equal to this:

        ```python
        class MyClassDTO(BaseModel):
            third: float
        ```

        It can be used as a regular pydantic model:

        ```python
        @post(path="/my-path")
        def create_obj(data: MyClassDTO) -> MyClass:
            ...
        ```

        This will affect parsing, validation and how OpenAPI schema is generated exactly like when using a pydantic model.

        Note: Although the value generated is a pydantic factory, because it is being generated programmatically,
        it's currently not possible to extend editor auto-complete for the DTO properties - it will be typed as a
        Pydantic BaseModel, but no attributes will be inferred in the editor.

        Args:
            name (str): This becomes the name of the generated pydantic model.
            source (type[T]): A type that is either a subclass of `BaseModel`, a `dataclass` or any other type with a
                plugin registered.
            exclude (list[str] | None): Names of attributes on `source`. Named Attributes will not have a field
                generated on the resultant pydantic model.
            field_mapping (dict[str, str | tuple[str, Any]] | None): Keys are names of attributes on `source`. Values
                are either a `str` to rename an attribute, or tuple `(str, Any)` to remap both name and type of the
                attribute.
            field_definitions (dict[str, tuple[Any, Any]] | None): Add fields to the model that don't exist on `source`.
                These are passed as kwargs to `pydantic.create_model()`.

        Returns:
            Type[DTO[T]]

        Raises:
            [ImproperlyConfiguredException][starlite.exceptions.ImproperlyConfiguredException]: If `source` is not a
                pydantic model or dataclass, and there is no plugin registered for its type.
        """
        field_definitions = field_definitions or {}
        exclude = exclude or []
        field_mapping = field_mapping or {}
        fields, plugin = self._get_fields_from_source(source)
        field_definitions = self._populate_field_definitions(exclude, field_definitions, field_mapping, fields)
        dto = cast("Type[DTO[T]]", create_model(name, __base__=DTO, **field_definitions))  # type:ignore[call-overload]
        dto.dto_source_model = source
        dto.dto_source_plugin = plugin
        dto.dto_field_mapping = {}
        for key, value in field_mapping.items():
            if not isinstance(value, str):
                value = value[0]
            dto.dto_field_mapping[value] = key
        return dto

    def _get_fields_from_source(
        self, source: Type[T]  # pyright: ignore
    ) -> Tuple[Dict[str, ModelField], Optional[PluginProtocol]]:
        """Converts a `BaseModel` subclass, `dataclass` or any other type that
        has a plugin registered into a mapping of `str` to `ModelField`."""
        plugin: Optional[PluginProtocol] = None
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
        return fields, plugin

    def _populate_field_definitions(
        self,
        exclude: List[str],
        field_definitions: Dict[str, Tuple[Any, Any]],
        field_mapping: Dict[str, Union[str, Tuple[str, Any]]],
        fields: Dict[str, ModelField],
    ) -> Dict[str, Tuple[Any, Any]]:
        """Populates `field_definitions`, ignoring fields in `exclude`, and
        remapping fields in `field_mapping`."""
        for field_name, model_field in fields.items():
            if field_name in exclude:
                continue
            field_type = get_field_type(model_field=model_field)
            self._populate_single_field_definition(
                field_definitions, field_mapping, field_name, field_type, model_field
            )
        return field_definitions

    @classmethod
    def _populate_single_field_definition(
        cls,
        field_definitions: Dict[str, Tuple[Any, Any]],
        field_mapping: Dict[str, Union[str, Tuple[str, Any]]],
        field_name: str,
        field_type: Any,
        model_field: ModelField,
    ) -> None:
        if field_name in field_mapping:
            field_name, field_type = cls._remap_field(field_mapping, field_name, field_type)
            if ModelFactory.is_constrained_field(field_type):
                field_definitions[field_name] = (field_type, ...)
            elif model_field.field_info.default not in (Undefined, None, ...):
                field_definitions[field_name] = (field_type, model_field.default)
            elif model_field.required or not model_field.allow_none:
                field_definitions[field_name] = (field_type, ...)
            else:
                field_definitions[field_name] = (field_type, None)
        else:
            # prevents losing Optional
            field_type = Optional[field_type] if model_field.allow_none else field_type
            if ModelFactory.is_constrained_field(field_type):
                field_definitions[field_name] = (field_type, ...)
            else:
                field_definitions[field_name] = (field_type, model_field.field_info)

    @staticmethod
    def _remap_field(
        field_mapping: Dict[str, Union[str, Tuple[str, Any]]], field_name: str, field_type: Any
    ) -> Tuple[str, Any]:
        """Returns tuple of field name and field type remapped according to
        entry in `field_mapping`."""
        mapping = field_mapping[field_name]
        if isinstance(mapping, tuple):
            field_name, field_type = mapping
        else:
            field_name = mapping
        return field_name, field_type
