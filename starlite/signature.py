from dataclasses import dataclass
from inspect import Parameter, Signature
from typing import (
    AbstractSet,
    Any,
    ClassVar,
    Dict,
    Generator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

from pydantic import BaseConfig, BaseModel, ValidationError, create_model
from pydantic.fields import FieldInfo, Undefined
from pydantic.typing import AnyCallable
from pydantic_factories import ModelFactory
from typing_extensions import get_args

from starlite.connection import Request, WebSocket
from starlite.exceptions import ImproperlyConfiguredException, ValidationException
from starlite.plugins.base import PluginMapping, PluginProtocol, get_plugin_for_value
from starlite.utils.dependency import is_dependency_field
from starlite.utils.typing import detect_optional_union


class SignatureModel(BaseModel):
    class Config(BaseConfig):
        arbitrary_types_allowed = True

    field_plugin_mappings: ClassVar[Dict[str, PluginMapping]]
    return_annotation: ClassVar[Any]
    has_kwargs: ClassVar[bool]
    factory: ClassVar["SignatureModelFactory"]

    @classmethod
    def parse_values_from_connection_kwargs(
        cls, connection: Union[Request, WebSocket], **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Given a dictionary of values extracted from the connection, create an instance of the given
        SignatureModel subclass and return the parsed values.

        This is not equivalent to calling the '.dict'  method of the pydantic model,
        because it doesn't convert nested values into dictionary, just extracts the data from the signature model
        """
        try:
            output: Dict[str, Any] = {}
            modelled_signature = cls(**kwargs)
            for key in cls.__fields__:
                value = modelled_signature.__getattribute__(key)  # pylint: disable=unnecessary-dunder-call
                plugin_mapping: Optional[PluginMapping] = cls.field_plugin_mappings.get(key)
                if plugin_mapping:
                    if isinstance(value, (list, tuple)):
                        output[key] = [
                            plugin_mapping.plugin.from_pydantic_model_instance(
                                plugin_mapping.model_class, pydantic_model_instance=v
                            )
                            for v in value
                        ]
                    else:
                        output[key] = plugin_mapping.plugin.from_pydantic_model_instance(
                            plugin_mapping.model_class, pydantic_model_instance=value
                        )
                else:
                    output[key] = value
            return output
        except ValidationError as e:
            raise ValidationException(
                detail=f"Validation failed for {connection.method if isinstance(connection, Request) else 'websocket'} {connection.url}",
                extra=e.errors(),
            ) from e


@dataclass
class SignatureParameter:
    """
    Represents the parameters of a callable for purpose of signature model generation.
    """

    name: str
    annotation: Any
    optional: bool
    default: Any

    @property
    def default_defined(self) -> bool:
        """
        `True` if `self.default` is not one of the undefined sentinel types.

        Returns
        -------
        bool
        """
        return self.default not in {Signature.empty, Undefined}

    @classmethod
    def new(cls, fn_name: str, parameter_name: str, parameter: Parameter) -> "SignatureParameter":
        """
        Create a new `SignatureParameter`

        Parameters
        ----------
        fn_name : str
            Name of function.
        parameter_name : str
            Name of parameter.
        parameter : inspect.Parameter

        Returns
        -------
        SignatureParameter
        """
        if parameter.annotation is Signature.empty:
            raise ImproperlyConfiguredException(
                f"Kwarg {parameter_name} of {fn_name} does not have a type annotation. If it "
                f"should receive any value, use the 'Any' type."
            )
        return cls(
            name=parameter_name,
            annotation=parameter.annotation,
            optional=detect_optional_union(parameter.annotation),
            default=parameter.default,
        )


class SignatureModelFactory:
    """
    Utility class for constructing the signature model and grouping associated state.

    Instance available at `SignatureModel.factory`.

    Parameters
    ----------
    fn : AnyCallable
    plugins : list[PluginProtocol]
    provided_dependency_names : AbstractSet[str]

    The following attributes are populated after the `model()` method has been called to generate
    the `SignatureModel` subclass.

    Attributes
    ----------
    field_plugin_mappings : dict[str, PluginMapping]
        Maps parameter name, to `PluginMapping` where a plugin has been applied.
    field_definitions : dict[str, Tuple[Any, Any]
        Maps parameter name to the `(<type>, <default>)` tuple passed to `pydantic.create_model()`.
    defaults : dict[str, Any]
        Maps parameter name to default value, if one defined.
    dependency_name_set : set[str]
        The names of all known dependency parameters.
    """

    # names of fn params not included in signature model.
    SKIP_NAMES = {"self", "cls"}
    # names of params always typed `Any`.
    SKIP_VALIDATION_NAMES = {"request", "socket"}

    def __init__(
        self, fn: AnyCallable, plugins: List[PluginProtocol], provided_dependency_names: AbstractSet[str]
    ) -> None:
        if fn is None:
            raise ImproperlyConfiguredException("Parameter `fn` to `SignatureModelFactory` cannot be `None`.")
        self.signature = Signature.from_callable(fn)
        self.fn_name = fn.__name__ if hasattr(fn, "__name__") else "anonymous"
        self.plugins = plugins
        self.provided_dependency_names = provided_dependency_names
        self.field_plugin_mappings: Dict[str, PluginMapping] = {}
        self.field_definitions: Dict[str, Any] = {}
        self.defaults: Dict[str, Any] = {}
        # this ends up being the total set of all identified deps. Might be provided, or not but
        # with default value.
        self.dependency_name_set: Set[str] = set(provided_dependency_names)

    def check_for_unprovided_dependency(self, parameter: SignatureParameter) -> None:
        """
        Where a dependency has been explicitly marked using the `Dependency` function, it is a
        configuration error if that dependency has been defined without a default value, and it
        hasn't been provided to the handler.

        Parameters
        ----------
        parameter : SignatureParameter

        Raises
        ------
        `ImproperlyConfiguredException`
        """
        if parameter.optional:
            return
        if not is_dependency_field(parameter.default):
            return
        field_info: FieldInfo = parameter.default
        if field_info.default is not Undefined:
            return
        if parameter.name not in self.provided_dependency_names:
            raise ImproperlyConfiguredException(
                f"Explicit dependency '{parameter.name}' for '{self.fn_name}' has no default value, "
                f"or provided dependency."
            )

    def collect_dependency_names(self, parameter: SignatureParameter) -> None:
        """
        Add parameter name of dependencies declared using `Dependency()` function to the set of all
        dependency names.

        Parameters
        ----------
        parameter : SignatureParameter
        """
        if is_dependency_field(parameter.default):
            self.dependency_name_set.add(parameter.name)

    def record_default(self, parameter: SignatureParameter) -> None:
        """
        If `parameter` has defined default, map it to the parameter name in `self.defaults`.

        Parameters
        ----------
        parameter : SignatureParameter
        """
        if parameter.default_defined:
            self.defaults[parameter.name] = parameter.default

    def get_type_annotation_from_plugin(self, parameter: SignatureParameter, plugin: PluginProtocol) -> Any:
        """
        Use plugin declared for parameter annotation type to generate a pydantic model.

        Parameters
        ----------
        parameter : SignatureParameter
        plugin : PluginProtocol

        Returns
        -------
        Any
        """
        type_args = get_args(parameter.annotation)
        type_value = type_args[0] if type_args else parameter.annotation
        self.field_plugin_mappings[parameter.name] = PluginMapping(plugin=plugin, model_class=type_value)
        pydantic_model = plugin.to_pydantic_model_class(model_class=type_value)
        if type_args:
            return List[pydantic_model]  # type:ignore[valid-type]
        return pydantic_model

    @staticmethod
    def field_definition_from_parameter(parameter: SignatureParameter) -> Tuple[Any, Any]:
        """
        Construct an `(<annotation>, <default>)` tuple, appropriate for `pydantic.create_model()`.

        Parameters
        ----------
        parameter : SignatureParameter

        Returns
        -------
        tuple[Any, Any]
        """
        if parameter.default_defined:
            field_definition = (parameter.annotation, parameter.default)
        elif not parameter.optional:
            field_definition = (parameter.annotation, ...)
        else:
            field_definition = (parameter.annotation, None)
        return field_definition

    @property
    def signature_parameters(self) -> Generator[SignatureParameter, None, None]:
        """
        Iterable of `SignatureModel` instances, that represent the parameters of the function
        signature that should be included in the `SignatureModel` type.

        Returns
        -------
        Generator[SignatureParameter, None, None]
        """
        for name, parameter in self.signature.parameters.items():
            if name in self.SKIP_NAMES:
                continue
            yield SignatureParameter.new(self.fn_name, name, parameter)

    def model(self) -> Type[SignatureModel]:
        """
        Construct a `SignatureModel` type that represents the signature of `self.fn`

        Returns
        -------
        type[SignatureModel]
        """
        try:
            for parameter in self.signature_parameters:
                self.check_for_unprovided_dependency(parameter)
                self.collect_dependency_names(parameter)
                self.record_default(parameter)
                if parameter.name in self.SKIP_VALIDATION_NAMES:
                    # pydantic has issues with none-pydantic classes that receive generics
                    self.field_definitions[parameter.name] = (Any, ...)
                    continue
                if ModelFactory.is_constrained_field(parameter.default):
                    self.field_definitions[parameter.name] = (parameter.default, ...)
                    continue
                plugin = get_plugin_for_value(value=parameter.annotation, plugins=self.plugins)
                if plugin:
                    parameter.annotation = self.get_type_annotation_from_plugin(parameter, plugin)
                self.field_definitions[parameter.name] = self.field_definition_from_parameter(parameter)
            model: Type[SignatureModel] = create_model(
                self.fn_name + "_signature_model", __base__=SignatureModel, **self.field_definitions
            )
            model.return_annotation = self.signature.return_annotation
            model.field_plugin_mappings = self.field_plugin_mappings
            model.has_kwargs = bool(model.__fields__)
            model.factory = self
            return model
        except TypeError as e:
            raise ImproperlyConfiguredException(repr(e)) from e


def get_signature_model(value: Any) -> Type[SignatureModel]:
    """
    Helper function to retrieve and validate the signature model from a provider or handler
    """
    try:
        return cast(Type[SignatureModel], getattr(value, "signature_model"))
    except AttributeError as e:  # pragma: no cover
        raise ImproperlyConfiguredException(f"The 'signature_model' attribute for {value} is not set") from e
