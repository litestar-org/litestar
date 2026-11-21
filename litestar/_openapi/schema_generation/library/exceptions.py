from litestar.exceptions import ImproperlyConfiguredException

__all__ = (
    "LibrarySchemaError",
    "SchemaConversionError",
    "SchemaNameConflictError",
    "UnresolvedSchemaError",
)


class LibrarySchemaError(ImproperlyConfiguredException):
    """A library-generated schema cannot be documented."""


class UnresolvedSchemaError(LibrarySchemaError):
    """The library resolvers did not produce a schema for every request."""


class SchemaNameConflictError(LibrarySchemaError):
    """An explicit component name is already used by a different schema."""


class SchemaConversionError(LibrarySchemaError):
    """A library-generated schema cannot be turned into an OpenAPI component."""
