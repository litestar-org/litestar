from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Tuple, Union


def _as_string(value: Any) -> str:
    if isinstance(value, str):
        return '"' + value + '"'

    if isinstance(value, bool):
        return "true" if value else "false"

    return str(value)


class TypeScriptElement(ABC):
    """A class representing a TypeScript type element."""

    @abstractmethod
    def write(self) -> str:
        """Write a typescript value corresponding to the given typescript element.

        Returns:
            A typescript string
        """
        raise NotImplementedError("")


class TypeScriptContainer(TypeScriptElement):
    """A class representing a TypeScript type container."""

    name: str

    @abstractmethod
    def write(self) -> str:
        """Write a typescript value corresponding to the given typescript container.

        Returns:
            A typescript string
        """
        raise NotImplementedError("")


@dataclass(unsafe_hash=True)
class TypeScriptIntersection(TypeScriptElement):
    """A class representing a TypeScript intersection type."""

    types: Iterable[TypeScriptElement]

    def write(self) -> str:
        """Write a typescript intersection value.

        Example:
            { prop: string } & { another: number }

        Returns:
            A typescript string
        """
        return " & ".join(t.write() for t in self.types)


@dataclass(unsafe_hash=True)
class TypeScriptUnion(TypeScriptElement):
    """A class representing a TypeScript union type."""

    types: Iterable[TypeScriptElement]

    def write(self) -> str:
        """Write a typescript union value.

        Example:
            string | number

        Returns:
            A typescript string
        """
        return " | ".join(t.write() for t in self.types)


@dataclass(unsafe_hash=True)
class TypeScriptPrimitive(TypeScriptElement):
    """A class representing a TypeScript primitive type."""

    type: Literal["string", "number", "boolean", "any", "null", "undefined", "symbol"]

    def write(self) -> str:
        """Write a typescript primitive type.

        Example:
            null

        Returns:
            A typescript string
        """
        return self.type


@dataclass(unsafe_hash=True)
class TypeScriptLiteral(TypeScriptElement):
    """A class representing a TypeScript literal type."""

    value: Union[str, int, float, bool]

    def write(self) -> str:
        """Write a typescript literal type.

        Example:
            "someValue"

        Returns:
            A typescript string
        """
        return _as_string(self.value)


@dataclass(unsafe_hash=True)
class TypeScriptArray(TypeScriptElement):
    """A class representing a TypeScript array type."""

    item_type: TypeScriptElement

    def write(self) -> str:
        """Write a typescript array type.

        Example:
            number[]

        Returns:
            A typescript string
        """
        value = (
            f"({self.item_type.write()})"
            if isinstance(self.item_type, (TypeScriptUnion, TypeScriptIntersection))
            else self.item_type.write()
        )
        return f"{value}[]"


@dataclass(unsafe_hash=True)
class TypeScriptProperty(TypeScriptElement):
    """A class representing a TypeScript interface property."""

    required: bool
    key: str
    value: TypeScriptElement

    def write(self) -> str:
        """Write a typescript property. This class is used exclusively inside interfaces.

        Example:
            key: string;
            optional?: number;

        Returns:
            A typescript string
        """
        return f"{self.key}{':' if self.required else '?:'} {self.value.write()};"


@dataclass(unsafe_hash=True)
class TypeScriptAnonymousInterface(TypeScriptElement):
    """A class representing a TypeScript anonymous interface."""

    properties: Iterable[TypeScriptProperty]

    def write(self) -> str:
        """Write a typescript interface object, without a name.

        Example:
            {
                key: string;
                optional?: number;
            }

        Returns:
            A typescript string
        """
        props = "\t" + "\n\t".join([prop.write() for prop in sorted(self.properties, key=lambda prop: prop.key)])
        return f"{{\n{props}\n}}"


@dataclass(unsafe_hash=True)
class TypeScriptInterface(TypeScriptContainer):
    """A class representing a TypeScript interface."""

    name: str
    properties: Iterable[TypeScriptProperty]

    def write(self) -> str:
        """Write a typescript interface.

        Example:
            export interface MyInterface {
                key: string;
                optional?: number;
            };

        Returns:
            A typescript string
        """
        interface = TypeScriptAnonymousInterface(properties=self.properties)
        return f"export interface {self.name} {interface.write()};"


