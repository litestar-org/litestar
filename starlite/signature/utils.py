from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from starlite.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from starlite.signature.models import SignatureModel


def get_signature_model(value: Any) -> type[SignatureModel]:
    """Retrieve and validate the signature model from a provider or handler."""
    try:
        return cast("type[SignatureModel]", value.signature_model)
    except AttributeError as e:  # pragma: no cover
        raise ImproperlyConfiguredException(f"The 'signature_model' attribute for {value} is not set") from e
