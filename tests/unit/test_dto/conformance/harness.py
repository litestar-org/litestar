import dataclasses
import json
from collections.abc import Callable, Iterator, Mapping
from typing import Annotated, Any, Final, Literal

import msgspec

from litestar import Litestar, get, post
from litestar.dto import DTOConfig, DTOData
from litestar.params import JSONBody
from litestar.testing import TestClient
from tests.unit.test_dto.conformance.features import DIRECTIONS, FEATURES, NA, Case, Direction, Feature
from tests.unit.test_dto.conformance.models import LIBRARIES, Library, Maker, maker

Backend = Literal["codegen", "interp"]
BACKENDS: Final[tuple[Backend, ...]] = ("codegen", "interp")

_json_body: Any = JSONBody
_dto_data: Any = DTOData


def cell_ids() -> Iterator[tuple[Feature, Library, Direction]]:
    for feature in FEATURES:
        for library in LIBRARIES:
            if library in feature.na:
                continue
            for direction in DIRECTIONS:
                expected = feature.requests if direction == "in" else feature.response
                if not isinstance(expected, NA):
                    yield feature, library, direction


def dump(value: Any) -> Any:
    cls = type(value)
    if dataclasses.is_dataclass(value):
        names: tuple[str, ...] = tuple(field.name for field in dataclasses.fields(value))
    elif isinstance(value, msgspec.Struct):
        names = value.__struct_fields__
    elif hasattr(cls, "model_fields"):
        names = tuple(cls.model_fields)
    elif isinstance(value, Mapping):
        return {key: dump(item) for key, item in value.items()}
    elif isinstance(value, (list, tuple, set, frozenset)):
        return [dump(item) for item in value]
    else:
        return value
    label = "<transfer model>" if hasattr(cls, "__schema_name__") else cls.__name__
    return {"$model": label, **{name: dump(getattr(value, name)) for name in names}}


def prepare_handler(
    feature: Feature, m: Maker, case: Case, direction: Direction, backend: Backend
) -> tuple[Callable[..., Any], Any]:
    config = DTOConfig(**feature.config, experimental_codegen_backend=backend == "codegen")
    base: Any = (
        m.dto if feature.accessor is None else type("AccessorDTO", (m.dto,), {"attribute_accessor": feature.accessor})
    )
    dto: Any = base[Annotated[case.model, config]]
    annotation = case.model if case.annotation is None else case.annotation
    receive = feature.receive

    def create(data: Any) -> Any:
        return dump(data if receive is None else receive(data))

    def read() -> Any:
        return case.instance()

    name = f"{feature.id}_{m.library}_{backend}"
    if direction == "in":
        create.__qualname__ = f"create_{name}"
        create.__annotations__["data"] = _json_body[_dto_data[annotation] if feature.dto_data else annotation]
        return create, dto
    read.__qualname__ = f"read_{name}"
    read.__annotations__["return"] = annotation
    return read, dto


def build_app(fn: Callable[..., Any], dto: Any, direction: Direction) -> Litestar:
    if direction == "in":
        handler: Any = post("/", dto=dto, return_dto=None, sync_to_thread=False)(fn)
    else:
        handler = get("/", return_dto=dto, sync_to_thread=False)(fn)
    return Litestar([handler], openapi_config=None)


def _show(status: int, body: Any) -> str:
    return str(status) if status >= 400 else f"{status} {json.dumps(body, sort_keys=True)}"


def find_gap(feature: Feature, library: Library, direction: Direction, backend: Backend) -> str | None:
    m = maker(library)
    case = feature.build(m)
    fn, dto = prepare_handler(feature, m, case, direction, backend)
    try:
        app = build_app(fn, dto, direction)
    except Exception as exc:
        return f"startup: {type(exc).__name__}: {exc.msg if isinstance(exc, SyntaxError) else exc}"
    gaps: list[str] = []
    with TestClient(app, raise_server_exceptions=False) as client:
        if direction == "out":
            response = client.get("/")
            expected = _show(200, feature.response)
            observed = _show(response.status_code, response.json() if response.status_code < 400 else None)
            if observed != expected:
                gaps.append(f"out: expected {expected}, got {observed}")
        else:
            assert not isinstance(feature.requests, NA)
            for request in feature.requests:
                response = client.post("/", json=request.body)
                expected = _show(request.status, request.received)
                observed = _show(response.status_code, response.json() if response.status_code < 400 else None)
                if observed != expected:
                    gaps.append(f"in {request.label}: expected {expected}, got {observed}")
    return "\n".join(gaps) or None
