from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Optional, Union

from msgspec import NODEFAULT, Meta, Struct, ValidationError, convert, defstruct
from msgspec.structs import asdict
from pydantic import ValidationError as PydanticValidationError
from typing_extensions import Annotated

from litestar.params import DependencyKwarg, KwargDefinition
from litestar.serialization import dec_hook
from litestar.utils import make_non_optional_union
from litestar.utils.dataclass import simple_asdict
from litestar.utils.typing import unwrap_union

from .base import SignatureModel

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
    from litestar.utils.signature import ParsedSignature

    from .base import ErrorMessage

__all__ = ("MsgspecSignatureModel",)

MSGSPEC_CONSTRAINT_FIELDS = (
    "gt",
    "ge",
    "lt",
    "le",
    "multiple_of",
    "pattern",
    "min_length",
    "max_length",
)

ERR_RE = re.compile(r"`\$\.(.+)`$")


class MsgspecSignatureModel(SignatureModel, Struct):
    """Model that represents a function signature that uses a msgspec specific type or types."""

    @classmethod
    def parse_values_from_connection_kwargs(cls, connection: ASGIConnection, **kwargs: Any) -> dict[str, Any]:
        """Extract values from the connection instance and return a dict of parsed values.

        Args:
            connection: The ASGI connection instance.
            **kwargs: A dictionary of kwargs.

        Raises:
            ValidationException: If validation failed.
            InternalServerException: If another exception has been raised.

        Returns:
            A dictionary of parsed values
        """
        messages: list[ErrorMessage] = []
        try:
            return convert(kwargs, cls, strict=False, dec_hook=dec_hook).to_dict()
        except PydanticValidationError as e:
            for exc in e.errors():
                keys = [str(loc) for loc in exc["loc"]]
                message = super()._build_error_message(keys=keys, exc_msg=exc["msg"], connection=connection)
                messages.append(message)
            raise cls._create_exception(messages=messages, connection=connection) from e
        except ValidationError as e:
            match = ERR_RE.search(str(e))
            keys = [str(match.group(1)) if match else "n/a"]
            message = super()._build_error_message(keys=keys, exc_msg=str(e), connection=connection)
            messages.append(message)
            raise cls._create_exception(messages=messages, connection=connection) from e

    def to_dict(self) -> dict[str, Any]:
        """Normalize access to the signature model's dictionary method, because different backends use different methods
        for this.

        Returns: A dictionary of string keyed values.
        """
        return asdict(self)

    @classmethod
    def create(
        cls,
        fn_name: str,
        fn_module: str | None,
        parsed_signature: ParsedSignature,
        dependency_names: set[str],
        type_overrides: dict[str, Any],
    ) -> type[SignatureModel]:
        struct_fields: list[tuple[str, Any, Any]] = []

        for field_definition in parsed_signature.parameters.values():
            annotation = type_overrides.get(field_definition.name, field_definition.annotation)

            meta_kwargs: dict[str, Any] = {}

            if isinstance(field_definition.kwarg_definition, KwargDefinition):
                meta_kwargs.update(
                    {k: v for k in MSGSPEC_CONSTRAINT_FIELDS if (v := getattr(field_definition.kwarg_definition, k))}
                )
                meta_kwargs["extra"] = simple_asdict(field_definition.kwarg_definition)
            elif isinstance(field_definition.kwarg_definition, DependencyKwarg):
                annotation = annotation if not field_definition.kwarg_definition.skip_validation else Any

            default = field_definition.default if field_definition.has_default else NODEFAULT

            meta = Meta(**meta_kwargs)
            if field_definition.is_optional:
                annotated_type = Optional[Annotated[make_non_optional_union(field_definition.annotation), meta]]  # type: ignore
            elif field_definition.is_union and meta_kwargs.keys() & MSGSPEC_CONSTRAINT_FIELDS:
                # unwrap inner types of a union and apply constraints to each individual type
                # see https://github.com/jcrist/msgspec/issues/447
                annotated_type = Union[
                    tuple(
                        Annotated[inner_type, meta] for inner_type in unwrap_union(field_definition.annotation)
                    )  # pyright: ignore
                ]
            else:
                annotated_type = Annotated[annotation, meta]

            struct_fields.append((field_definition.name, annotated_type, default))

        return defstruct(  # type:ignore[return-value]
            f"{fn_name}_signature_model",
            struct_fields,
            bases=(MsgspecSignatureModel,),
            module=fn_module,
            namespace={
                "return_annotation": parsed_signature.return_type.annotation,
                "dependency_name_set": dependency_names,
                "fields": parsed_signature.parameters,
            },
            kw_only=True,
        )
