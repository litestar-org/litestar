"""DTO backends do the heavy lifting of decoding and validating raw bytes into domain models, and
back again, to bytes.
"""
from __future__ import annotations

import secrets
import textwrap
from contextlib import contextmanager, nullcontext
from dataclasses import replace
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Any,
    Callable,
    ClassVar,
    Collection,
    Container,
    ContextManager,
    Final,
    Generator,
    Mapping,
    Protocol,
    Union,
    cast,
)

from msgspec import UNSET, Struct, UnsetType, convert, defstruct, field
from typing_extensions import get_origin

from litestar.dto._types import (
    CollectionType,
    CompositeType,
    MappingType,
    NestedFieldInfo,
    SimpleType,
    TransferDTOFieldDefinition,
    TransferType,
    TupleType,
    UnionType,
)
from litestar.dto.data_structures import DTOData, DTOFieldDefinition
from litestar.dto.field import Mark
from litestar.enums import RequestEncodingType
from litestar.serialization import decode_json, decode_msgpack
from litestar.types import Empty
from litestar.typing import FieldDefinition
from litestar.utils.typing import safe_generic_origin_map

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
    from litestar.dto import AbstractDTO, RenameStrategy
    from litestar.types.serialization import LitestarEncodableType

__all__ = ("DTOBackend",)


