from __future__ import annotations

import re
import traceback
from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache, partial
from pathlib import PurePath
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Union,
    cast,
)
from uuid import UUID

from _decimal import Decimal
from typing_extensions import get_args

from litestar._signature.field import SignatureField
from litestar._signature.models.base import ErrorMessage, SignatureModel
from litestar.connection import ASGIConnection, Request, WebSocket
from litestar.datastructures import ImmutableState, MultiDict, State, UploadFile
from litestar.exceptions import MissingDependencyException
from litestar.params import BodyKwarg, DependencyKwarg, ParameterKwarg
from litestar.types import Empty
from litestar.utils.predicates import is_optional_union, is_union
from litestar.utils.typing import get_origin_or_inner_type, make_non_optional_union, unwrap_union

try:
    import attr
    import attrs
    import cattrs
except ImportError as e:
    raise MissingDependencyException("attrs") from e

try:
    from dateutil.parser import parse
except ImportError as e:
    raise MissingDependencyException("python-dateutil", "attrs") from e

try:
    from pytimeparse.timeparse import timeparse
except ImportError as e:
    raise MissingDependencyException("pytimeparse", "attrs") from e

if TYPE_CHECKING:
    from litestar.utils.signature import ParsedSignature

__all__ = ("AttrsSignatureModel",)
key_re = re.compile("@ (attribute|index) (.*)|'(.*)'")
TRUE_SET = {"1", "true", "on", "t", "y", "yes"}
FALSE_SET = {"0", "false", "off", "f", "n", "no"}

try:
    import pydantic

    def _structure_base_model(value: Any, cls: type[pydantic.BaseModel]) -> pydantic.BaseModel:
        if isinstance(value, pydantic.BaseModel):
            return value
        return cls(**value)

    pydantic_hooks: list[tuple[type[Any], Callable[[Any, type[Any]], Any]]] = [
        (pydantic.BaseModel, _structure_base_model),
    ]
except ImportError:
    pydantic_hooks = []


StructureException = Union[
    cattrs.ClassValidationError, cattrs.IterableValidationError, ValueError, TypeError, AttributeError
]


def _pass_through_structure_hook(value: Any, _: type[Any]) -> Any:
    return value


def _pass_through_unstructure_hook(value: Any) -> Any:
    return value


def _structure_bool(value: Any, _: type[bool]) -> bool:
    if isinstance(value, bytes):
        value = value.decode("utf-8").lower()

    if isinstance(value, str):
        value = value.lower()

    if value == 0 or value in FALSE_SET:
        return False

    if value == 1 or value in TRUE_SET:
        return True

    raise ValueError(f"Cannot convert {value} to bool")


def _structure_datetime(value: Any, cls: type[datetime]) -> datetime:
    if isinstance(value, datetime):
        return value

    try:
        return cls.fromtimestamp(float(value), tz=timezone.utc)
    except (ValueError, TypeError):
        pass

    return parse(value)


def _structure_date(value: Any, cls: type[date]) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, (float, int, Decimal)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).date()

    dt = _structure_datetime(value=value, cls=datetime)
    return cls(year=dt.year, month=dt.month, day=dt.day)


def _structure_time(value: Any, cls: type[time]) -> time:
    if isinstance(value, time):
        return value

    if isinstance(value, str):
        return cls.fromisoformat(value)

    dt = _structure_datetime(value=value, cls=datetime)
    return cls(hour=dt.hour, minute=dt.minute, second=dt.second, microsecond=dt.microsecond, tzinfo=dt.tzinfo)


def _structure_timedelta(value: Any, cls: type[timedelta]) -> timedelta:
    if isinstance(value, timedelta):
        return value
    if isinstance(value, (float, int, Decimal)):
        return cls(seconds=int(value))
    return cls(seconds=timeparse(value))  # pyright: ignore


def _structure_decimal(value: Any, cls: type[Decimal]) -> Decimal:
    return cls(str(value))


