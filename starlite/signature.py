from inspect import Parameter, Signature
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Generator,
    List,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

from pydantic import BaseConfig, BaseModel, ValidationError, create_model
from pydantic.fields import FieldInfo, Undefined
from pydantic_factories import ModelFactory
from typing_extensions import get_args

from starlite.connection import Request, WebSocket
from starlite.enums import ScopeType
from starlite.exceptions import (
    ImproperlyConfiguredException,
    InternalServerException,
    ValidationException,
)
from starlite.plugins.base import PluginMapping, PluginProtocol, get_plugin_for_value
from starlite.utils import (
    is_dependency_field,
    is_optional_union,
    should_skip_dependency_validation,
)

if TYPE_CHECKING:
    from pydantic.error_wrappers import ErrorDict
    from starlette.datastructures import URL

    from starlite.types import AnyCallable


UNDEFINED_SENTINELS = {Undefined, Signature.empty}
SKIP_NAMES = {"self", "cls"}
SKIP_VALIDATION_NAMES = {"request", "socket", "state", "scope"}


class SignatureModel(BaseModel):
    class Config(BaseConfig):
        arbitrary_types_allowed = True

    dependency_name_set: ClassVar[Set[str]]
    field_plugin_mappings: ClassVar[Dict[str, PluginMapping]]
    return_annotation: ClassVar[Any]

    @classmethod
    def parse_values_from_connection_kwargs(
        cls, connection: Union[Request, WebSocket], **kwargs: Any
    ) -> Dict[str, Any]:
        """Given a dictionary of values extracted from the connection, create
        an instance of the given SignatureModel subclass and return the parsed
        values.

        This is not equivalent to calling the '.dict'  method of the
        pydantic model, because it doesn't convert nested values into
        dictionary, just extracts the data from the signature model
        """
        try:
            signature = cls(**kwargs)
            return {key: signature.resolve_field_value(key) for key in cls.__fields__}
        except ValidationError as exc:
            raise cls.construct_exception(connection, exc) from exc

    def resolve_field_value(self, key: str) -> Any:
        """Given a field key, return value using plugin mapping, if
        available."""
        value = self.__getattribute__(key)  # pylint: disable=unnecessary-dunder-call
        mapping = self.field_plugin_mappings.get(key)
        return mapping.get_model_instance_for_value(value) if mapping else value

    @classmethod
    def construct_exception(
        cls, connection: Union[Request, WebSocket], exc: ValidationError
    ) -> Union[InternalServerException, ValidationException]:
        """Distinguish between validation errors that arise from parameters and
        dependencies.

        If both parameter and dependency values are invalid, we raise the client error first.

        Parameters
        ----------
        connection : Request | WebSocket
        exc : ValidationError

        Returns
        -------
        ValidationException | InternalServerException
        """
        server_errors: List["ErrorDict"] = []
        client_errors: List["ErrorDict"] = []

        for error in exc.errors():
            if cls.is_server_error(error):
                server_errors.append(error)
            else:
                client_errors.append(error)

        method, url = cls.get_connection_method_and_url(connection)

        if client_errors:
            return ValidationException(detail=f"Validation failed for {method} {url}", extra=client_errors)

        return InternalServerException(detail=f"A dependency failed validation for {method} {url}", extra=server_errors)

    @classmethod
    def is_server_error(cls, error: "ErrorDict") -> bool:
        """Check whether given validation error is a server error."""
        return error["loc"][-1] in cls.dependency_name_set

    @staticmethod
    def get_connection_method_and_url(connection: Union[Request, WebSocket]) -> Tuple[str, "URL"]:
        """Extract method and URL from Request or WebSocket."""
        method = ScopeType.WEBSOCKET if isinstance(connection, WebSocket) else connection.method
        return method, connection.url


class SignatureParameter:
    """Represents the parameters of a callable for purpose of signature model
    generation.

    Parameters
    ----------
    fn_name : str
        Name of function.
    parameter_name : str
        Name of parameter.
    parameter : inspect.Parameter
    """

    __slots__ = (
        "annotation",
        "default",
        "name",
        "optional",
    )

    annotation: Any
    default: Any
    name: str
    optional: bool

    def __init__(self, fn_name: str, parameter_name: str, parameter: Parameter) -> None:
        if parameter.annotation is Signature.empty:
            raise ImproperlyConfiguredException(
                f"Kwarg {parameter_name} of {fn_name} does not have a type annotation. If it "
                f"should receive any value, use the 'Any' type."
            )
        self.annotation = parameter.annotation
        self.default = parameter.default
        self.name = parameter_name
        self.optional = is_optional_union(parameter.annotation)

    @property
    def default_defined(self) -> bool:
        """`True` if `self.default` is not one of the undefined sentinel types.

        Returns
        -------
        bool
        """
        return self.default not in UNDEFINED_SENTINELS