class DTOBackend:
    __slots__ = (
        "annotation",
        "dto_data_type",
        "dto_factory",
        "field_definition",
        "handler_id",
        "is_data_field",
        "model_type",
        "override_serialization_name",
        "parsed_field_definitions",
        "reverse_name_map",
        "transfer_model_type",
        "wrapper_attribute_name",
        "_transfer_to_dict",
        "_transfer_to_model_type",
        "_transfer_fns",
    )

    _seen_model_names: ClassVar[set[str]] = set()

    def __init__(
        self,
        dto_factory: type[AbstractDTO],
        field_definition: FieldDefinition,
        handler_id: str,
        is_data_field: bool,
        model_type: type[Any],
        wrapper_attribute_name: str | None,
    ) -> None:
        """Create dto backend instance.

        Args:
            dto_factory: The DTO factory class calling this backend.
            field_definition: Parsed type.
            handler_id: The name of the handler that this backend is for.
            is_data_field: Whether or not the field is a subclass of DTOData.
            model_type: Model type.
            wrapper_attribute_name: If the data that DTO should operate upon is wrapped in a generic datastructure, this is the name of the attribute that the data is stored in.
        """
        self.dto_factory: Final[type[AbstractDTO]] = dto_factory
        self.field_definition: Final[FieldDefinition] = field_definition
        self.is_data_field: Final[bool] = is_data_field
        self.handler_id: Final[str] = handler_id
        self.model_type: Final[type[Any]] = model_type
        self.wrapper_attribute_name: Final[str | None] = wrapper_attribute_name

        self.parsed_field_definitions = self.parse_model(
            model_type=model_type, exclude=self.dto_factory.config.exclude, include=self.dto_factory.config.include
        )
        self.transfer_model_type = self.create_transfer_model_type(
            model_name=model_type.__name__, field_definitions=self.parsed_field_definitions
        )
        self.dto_data_type: type[DTOData] | None = None

        self.override_serialization_name: bool = False
        if field_definition.is_subclass_of(DTOData):
            self.dto_data_type = field_definition.annotation
            annotation = self.field_definition.inner_types[0].annotation
        else:
            annotation = field_definition.annotation

        self.annotation = _maybe_wrap_in_generic_annotation(annotation, self.transfer_model_type)
        self._transfer_fns: dict[str, Callable[[Any], Any]] = {}
        self._transfer_to_dict = self._create_transfer_data_fn(
            destination_type=dict,
            field_definition=self.field_definition,
        )
        self._transfer_to_model_type = self._create_transfer_data_fn(
            destination_type=self.model_type,
            field_definition=self.field_definition,
        )

    def parse_model(
        self, model_type: Any, exclude: AbstractSet[str], include: AbstractSet[str], nested_depth: int = 0
    ) -> tuple[TransferDTOFieldDefinition, ...]:
        """Reduce :attr:`model_type` to a tuple :class:`TransferDTOFieldDefinition` instances.

        Returns:
        Fields for data transfer.
        """
        defined_fields = []
        generic_field_definitons = list(FieldDefinition.from_annotation(model_type).generic_types or ())
        for field_definition in self.dto_factory.generate_field_definitions(model_type):
            if field_definition.is_type_var:
                base_arg_field = generic_field_definitons.pop()
                field_definition = replace(
                    field_definition, annotation=base_arg_field.annotation, raw=base_arg_field.raw
                )

            if _should_mark_private(field_definition, self.dto_factory.config.underscore_fields_private):
                field_definition.dto_field.mark = Mark.PRIVATE

            try:
                transfer_type = self._create_transfer_type(
                    field_definition=field_definition,
                    exclude=exclude,
                    include=include,
                    field_name=field_definition.name,
                    unique_name=field_definition.model_name,
                    nested_depth=nested_depth,
                )
            except RecursionError:
                continue

            if rename := self.dto_factory.config.rename_fields.get(field_definition.name):
                serialization_name = rename
            elif self.dto_factory.config.rename_strategy:
                serialization_name = _rename_field(
                    name=field_definition.name, strategy=self.dto_factory.config.rename_strategy
                )
            else:
                serialization_name = field_definition.name

            transfer_field_definition = TransferDTOFieldDefinition.from_dto_field_definition(
                field_definition=field_definition,
                serialization_name=serialization_name,
                transfer_type=transfer_type,
                is_partial=self.dto_factory.config.partial,
                is_excluded=_should_exclude_field(
                    field_definition=field_definition,
                    exclude=exclude,
                    include=include,
                    is_data_field=self.is_data_field,
                ),
            )
            defined_fields.append(transfer_field_definition)
        return tuple(defined_fields)

    def create_transfer_model_type(
        self, model_name: str, field_definitions: tuple[TransferDTOFieldDefinition, ...]
    ) -> type[Struct]:
        """Create a model for data transfer.

        Args:
            model_name: name for the type that should be unique across all transfer types.
            field_definitions: field definitions for the container type.

        Returns:
            A ``BackendT`` class.
        """
        long_name_prefix = self.handler_id.split("::")[0]
        short_name_prefix = _camelize(long_name_prefix.split(".")[-1], True)

        name_suffix = "RequestBody" if self.is_data_field else "ResponseBody"

        if f"{short_name_prefix}{model_name}{name_suffix}" not in self._seen_model_names:
            struct_name = f"{short_name_prefix}{model_name}{name_suffix}"
        elif f"{long_name_prefix}{model_name}{name_suffix}" not in self._seen_model_names:
            struct_name = f"{long_name_prefix}{model_name}{name_suffix}"
        else:
            struct_name = f"{long_name_prefix}{model_name}{name_suffix}{secrets.token_hex(8)}"

        self._seen_model_names.add(struct_name)
        struct = _create_struct_for_field_definitions(struct_name, field_definitions)
        setattr(struct, "__schema_name__", struct_name)
        return struct

    def parse_raw(self, raw: bytes, asgi_connection: ASGIConnection) -> Struct | Collection[Struct]:
        """Parse raw bytes into transfer model type.

        Args:
            raw: bytes
            asgi_connection: The current ASGI Connection

        Returns:
            The raw bytes parsed into transfer model type.
        """
        request_encoding = RequestEncodingType.JSON

        if (content_type := getattr(asgi_connection, "content_type", None)) and (media_type := content_type[0]):
            request_encoding = media_type

        type_decoders = asgi_connection.route_handler.resolve_type_decoders()

        if request_encoding == RequestEncodingType.MESSAGEPACK:
            result = decode_msgpack(value=raw, target_type=self.annotation, type_decoders=type_decoders)
        else:
            result = decode_json(value=raw, target_type=self.annotation, type_decoders=type_decoders)

        return cast("Struct | Collection[Struct]", result)

    def parse_builtins(self, builtins: Any, asgi_connection: ASGIConnection) -> Any:
        """Parse builtin types into transfer model type.

        Args:
            builtins: Builtin type.
            asgi_connection: The current ASGI Connection

        Returns:
            The builtin type parsed into transfer model type.
        """
        return convert(
            obj=builtins,
            type=self.annotation,
            dec_hook=asgi_connection.route_handler.default_deserializer,
            strict=False,
            str_keys=True,
        )

    def populate_data_from_builtins(self, builtins: Any, asgi_connection: ASGIConnection) -> Any:
        """Populate model instance from builtin types.

        Args:
            builtins: Builtin type.
            asgi_connection: The current ASGI Connection

        Returns:
            Instance or collection of ``model_type`` instances.
        """
        if self.dto_data_type:
            return self.dto_data_type(
                backend=self,
                data_as_builtins=self._transfer_to_dict(self.parse_builtins(builtins, asgi_connection)),
            )
        return self.transfer_data_from_builtins(self.parse_builtins(builtins, asgi_connection))

    def transfer_data_from_builtins(self, builtins: Any, override_serialization_name: bool = False) -> Any:
        """Populate model instance from builtin types.

        Args:
            builtins: Builtin type.
            override_serialization_name: Use the original field names, used when creating
                                         an instance using `DTOData.create_instance`

        Returns:
            Instance or collection of ``model_type`` instances.
        """
        self.override_serialization_name = override_serialization_name
        if not (transfer_fn := self._transfer_fns.get("transfer_data_from_builtins")):
            transfer_fn = self._transfer_fns["transfer_data_from_builtins"] = self._create_transfer_data_fn(
                destination_type=self.model_type,
                field_definition=self.field_definition,
            )
        data = transfer_fn(builtins)
        self.override_serialization_name = False
        return data

    def populate_data_from_raw(self, raw: bytes, asgi_connection: ASGIConnection) -> Any:
        """Parse raw bytes into instance of `model_type`.

        Args:
            raw: bytes
            asgi_connection: The current ASGI Connection

        Returns:
            Instance or collection of ``model_type`` instances.
        """
        if self.dto_data_type:
            return self.dto_data_type(
                backend=self,
                data_as_builtins=self._transfer_to_dict(self.parse_raw(raw, asgi_connection)),
            )
        return self._transfer_to_model_type(self.parse_raw(raw, asgi_connection))

    def encode_data(self, data: Any) -> LitestarEncodableType:
        """Encode data into a ``LitestarEncodableType``.

        Args:
            data: Data to encode.

        Returns:
            Encoded data.
        """
        if not (transfer_fn := self._transfer_fns.get("encode_data")):
            transfer_fn = self._transfer_fns["encode_data"] = self._create_transfer_data_fn(
                destination_type=self.transfer_model_type,
                field_definition=self.field_definition,
            )
        if self.wrapper_attribute_name:
            wrapped_transfer = transfer_fn(getattr(data, self.wrapper_attribute_name))
            setattr(data, self.wrapper_attribute_name, wrapped_transfer)
            return cast("LitestarEncodableType", data)

        return cast("LitestarEncodableType", transfer_fn(data))

    def _create_transfer_data_fn(self, destination_type: type[Any], field_definition: FieldDefinition) -> Any:
        """Create instance or iterable of instances of ``destination_type``.

        Args:
            destination_type: the model type received by the DTO on type narrowing.
            field_definition: the parsed type that represents the handler annotation for which the DTO is being applied.

        Returns:
            Data parsed into ``destination_type``.
        """

        return TransferFunctionFactory.create_transfer_data(
            destination_type=destination_type,
            field_definitions=self.parsed_field_definitions,
            is_data_field=self.is_data_field,
            override_serialization_name=self.override_serialization_name,
            field_definition=field_definition,
        )

    def _get_handler_for_field_definition(
        self, field_definition: FieldDefinition
    ) -> Callable[[FieldDefinition, AbstractSet[str], AbstractSet[str], str, int], CompositeType] | None:
        if field_definition.is_union:
            return self._create_union_type

        if field_definition.is_tuple:
            if len(field_definition.inner_types) == 2 and field_definition.inner_types[1].annotation is Ellipsis:
                return self._create_collection_type
            return self._create_tuple_type

        if field_definition.is_mapping:
            return self._create_mapping_type

        if field_definition.is_non_string_collection:
            return self._create_collection_type
        return None

    def _create_transfer_type(
        self,
        field_definition: FieldDefinition,
        exclude: AbstractSet[str],
        include: AbstractSet[str],
        field_name: str,
        unique_name: str,
        nested_depth: int,
    ) -> CompositeType | SimpleType:
        exclude = _filter_nested_field(exclude, field_name)
        include = _filter_nested_field(include, field_name)

        if composite_type_handler := self._get_handler_for_field_definition(field_definition):
            return composite_type_handler(field_definition, exclude, include, unique_name, nested_depth)

        transfer_model: NestedFieldInfo | None = None

        if self.dto_factory.detect_nested_field(field_definition):
            if nested_depth == self.dto_factory.config.max_nested_depth:
                raise RecursionError

            nested_field_definitions = self.parse_model(
                model_type=field_definition.annotation, exclude=exclude, include=include, nested_depth=nested_depth + 1
            )

            transfer_model = NestedFieldInfo(
                model=self.create_transfer_model_type(unique_name, nested_field_definitions),
                field_definitions=nested_field_definitions,
            )

        return SimpleType(field_definition, nested_field_info=transfer_model)

    def _create_collection_type(
        self,
        field_definition: FieldDefinition,
        exclude: AbstractSet[str],
        include: AbstractSet[str],
        unique_name: str,
        nested_depth: int,
    ) -> CollectionType:
        inner_types = field_definition.inner_types
        inner_type = self._create_transfer_type(
            field_definition=inner_types[0] if inner_types else FieldDefinition.from_annotation(Any),
            exclude=exclude,
            include=include,
            field_name="0",
            unique_name=f"{unique_name}_0",
            nested_depth=nested_depth,
        )
        return CollectionType(
            field_definition=field_definition, inner_type=inner_type, has_nested=inner_type.has_nested
        )

    def _create_mapping_type(
        self,
        field_definition: FieldDefinition,
        exclude: AbstractSet[str],
        include: AbstractSet[str],
        unique_name: str,
        nested_depth: int,
    ) -> MappingType:
        inner_types = field_definition.inner_types
        key_type = self._create_transfer_type(
            field_definition=inner_types[0] if inner_types else FieldDefinition.from_annotation(Any),
            exclude=exclude,
            include=include,
            field_name="0",
            unique_name=f"{unique_name}_0",
            nested_depth=nested_depth,
        )
        value_type = self._create_transfer_type(
            field_definition=inner_types[1] if inner_types else FieldDefinition.from_annotation(Any),
            exclude=exclude,
            include=include,
            field_name="1",
            unique_name=f"{unique_name}_1",
            nested_depth=nested_depth,
        )
        return MappingType(
            field_definition=field_definition,
            key_type=key_type,
            value_type=value_type,
            has_nested=key_type.has_nested or value_type.has_nested,
        )

    def _create_tuple_type(
        self,
        field_definition: FieldDefinition,
        exclude: AbstractSet[str],
        include: AbstractSet[str],
        unique_name: str,
        nested_depth: int,
    ) -> TupleType:
        inner_types = tuple(
            self._create_transfer_type(
                field_definition=inner_type,
                exclude=exclude,
                include=include,
                field_name=str(i),
                unique_name=f"{unique_name}_{i}",
                nested_depth=nested_depth,
            )
            for i, inner_type in enumerate(field_definition.inner_types)
        )
        return TupleType(
            field_definition=field_definition,
            inner_types=inner_types,
            has_nested=any(t.has_nested for t in inner_types),
        )

    def _create_union_type(
        self,
        field_definition: FieldDefinition,
        exclude: AbstractSet[str],
        include: AbstractSet[str],
        unique_name: str,
        nested_depth: int,
    ) -> UnionType:
        inner_types = tuple(
            self._create_transfer_type(
                field_definition=inner_type,
                exclude=exclude,
                include=include,
                field_name=str(i),
                unique_name=f"{unique_name}_{i}",
                nested_depth=nested_depth,
            )
            for i, inner_type in enumerate(field_definition.inner_types)
        )
        return UnionType(
            field_definition=field_definition,
            inner_types=inner_types,
            has_nested=any(t.has_nested for t in inner_types),
        )