def _structure_path(value: Any, cls: type[PurePath]) -> PurePath:
    return cls(str(value))


def _structure_uuid(value: Any, cls: type[UUID]) -> UUID:
    return value if isinstance(value, UUID) else cls(str(value))


def _structure_multidict(value: Any, cls: type[MultiDict]) -> MultiDict:
    return cls(value)


def _structure_str(value: Any, cls: type[str]) -> str:
    # see: https://github.com/python-attrs/cattrs/issues/26#issuecomment-358594015
    if value is None:
        raise ValueError
    return cls(value)


hooks: list[tuple[type[Any], Callable[[Any, type[Any]], Any]]] = [
    (ASGIConnection, _pass_through_structure_hook),
    (Decimal, _structure_decimal),
    (ImmutableState, _pass_through_structure_hook),
    (MultiDict, _structure_multidict),
    (PurePath, _structure_path),
    (Request, _pass_through_structure_hook),
    (State, _pass_through_structure_hook),
    (UUID, _structure_uuid),
    (UploadFile, _pass_through_structure_hook),
    (WebSocket, _pass_through_structure_hook),
    (bool, _structure_bool),
    (date, _structure_date),
    (datetime, _structure_datetime),
    (str, _structure_str),
    (time, _structure_time),
    (timedelta, _structure_timedelta),
    *pydantic_hooks,
]


def _create_default_structuring_hooks(
    converter: cattrs.Converter,
) -> tuple[Callable, Callable]:
    """Create scoped default hooks for a given converter.

    Notes:
        - We are forced to use this pattern because some types cannot be handled by cattrs out of the box. For example,
            union types, optionals, complex union types etc.
        - See: https://github.com/python-attrs/cattrs/issues/311
    Args:
        converter: A converter instance

    Returns:
        A tuple of hook handlers
    """

    @lru_cache(1024)
    def _default_structuring_hook(value: Any, annotation: Any) -> Any:
        for arg in unwrap_union(annotation) or get_args(annotation):
            try:
                return converter.structure(arg, value)
            except ValueError:  # pragma: no cover
                continue
        return value

    return (
        _pass_through_unstructure_hook,
        _default_structuring_hook,
    )


class Converter(cattrs.Converter):
    def __init__(self) -> None:
        super().__init__()

        # this is a hack to create a catch-all hook, see: https://github.com/python-attrs/cattrs/issues/311
        self._structure_func._function_dispatch._handler_pairs[-1] = (
            *_create_default_structuring_hooks(self),
            False,
        )

        # ensure attrs instances are not unstructured into dict
        self.register_unstructure_hook_factory(
            # the first parameter is a predicate that tests the value. In this case we are testing for an attrs
            # decorated class that does not have the AttrsSignatureModel anywhere in its mro chain.
            lambda x: attrs.has(x) and AttrsSignatureModel not in list(x.__mro__),
            # the "unstructuring" hook we are registering is a lambda that receives the class constructor and returns
            # another lambda that will take a value and receive it unmodified.
            # this is a hack to ensure that no attrs constructors are called during unstructuring.
            lambda x: lambda x: x,
        )

        for cls, structure_hook in hooks:
            self.register_structure_hook(cls, structure_hook)
            self.register_unstructure_hook(cls, _pass_through_unstructure_hook)


_converter: Converter = Converter()