@dataclass(unsafe_hash=True)
class TypeScriptEnum(TypeScriptContainer):
    """A class representing a TypeScript enum."""

    name: str
    values: Union[Iterable[Tuple[str, str]], Iterable[Tuple[str, Union[int, float]]]]

    def write(self) -> str:
        """Write a typescript enum.

        Example:
            export enum MyEnum {
                DOG = "canine",
                CAT = "feline",
            };

        Returns:
            A typescript string
        """
        members = "\t" + "\n\t".join(
            [f"{key} = {_as_string(value)}," for key, value in sorted(self.values, key=lambda member: member[0])]
        )
        return f"export enum {self.name} {{\n{members}\n}};"


@dataclass(unsafe_hash=True)
class TypeScriptType(TypeScriptContainer):
    """A class representing a TypeScript type."""

    name: str
    value: TypeScriptElement

    def write(self) -> str:
        """Write a typescript type.

        Example:
            export type MyType = number | "42";

        Returns:
            A typescript string
        """
        return f"export type {self.name} = {self.value.write()};"


@dataclass(unsafe_hash=True)
class TypeScriptConst(TypeScriptContainer):
    """A class representing a TypeScript const."""

    name: str
    value: Union[TypeScriptPrimitive, TypeScriptLiteral]

    def write(self) -> str:
        """Write a typescript const.

        Example:
            export const MyConst: number;

        Returns:
            A typescript string
        """
        return f"export const {self.name}: {self.value.write()};"


@dataclass(unsafe_hash=True)
class TypeScriptNamespace(TypeScriptElement):
    """A class representing a TypeScript namespace."""

    name: str
    values: Iterable[TypeScriptContainer]

    def write(self) -> str:
        """Write a typescript namespace.

        Example:
            export MyNamespace {
                export const MyConst: number;
            }

        Returns:
            A typescript string
        """
        members = "\t" + "\n\n\t".join([value.write() for value in sorted(self.values, key=lambda el: el.name)])
        return f"export namespace {self.name} {{\n{members}\n}};"


#
# TypeScriptType = Union[TypeScriptIntersection, TypeScriptUnion, TypeScriptArray, TypeScriptInterface, TypeScriptEnum]
#
#
# def is_schema_value(value: Any) -> TypeGuard[Schema]:
#     return isinstance(value, Schema)
#
#
# def create_any_of(any_of: List[Schema]) -> TypeScriptUnion:
#     num_of_permutations = len(any_of)
#     parsed_schemas = [parse_schema(s) for s in any_of]
#     variants: List[TypeScriptType] = [*parsed_schemas]
#
#     while num_of_permutations > 1:
#         variants.extend(
#             TypeScriptIntersection(permutation) for permutation in permutations(parsed_schemas, num_of_permutations)
#         )
#         num_of_permutations -= 1
#
#     return TypeScriptUnion(tuple(variants))
#
#
# def parse_schema(schema: Schema) -> TypeScriptType:
#     if all_of := is_schema_value(schema.allOf):
#         return TypeScriptIntersection(tuple(parse_schema(s) for s in all_of))
#     if one_of := is_schema_value(schema.oneOf):
#         return TypeScriptUnion(tuple(parse_schema(s) for s in one_of))
#     if any_of := is_schema_value(schema.anyOf):
#         return create_any_of(any_of)
#     if items := is_schema_value(schema.items):
#         return TypeScriptType(python_container=list, typescript_container=parse_schema(items))
#
#
# def parse_response(response: Response) -> List[Tuple[str, TypeScriptType]]:
#     if response.content:
#
#         response_type = parse_schema(response.content)
#
#
# def create_typescript_types_from_open_api_schema(components: Components) -> Dict[str, TypeScriptTypeContainer]:
#     output: Dict[str, TypeScriptTypeContainer] = {}
#
#     for response in [r for r in (components.responses or []) if isinstance(r, Response)]:
#         type_name, response_type = parse_response(response)
#         output[type_name] = response_type
#
#     return output