def _camelize(value: str, capitalize_first_letter: bool) -> str:
    return "".join(
        word if index == 0 and not capitalize_first_letter else word.capitalize()
        for index, word in enumerate(value.split("_"))
    )


def _rename_field(name: str, strategy: RenameStrategy) -> str:
    if callable(strategy):
        return strategy(name)

    if strategy == "camel":
        return _camelize(value=name, capitalize_first_letter=False)

    if strategy == "pascal":
        return _camelize(value=name, capitalize_first_letter=True)

    return name.lower() if strategy == "lower" else name.upper()


def _filter_nested_field(field_name_set: AbstractSet[str], field_name: str) -> AbstractSet[str]:
    """Filter a nested field name."""
    return {split[1] for s in field_name_set if (split := s.split(".", 1))[0] == field_name and len(split) > 1}


def _gen_uniq_name(ctx: Container, name: str) -> str:
    i = 0
    while True:
        unique_name = f"{name}_{i}"
        if unique_name not in ctx:
            return unique_name
        i += 1


class FieldAccessManager(Protocol):
    def __call__(self, source_instance_name: str, field_name: str, expect_optional: bool) -> ContextManager[str]:
        ...


class TransferFunctionFactory:
    def __init__(self, is_data_field: bool, override_serialization_name: bool, nested_as_dict: bool) -> None:
        self.is_data_field = is_data_field
        self.override_serialization_name = override_serialization_name
        self.fn_locals: dict[str, Any] = {
            "Mapping": Mapping,
            "_transfer_nested_union_type_data": _transfer_nested_union_type_data,
            "UNSET": UNSET,
        }
        self.indentation = 1
        self.body = ""
        self.names: set[str] = set()
        self.nested_as_dict = nested_as_dict

    def add_to_fn_globals(self, name: str, value: Any) -> str:
        unique_name = _gen_uniq_name(self.fn_locals, name)
        self.fn_locals[unique_name] = value
        return unique_name

    def create_local_name(self, name: str) -> str:
        unique_name = _gen_uniq_name(self.names, name)
        self.names.add(unique_name)
        return unique_name

    @contextmanager
    def start_indented_block(self) -> Generator[None, None, None]:
        self.indentation += 1
        yield
        self.indentation -= 1

    def add_stmt(self, stmt: str, newline: bool = True, indentation: int | None = None) -> None:
        self.body += textwrap.indent(
            stmt + ("\n" if newline else ""), " " * (indentation if indentation is not None else self.indentation)
        )

    @contextmanager
    def _access_mapping_item(
        self, source_instance_name: str, field_name: str, expect_optional: bool
    ) -> Generator[str, None, None]:
        value_expr = f"{source_instance_name}['{field_name}']"

        # if we expect an optional item, it's faster to check if it exists beforehand
        if expect_optional:
            self.add_stmt(f"if '{field_name}' in {source_instance_name}:")
            with self.start_indented_block():
                yield value_expr
        # the happy path of a try/except will be faster than that, so we use that if
        # we expect a value
        else:
            self.add_stmt("try:")
            with self.start_indented_block():
                yield value_expr
            self.add_stmt("except KeyError:")
            with self.start_indented_block():
                self.add_stmt("pass")

    @contextmanager
    def _access_attribute(
        self, source_instance_name: str, field_name: str, expect_optional: bool
    ) -> Generator[str, None, None]:
        value_expr = f"{source_instance_name}.{field_name}"

        # if we expect an optional attribute it's faster to check with hasattr
        if expect_optional:
            self.add_stmt(f"if hasattr({source_instance_name}, '{field_name}'):")
            with self.start_indented_block():
                yield value_expr
        # the happy path of a try/except will be faster than that, so we use that if
        # we expect a value
        else:
            self.add_stmt("try:")
            with self.start_indented_block():
                yield value_expr
            self.add_stmt("except AttributeError:")
            with self.start_indented_block():
                self.add_stmt("pass")

    @classmethod
    def create_transfer_instance_data(
        cls,
        field_definitions: tuple[TransferDTOFieldDefinition, ...],
        destination_type: type[Any],
        is_data_field: bool,
        override_serialization_name: bool,
    ) -> Callable[[Any], Any]:
        factory = cls(
            is_data_field=is_data_field,
            override_serialization_name=override_serialization_name,
            nested_as_dict=destination_type is dict,
        )
        tmp_return_type_name = factory.create_local_name("tmp_return_type")
        source_instance_name = factory.create_local_name("source_instance")
        destination_type_name = factory.add_to_fn_globals("destination_type", destination_type)
        factory._create_transfer_instance_data(
            tmp_return_type_name=tmp_return_type_name,
            source_instance_name=source_instance_name,
            destination_type_name=destination_type_name,
            field_definitions=field_definitions,
            destination_type_is_dict=destination_type is dict,
        )
        return factory._make_function(source_value_name=source_instance_name, return_value_name=tmp_return_type_name)

    @classmethod
    def create_transfer_type_data(
        cls,
        transfer_type: TransferType,
        is_data_field: bool,
        override_serialization_name: bool,
    ) -> Callable[[Any], Any]:
        factory = cls(
            is_data_field=is_data_field, override_serialization_name=override_serialization_name, nested_as_dict=False
        )
        tmp_return_type_name = factory.create_local_name("tmp_return_type")
        source_value_name = factory.create_local_name("source_value")
        factory._create_transfer_type_data_body(
            transfer_type=transfer_type,
            nested_as_dict=False,
            assignment_target=tmp_return_type_name,
            source_value_name=source_value_name,
        )
        return factory._make_function(source_value_name=source_value_name, return_value_name=tmp_return_type_name)

    @classmethod
    def create_transfer_data(
        cls,
        destination_type: type[Any],
        field_definitions: tuple[TransferDTOFieldDefinition, ...],
        is_data_field: bool,
        override_serialization_name: bool,
        field_definition: FieldDefinition | None = None,
    ) -> Callable[[Any], Any]:
        if field_definition and field_definition.is_non_string_collection and not field_definition.is_mapping:
            factory = cls(
                is_data_field=is_data_field,
                override_serialization_name=override_serialization_name,
                nested_as_dict=False,
            )
            source_value_name = factory.create_local_name("source_value")
            return_value_name = factory.create_local_name("tmp_return_value")
            factory._create_transfer_data_body_nested(
                field_definitions=field_definitions,
                field_definition=field_definition,
                destination_type=destination_type,
                source_data_name=source_value_name,
                assignment_target=return_value_name,
            )
            return factory._make_function(source_value_name=source_value_name, return_value_name=return_value_name)

        return cls.create_transfer_instance_data(
            destination_type=destination_type,
            field_definitions=field_definitions,
            is_data_field=is_data_field,
            override_serialization_name=override_serialization_name,
        )

    def _create_transfer_data_body_nested(
        self,
        field_definition: FieldDefinition,
        field_definitions: tuple[TransferDTOFieldDefinition, ...],
        destination_type: type[Any],
        source_data_name: str,
        assignment_target: str,
    ) -> None:
        origin_name = self.add_to_fn_globals("origin", field_definition.instantiable_origin)
        transfer_func = TransferFunctionFactory.create_transfer_data(
            is_data_field=self.is_data_field,
            destination_type=destination_type,
            field_definition=field_definition.inner_types[0],
            field_definitions=field_definitions,
            override_serialization_name=self.override_serialization_name,
        )
        transfer_func_name = self.add_to_fn_globals("transfer_data", transfer_func)
        self.add_stmt(f"{assignment_target} = {origin_name}({transfer_func_name}(item) for item in {source_data_name})")

    def _make_function(self, source_value_name: str, return_value_name: str) -> Callable[[Any], Any]:
        source = f"def func({source_value_name}):\n" + self.body + f" return {return_value_name}"
        ctx: dict[str, Any] = {}
        exec(source, self.fn_locals, ctx)  # noqa: S102
        return ctx["func"]  # type: ignore[no-any-return]

    def _create_transfer_instance_data(
        self,
        tmp_return_type_name: str,
        source_instance_name: str,
        destination_type_name: str,
        field_definitions: tuple[TransferDTOFieldDefinition, ...],
        destination_type_is_dict: bool,
    ) -> None:
        local_dict_name = self.create_local_name("unstructured_data")
        self.add_stmt(f"{local_dict_name} = {{}}")

        field_definitions = tuple(f for f in field_definitions if self.is_data_field or not f.is_excluded)

        if field_definitions:
            for source_type in ("mapping", "object"):
                if source_type == "mapping":
                    self.add_stmt(f"if isinstance({source_instance_name}, Mapping):")
                    access_item = self._access_mapping_item
                else:
                    self.add_stmt("else:")
                    access_item = self._access_attribute

                with self.start_indented_block():
                    self._create_transfer_instance_data_inner(
                        local_dict_name=local_dict_name,
                        field_definitions=field_definitions,
                        access_field_safe=access_item,
                        source_instance_name=source_instance_name,
                    )

        # if the destination type is a dict we can reuse our temporary dictionary of
        # unstructured data as the "return value"
        if not destination_type_is_dict:
            self.add_stmt(f"{tmp_return_type_name} = {destination_type_name}(**{local_dict_name})")
        else:
            self.add_stmt(f"{tmp_return_type_name} = {local_dict_name}")

    def _create_transfer_instance_data_inner(
        self,
        *,
        local_dict_name: str,
        field_definitions: tuple[TransferDTOFieldDefinition, ...],
        access_field_safe: FieldAccessManager,
        source_instance_name: str,
    ) -> None:
        should_use_serialization_name = not self.override_serialization_name and self.is_data_field
        for field_definition in field_definitions:
            source_field_name = (
                field_definition.serialization_name if should_use_serialization_name else field_definition.name
            )
            destination_name = field_definition.name if self.is_data_field else field_definition.serialization_name

            with access_field_safe(
                source_instance_name=source_instance_name,
                field_name=source_field_name,
                expect_optional=field_definition.is_partial or field_definition.is_optional,
            ) as source_value_expr:
                if self.is_data_field and field_definition.is_partial:
                    # we assign the source value to a name here, so we can skip
                    # getting it twice from the source instance
                    source_value_name = self.create_local_name("source_value")
                    self.add_stmt(f"{source_value_name} = {source_value_expr}")
                    self.add_stmt(f"if {source_value_name} is not UNSET:")
                    ctx = self.start_indented_block()
                else:
                    # in these cases, we only ever access the source value once, so
                    # we can skip assigning it
                    source_value_name = source_value_expr
                    ctx = nullcontext()  # type: ignore[assignment]
                with ctx:
                    self._create_transfer_type_data_body(
                        transfer_type=field_definition.transfer_type,
                        nested_as_dict=self.nested_as_dict,
                        source_value_name=source_value_name,
                        assignment_target=f"{local_dict_name}['{destination_name}']",
                    )

    def _create_transfer_type_data_body(
        self,
        transfer_type: TransferType,
        nested_as_dict: bool,
        source_value_name: str,
        assignment_target: str,
    ) -> None:
        if isinstance(transfer_type, SimpleType) and transfer_type.nested_field_info:
            if nested_as_dict:
                destination_type: Any = dict
            elif self.is_data_field:
                destination_type = transfer_type.field_definition.annotation
            else:
                destination_type = transfer_type.nested_field_info.model

            self._create_transfer_instance_data(
                field_definitions=transfer_type.nested_field_info.field_definitions,
                tmp_return_type_name=assignment_target,
                source_instance_name=source_value_name,
                destination_type_name=self.add_to_fn_globals("destination_type", destination_type),
                destination_type_is_dict=destination_type is dict,
            )
            return

        if isinstance(transfer_type, UnionType) and transfer_type.has_nested:
            self.add_stmt(
                f"{assignment_target} = _transfer_nested_union_type_data("
                f"transfer_type={self.add_to_fn_globals('transfer_type', transfer_type)},"
                f"source_value={source_value_name},"
                f"is_data_field={self.is_data_field},"
                f"override_serialization_name={self.override_serialization_name})"
            )
            return

        if isinstance(transfer_type, CollectionType):
            origin_name = self.add_to_fn_globals("origin", transfer_type.field_definition.instantiable_origin)
            if transfer_type.has_nested:
                transfer_type_data_fn = TransferFunctionFactory.create_transfer_type_data(
                    is_data_field=self.is_data_field,
                    override_serialization_name=self.override_serialization_name,
                    transfer_type=transfer_type.inner_type,
                )
                transfer_type_data_name = self.add_to_fn_globals("transfer_type_data", transfer_type_data_fn)
                self.add_stmt(
                    f"{assignment_target} = {origin_name}({transfer_type_data_name}(item) for item in {source_value_name})"
                )
                return

            self.add_stmt(f"{assignment_target} = {origin_name}({source_value_name})")
            return

        self.add_stmt(f"{assignment_target} = {source_value_name}")