def _create_validators(
    annotation: Any, kwargs_model: BodyKwarg | ParameterKwarg
) -> list[Callable[[Any, attrs.Attribute[Any], Any], Any]] | Callable[[Any, attrs.Attribute[Any], Any], Any]:
    validators: list[Callable[[Any, attrs.Attribute[Any], Any], Any]] = []

    for value, validator in [
        (kwargs_model.gt, attrs.validators.gt),
        (kwargs_model.ge, attrs.validators.ge),
        (kwargs_model.lt, attrs.validators.lt),
        (kwargs_model.le, attrs.validators.le),
        (kwargs_model.min_length, attrs.validators.min_len),
        (kwargs_model.max_length, attrs.validators.max_len),
        (kwargs_model.min_items, attrs.validators.min_len),
        (kwargs_model.max_items, attrs.validators.max_len),
        (kwargs_model.pattern, partial(attrs.validators.matches_re, flags=0)),
    ]:
        if value is not None:
            validators.append(validator(value))  # type: ignore

    if is_optional_union(annotation):
        annotation = make_non_optional_union(annotation)
        instance_of_validator = attrs.validators.instance_of(
            unwrap_union(annotation) if is_union(annotation) else (get_origin_or_inner_type(annotation) or annotation)
        )
        return attrs.validators.optional([instance_of_validator, *validators])

    instance_of_validator = attrs.validators.instance_of(get_origin_or_inner_type(annotation) or annotation)
    return [instance_of_validator, *validators]