class SignatureModelFactory:
    """Utility class for constructing the signature model and grouping
    associated state.

    Instance available at `SignatureModel.factory`.

    Parameters
    ----------
    fn : AnyCallable
    plugins : list[PluginProtocol]
    dependency_names : Set[str]

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

    __slots__ = (
        "defaults",
        "dependency_name_set",
        "field_definitions",
        "field_plugin_mappings",
        "fn_name",
        "plugins",
        "signature",
    )

    def __init__(self, fn: "AnyCallable", plugins: List["PluginProtocol"], dependency_names: Set[str]) -> None:
        if fn is None:
            raise ImproperlyConfiguredException("Parameter `fn` to `SignatureModelFactory` cannot be `None`.")
        self.signature = Signature.from_callable(fn)
        self.fn_name = fn.__name__ if hasattr(fn, "__name__") else "anonymous"
        self.plugins = plugins
        self.field_plugin_mappings: Dict[str, PluginMapping] = {}
        self.field_definitions: Dict[str, Any] = {}
        self.defaults: Dict[str, Any] = {}
        self.dependency_name_set = dependency_names

    def check_for_unprovided_dependency(self, parameter: SignatureParameter) -> None:
        """Where a dependency has been explicitly marked using the `Dependency`
        function, it is a configuration error if that dependency has been
        defined without a default value, and it hasn't been provided to the
        handler.

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
        if parameter.name not in self.dependency_name_set:
            raise ImproperlyConfiguredException(
                f"Explicit dependency '{parameter.name}' for '{self.fn_name}' has no default value, "
                f"or provided dependency."
            )

    def collect_dependency_names(self, parameter: SignatureParameter) -> None:
        """Add parameter name of dependencies declared using `Dependency()`
        function to the set of all dependency names.

        Parameters
        ----------
        parameter : SignatureParameter
        """
        if is_dependency_field(parameter.default):
            self.dependency_name_set.add(parameter.name)

    def set_field_default(self, parameter: SignatureParameter) -> None:
        """If `parameter` has defined default, map it to the parameter name in
        `self.defaults`.

        Parameters
        ----------
        parameter : SignatureParameter
        """
        if parameter.default_defined:
            self.defaults[parameter.name] = parameter.default

    def get_type_annotation_from_plugin(self, parameter: SignatureParameter, plugin: PluginProtocol) -> Any:
        """Use plugin declared for parameter annotation type to generate a
        pydantic model.

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
        pydantic_model = plugin.to_pydantic_model_class(model_class=type_value, parameter_name=parameter.name)
        if type_args:
            return List[pydantic_model]  # type:ignore[valid-type]
        return pydantic_model

    @staticmethod
    def create_field_definition_from_parameter(parameter: SignatureParameter) -> Tuple[Any, Any]:
        """Construct an `(<annotation>, <default>)` tuple, appropriate for
        `pydantic.create_model()`.

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
        """Iterable of `SignatureModel` instances, that represent the
        parameters of the function signature that should be included in the
        `SignatureModel` type.

        Returns
        -------
        Generator[SignatureParameter, None, None]
        """
        for name, parameter in filter(lambda x: x[0] not in SKIP_NAMES, self.signature.parameters.items()):
            yield SignatureParameter(self.fn_name, name, parameter)

    def should_skip_parameter_validation(self, parameter: SignatureParameter) -> bool:
        """Identify dependencies for which provided values should not be
        validated.

        Args:
            parameter (SignatureParameter): A parameter to be added to the signature model.

        Returns:
            A boolean indicating whether injected values for this parameter should not be validated.
        """
        return parameter.name in SKIP_VALIDATION_NAMES or should_skip_dependency_validation(parameter.default)

    def create_signature_model(self) -> Type[SignatureModel]:
        """Constructs a `SignatureModel` type that represents the signature of
        `self.fn`

        Returns
        -------
        type[SignatureModel]
        """
        try:
            for parameter in self.signature_parameters:
                self.check_for_unprovided_dependency(parameter)
                self.collect_dependency_names(parameter)
                self.set_field_default(parameter)
                if self.should_skip_parameter_validation(parameter):
                    # pydantic has issues with none-pydantic classes that receive generics
                    self.field_definitions[parameter.name] = (Any, ...)
                    continue
                if ModelFactory.is_constrained_field(parameter.default):
                    self.field_definitions[parameter.name] = (parameter.default, ...)
                    continue
                plugin = get_plugin_for_value(value=parameter.annotation, plugins=self.plugins)
                if plugin:
                    parameter.annotation = self.get_type_annotation_from_plugin(parameter, plugin)
                self.field_definitions[parameter.name] = self.create_field_definition_from_parameter(parameter)
            model: Type[SignatureModel] = create_model(
                self.fn_name + "_signature_model", __base__=SignatureModel, **self.field_definitions
            )
            model.return_annotation = self.signature.return_annotation
            model.field_plugin_mappings = self.field_plugin_mappings
            model.dependency_name_set = self.dependency_name_set
            return model
        except TypeError as e:
            raise ImproperlyConfiguredException(f"Error creating signature model for '{self.fn_name}': '{e}'") from e


def get_signature_model(value: Any) -> Type[SignatureModel]:
    """Helper function to retrieve and validate the signature model from a
    provider or handler."""
    try:
        return cast("Type[SignatureModel]", getattr(value, "signature_model"))
    except AttributeError as e:  # pragma: no cover
        raise ImproperlyConfiguredException(f"The 'signature_model' attribute for {value} is not set") from e