def _transfer_instance_data(
    destination_type: type[Any],
    source_instance: Any,
    field_definitions: tuple[TransferDTOFieldDefinition, ...],
    is_data_field: bool,
    override_serialization_name: bool,
) -> Any:
    fn = TransferFunctionFactory.create_transfer_instance_data(
        field_definitions=field_definitions,
        destination_type=destination_type,
        is_data_field=is_data_field,
        override_serialization_name=override_serialization_name,
    )
    return fn(source_instance)


def _transfer_nested_union_type_data(
    transfer_type: UnionType,
    source_value: Any,
    is_data_field: bool,
    override_serialization_name: bool,
) -> Any:
    for inner_type in transfer_type.inner_types:
        if isinstance(inner_type, CompositeType):
            raise RuntimeError("Composite inner types not (yet) supported for nested unions.")

        if inner_type.nested_field_info and isinstance(
            source_value,
            inner_type.nested_field_info.model if is_data_field else inner_type.field_definition.annotation,
        ):
            return _transfer_instance_data(
                destination_type=inner_type.field_definition.annotation
                if is_data_field
                else inner_type.nested_field_info.model,
                source_instance=source_value,
                field_definitions=inner_type.nested_field_info.field_definitions,
                is_data_field=is_data_field,
                override_serialization_name=override_serialization_name,
            )
    return source_value