@attr.define
class AttrsSignatureModel(SignatureModel):
    """Model that represents a function signature that uses a pydantic specific type or types."""

    @classmethod
    def parse_values_from_connection_kwargs(cls, connection: ASGIConnection, **kwargs: Any) -> dict[str, Any]:
        try:
            signature = _converter.structure(obj=kwargs, cl=cls)
        except (cattrs.ClassValidationError, ValueError, TypeError, AttributeError) as e:
            raise cls._create_exception(messages=cls._extract_exceptions(e, connection), connection=connection) from e

        return cast("dict[str, Any]", _converter.unstructure(obj=signature))

    def to_dict(self) -> dict[str, Any]:
        return attrs.asdict(self)

    @classmethod
    def _extract_exceptions(cls, e: StructureException, connection: ASGIConnection) -> list[ErrorMessage]:
        """Extracts and normalizes cattrs exceptions.

        Args:
            e: An ExceptionGroup - which is a py3.11 feature. We use hasattr instead of instance checks to avoid installing this.
            connection: The connection instance.

        Returns:
            A list of normalized exception messages.
        """

        error_messages: list[ErrorMessage] = []

        if isinstance(e, cattrs.ClassValidationError):
            for exc in cast("list[StructureException]", e.exceptions):
                if messages := cls._get_messages_from_traceback(exc, connection):
                    error_messages.extend(messages)

        return error_messages

    @classmethod
    def _get_messages_from_traceback(cls, exc: StructureException, connection: ASGIConnection) -> list[ErrorMessage]:
        """Gets a message from an attrs validation error.

        The key will be a dot-separated string of the attribute path that failed
        validation. The message will be the error message from the exception (or the
        last exception in the exception group, when applicable).

        Args:
            exc: The exception to get the message from
            connection: The connection instance

        Returns:
            An error message
        """

        error_data = cls._get_data_from_exception(exc=exc)
        return cls._get_error_messages(error_data=error_data, connection=connection)

    @classmethod
    def _get_data_from_exception(
        cls, exc: StructureException, prefix: str = "", error_data: dict | None = None
    ) -> dict[str, str]:
        """Gets the keys from an attrs validation error.

        Handles nested structures (e.g. a model attribute references another
        model) by going through all exceptions in the exception group
        """

        error_data = error_data or {}

        if isinstance(exc, (cattrs.ClassValidationError, cattrs.IterableValidationError)):
            formatted_exception = traceback.format_exception_only(type(exc), value=exc)
            key = cls._get_key_from_formatted_exception(formatted_exception)

            new_prefix = f"{prefix}.{key}" if prefix else key

            for sub_exc in cast("list[StructureException]", exc.exceptions):
                error_data = cls._get_data_from_exception(sub_exc, new_prefix, error_data)
        # when using attrs as the preferred backend validation but
        # pydantic as the model, you can still get pydantic
        # validation errors.
        elif isinstance(exc, pydantic.ValidationError):
            formatted_exception = traceback.format_exception_only(type(exc), value=exc)
            key = cls._get_key_from_formatted_exception(formatted_exception)

            for error in exc.errors():
                error_key = ".".join([key, *[str(loc) for loc in error["loc"]]])
                error_data[error_key] = error["msg"]
        else:
            formatted_exception = traceback.format_exception(type(exc), value=exc, tb=exc.__traceback__)
            key = cls._get_key_from_formatted_exception(formatted_exception)
            key = f"{prefix}.{key}" if prefix else key

            error_data[key] = str(exc)

        return error_data

    @classmethod
    def _get_key_from_formatted_exception(cls, formatted_exception: list[str]) -> str:
        """Gets the key from a formatted exception."""
        return next(
            (key for line in formatted_exception if (match := key_re.findall(line)) and (key := match[0][1].strip())),
            "",
        )

    @classmethod
    def _get_error_messages(cls, error_data: dict[str, str], connection: ASGIConnection) -> list[ErrorMessage]:
        """Build an error message.

        Args:
            error_data: A mapping of error location (dot-notated) to their error.
            connection: An ASGI connection instance.

        Returns:
            An ErrorMessage
        """

        messages: list[ErrorMessage] = []

        for key, error in error_data.items():
            keys = key.split(".")
            message = super()._build_error_message(keys=keys, exc_msg=error, connection=connection)
            messages.append(message)

        return messages

    @classmethod
    def populate_signature_fields(cls) -> None:
        cls.fields = {
            k: SignatureField.create(
                field_type=attribute.type,
                name=k,
                default_value=attribute.default if attribute.default is not attr.NOTHING else Empty,
                kwarg_model=attribute.metadata.get("kwargs_model", None) if attribute.metadata else None,
                extra=attribute.metadata or None,
            )
            for k, attribute in attrs.fields_dict(cls).items()
        }

    @classmethod
    def create(
        cls,
        fn_name: str,
        fn_module: str | None,
        parsed_signature: ParsedSignature,
        dependency_names: set[str],
        type_overrides: dict[str, Any],
    ) -> type[SignatureModel]:
        attributes: dict[str, Any] = {}

        for parameter in parsed_signature.parameters.values():
            annotation = type_overrides.get(parameter.name, parameter.parsed_type.annotation)

            if kwargs_container := parameter.kwarg_container:
                if isinstance(kwargs_container, DependencyKwarg):
                    attribute = attr.attrib(
                        type=annotation if not kwargs_container.skip_validation else Any,
                        default=kwargs_container.default if kwargs_container.default is not Empty else None,
                        metadata={
                            "kwargs_model": kwargs_container,
                            "parsed_parameter": parameter,
                        },
                    )
                else:
                    attribute = attr.attrib(
                        type=annotation,
                        metadata={
                            **asdict(kwargs_container),
                            "kwargs_model": kwargs_container,
                            "parsed_parameter": parameter,
                        },
                        default=kwargs_container.default if kwargs_container.default is not Empty else attr.NOTHING,
                        validator=_create_validators(annotation=annotation, kwargs_model=kwargs_container),
                    )
            elif parameter.has_default:
                attribute = attr.attrib(type=annotation, default=parameter.default)
            else:
                attribute = attr.attrib(
                    type=annotation, default=None if parameter.parsed_type.is_optional else attr.NOTHING
                )

            attributes[parameter.name] = attribute

        model: type[AttrsSignatureModel] = attrs.make_class(
            f"{fn_name}_signature_model",
            attrs=attributes,
            bases=(AttrsSignatureModel,),
            slots=True,
            kw_only=True,
        )
        model.return_annotation = parsed_signature.return_type.annotation  # pyright: ignore
        model.dependency_name_set = dependency_names  # pyright: ignore
        model.populate_signature_fields()  # pyright: ignore
        return model
