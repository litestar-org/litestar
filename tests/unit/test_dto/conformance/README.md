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
library with `na={"py": reason}`; such cells are not collected.
Cells for `py` are skipped when pydantic is not installed.

## Known gaps

`known_gaps.py::KNOWN_GAPS` lists the cells that do not conform yet, with the exact text of the failure:

    "tuple_fixed-dc-out": 'out: expected 200 {...}, got 200 {...}'

The test asserts that the cell still fails with exactly this text and then reports it as `xfail`.
A cell that fails differently, a cell that conforms while it is still listed, and a key that names no
cell all fail the suite.

## Flipping a cell

1. Fix the behaviour.
2. Run the grid. The fixed cells fail with `assert None == '...'`.
3. Delete their entries from `KNOWN_GAPS`. Do not edit the expectation in `features.py` to match the code.

Five entries are not expected to flip: `partial_nested_list-{dc,ms,py}-in` (`DTOData` does not convert the
members of nested collections) and `constraint_partial_length-py-in`, `constraint_partial_number-py-in`
(pydantic does not validate a `DTOData` payload). They record accepted limits, not planned work.

To record a new gap, add the row to `features.py`, run the grid, and copy the text shown on the left of
the failing assertion into `KNOWN_GAPS`; add `-vv` when pytest truncates it.

Test ids end in `-codegen` or `-interp`, the DTO backend the cell ran on. When only one backend fails, or the
two texts differ, key the entry `<cell>@<backend>`; when both fail with the same text, use the bare `<cell>`.