def _create_msgspec_field(field_definition: TransferDTOFieldDefinition) -> Any:
    kwargs: dict[str, Any] = {}
    if field_definition.is_partial:
        kwargs["default"] = UNSET

    elif field_definition.default is not Empty:
        kwargs["default"] = field_definition.default

    elif field_definition.default_factory is not None:
        kwargs["default_factory"] = field_definition.default_factory

    return field(**kwargs)


def _create_struct_for_field_definitions(
    model_name: str, field_definitions: tuple[TransferDTOFieldDefinition, ...]
) -> type[Struct]:
    struct_fields: list[tuple[str, type] | tuple[str, type, type]] = []

    for field_definition in field_definitions:
        if field_definition.is_excluded:
            continue

        field_type = _create_transfer_model_type_annotation(field_definition.transfer_type)
        if field_definition.is_partial:
            field_type = Union[field_type, UnsetType]

        struct_fields.append(
            (
                field_definition.serialization_name or field_definition.name,
                field_type,
                _create_msgspec_field(field_definition),
            )
        )
    return defstruct(model_name, struct_fields, frozen=True, kw_only=True)


def _maybe_wrap_in_generic_annotation(annotation: Any, model: Any) -> Any:
    """A helper to re-build a generic outer type with new inner type.

    Args:
        annotation: The original annotation on the handler signature
        model: The data container type

    Returns:
        Annotation with new inner type if applicable.
    """
    if (origin := get_origin(annotation)) and origin in safe_generic_origin_map:
        return safe_generic_origin_map[origin][model]  # type: ignore[index]

    return origin[model] if (origin := get_origin(annotation)) else model


