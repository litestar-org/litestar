from __future__ import annotations

import inspect
from inspect import Signature
from typing import Any

from litestar.plugins import DIPlugin
from litestar.plugins.pydantic.utils import is_pydantic_model_class


class PydanticDIPlugin(DIPlugin):
    def has_typed_init(self, type_: Any) -> bool:
        return is_pydantic_model_class(type_)

    def get_typed_init(self, type_: Any) -> tuple[Signature, dict[str, Any]]:
        try:
            model_fields = dict(type_.model_fields)
        except AttributeError:
            model_fields = {k: model_field.field_info for k, model_field in type_.__fields__.items()}

        parameters = [
            inspect.Parameter(name=field_name, kind=inspect.Parameter.KEYWORD_ONLY, annotation=Any)
            for field_name in model_fields
        ]
        type_hints = dict.fromkeys(model_fields, Any)
        return Signature(parameters), type_hints
