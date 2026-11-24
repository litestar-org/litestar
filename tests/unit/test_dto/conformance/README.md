# DTO conformance grid

Every row of `features.py` describes one DTO feature: a model shape, a `DTOConfig`, the requests to send
and the response to expect. The grid runs each row against dataclasses (`dc`), msgspec structs (`ms`) and
pydantic models (`py`), for request data (`in`) and for returned data (`out`). The expectation is stated
once per row, so the three libraries must behave the same.

## Cells

A cell is `<feature>-<library>-<direction>`, for example `exclude_nested-ms-out`. Run one with:

    pytest tests/unit/test_dto/conformance -k "exclude_nested-ms-out"

- `in`: the handler receives the decoded data and returns a dump of it. A model instance is dumped as
  `{"$model": "<class name>", ...}` with its Python attribute names.
- `out`: the handler returns an instance and the response body is compared.

A row marks a direction as not applicable by passing `NA(reason)` as its `requests` or `response`, and a
library with `na={"py": reason}`; such cells are not collected. A behaviour a library does not share,
such as pydantic not validating a `DTOData` payload, is a `na` entry with the reason, and a limit all
libraries share is the row's expectation. A known defect is an `xfail={"dc": reason}` entry: the cell is
a strict `xfail`, so it fails the suite once the defect is fixed. Cells for `py` are skipped when pydantic
is not installed.

A failing cell reports the difference between the expected and the observed exchange, for example
`assert 'in invalid: expected 400, got 201 {"value": "ab"}' is None`.
