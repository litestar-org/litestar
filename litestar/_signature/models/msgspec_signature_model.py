from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Optional, Union

from msgspec import NODEFAULT, Meta, Struct, ValidationError, convert, defstruct
from msgspec.structs import asdict
from typing_extensions import Annotated

from litestar._signature.field import SignatureField
from litestar.params import DependencyKwarg
from litestar.serialization import dec_hook
from litestar.types.empty import Empty
from litestar.utils import make_non_optional_union
from litestar.utils.dataclass import simple_asdict
from litestar.utils.typing import unwrap_union

from .base import SignatureModel

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

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
    from litestar.utils.signature import ParsedSignature

__all__ = ("MsgspecSignatureModel",)


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
        try:
            return convert(kwargs, cls, strict=False, dec_hook=dec_hook).to_dict()
        except ValidationError as e:
            message = str(e)
            match = ERR_RE.search(message)
            key = str(match.group(1)) if match else "n/a"
            raise cls._create_exception(messages=[{"key": key, "message": message}], connection=connection) from e

    def to_dict(self) -> dict[str, Any]:
        """Normalize access to the signature model's dictionary method, because different backends use different methods
        for this.

        Returns: A dictionary of string keyed values.
        """
        return asdict(self)

    @classmethod
    def populate_signature_fields(cls) -> None:
        ...

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
        signature_fields: dict[str, SignatureField] = {}

        for parameter in parsed_signature.parameters.values():
            annotation = type_overrides.get(parameter.name, parameter.parsed_type.annotation)

            field_extra: dict[str, Any] = {"parsed_parameter": parameter}
            meta_kwargs: dict[str, Any] = {}

            if kwargs_container := parameter.kwarg_container:
                field_extra["kwargs_model"] = kwargs_container
                if isinstance(kwargs_container, DependencyKwarg):
                    annotation = annotation if not kwargs_container.skip_validation else Any
                    default = kwargs_container.default if kwargs_container.default is not Empty else NODEFAULT
                else:
                    param_dict = simple_asdict(kwargs_container)
                    field_extra |= param_dict
                    meta_kwargs = {k: v for k in MSGSPEC_CONSTRAINT_FIELDS if (v := getattr(kwargs_container, k))}

                    if kwargs_container.min_items:
                        meta_kwargs["min_length"] = kwargs_container.min_items
                    if kwargs_container.max_items:
                        meta_kwargs["max_length"] = kwargs_container.max_items

                    default = NODEFAULT
            else:
                default = parameter.default if parameter.has_default else NODEFAULT

            meta = Meta(extra=field_extra, **meta_kwargs)
            if parameter.parsed_type.is_optional:
                annotated_type = Optional[Annotated[make_non_optional_union(parameter.annotation), meta]]  # type: ignore[valid-type]
            elif parameter.parsed_type.is_union and meta_kwargs.keys() & MSGSPEC_CONSTRAINT_FIELDS:
                # unwrap inner types of a union and apply constraints to each individual type
                # see https://github.com/jcrist/msgspec/issues/447
                annotated_type = Union[
                    tuple(
                        Annotated[inner_type, meta] for inner_type in unwrap_union(parameter.annotation)
                    )  # pyright: ignore
                ]
            else:
                annotated_type = Annotated[annotation, meta]
            struct_fields.append((parameter.name, annotated_type, default))

            signature_fields[parameter.name] = SignatureField.create(
                field_type=annotation,
                name=parameter.name,
                default_value=Empty if default is NODEFAULT else default,
                kwarg_model=kwargs_container,
                extra=field_extra,
            )

        return defstruct(  # type:ignore[return-value]
            f"{fn_name}_signature_model",
            struct_fields,
            bases=(MsgspecSignatureModel,),
            module=fn_module,
            namespace={
                "return_annotation": parsed_signature.return_type.annotation,
                "dependency_name_set": dependency_names,
                "fields": signature_fields,
            },
            kw_only=True,
        )