def _should_mark_private(field_definition: DTOFieldDefinition, underscore_fields_private: bool) -> bool:
    """Returns ``True`` where a field should be marked as private.

    Fields should be marked as private when:
    - the ``underscore_fields_private`` flag is set.
    - the field is not already marked.
    - the field name is prefixed with an underscore

    Args:
        field_definition: defined DTO field
        underscore_fields_private: whether fields prefixed with an underscore should be marked as private.
    """
    return bool(
        underscore_fields_private and field_definition.dto_field.mark is None and field_definition.name.startswith("_")
    )


def _should_exclude_field(
    field_definition: DTOFieldDefinition, exclude: AbstractSet[str], include: AbstractSet[str], is_data_field: bool
) -> bool:
    """Returns ``True`` where a field should be excluded from data transfer.

    Args:
        field_definition: defined DTO field
        exclude: names of fields to exclude
        include: names of fields to exclude
        is_data_field: whether the field is a data field

    Returns:
        ``True`` if the field should not be included in any data transfer.
    """
    field_name = field_definition.name
    if field_name in exclude:
        return True
    if include and field_name not in include and not (any(f.startswith(f"{field_name}.") for f in include)):
        return True
    if field_definition.dto_field.mark is Mark.PRIVATE:
        return True
    if is_data_field and field_definition.dto_field.mark is Mark.READ_ONLY:
        return True
    return not is_data_field and field_definition.dto_field.mark is Mark.WRITE_ONLY


def _create_transfer_model_type_annotation(transfer_type: TransferType) -> Any:
    """Create a type annotation for a transfer model.

    Uses the parsed type that originates from the data model and the transfer model generated to represent a nested
    type to reconstruct the type annotation for the transfer model.
    """
    if isinstance(transfer_type, SimpleType):
        if transfer_type.nested_field_info:
            return transfer_type.nested_field_info.model
        return transfer_type.field_definition.annotation

    if isinstance(transfer_type, CollectionType):
        return _create_transfer_model_collection_type(transfer_type)

    if isinstance(transfer_type, MappingType):
        return _create_transfer_model_mapping_type(transfer_type)

    if isinstance(transfer_type, TupleType):
        return _create_transfer_model_tuple_type(transfer_type)

    if isinstance(transfer_type, UnionType):
        return _create_transfer_model_union_type(transfer_type)

    raise RuntimeError(f"Unexpected transfer type: {type(transfer_type)}")


def _create_transfer_model_collection_type(transfer_type: CollectionType) -> Any:
    generic_collection_type = transfer_type.field_definition.safe_generic_origin
    inner_type = _create_transfer_model_type_annotation(transfer_type.inner_type)
    if transfer_type.field_definition.origin is tuple:
        return generic_collection_type[inner_type, ...]
    return generic_collection_type[inner_type]


def _create_transfer_model_tuple_type(transfer_type: TupleType) -> Any:
    inner_types = tuple(_create_transfer_model_type_annotation(t) for t in transfer_type.inner_types)
    return transfer_type.field_definition.safe_generic_origin[inner_types]


def _create_transfer_model_union_type(transfer_type: UnionType) -> Any:
    inner_types = tuple(_create_transfer_model_type_annotation(t) for t in transfer_type.inner_types)
    return transfer_type.field_definition.safe_generic_origin[inner_types]


def _create_transfer_model_mapping_type(transfer_type: MappingType) -> Any:
    key_type = _create_transfer_model_type_annotation(transfer_type.key_type)
    value_type = _create_transfer_model_type_annotation(transfer_type.value_type)
    return transfer_type.field_definition.safe_generic_origin[key_type, value_type]
