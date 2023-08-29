from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import ClauseElement, ColumnElement, UpdateBase
from sqlalchemy.ext.compiler import compiles

if TYPE_CHECKING:
    from typing import Literal, Self

    from sqlalchemy.sql.compiler import StrSQLCompiler


class MergeClause(ClauseElement):
    __visit_name__ = "merge_into_clause"

    def __init__(self, command: Literal["INSERT", "UPDATE", "DELETE"]) -> None:
        self.on_sets: dict[str, ColumnElement[Any]] = {}
        self.predicate: ColumnElement[bool] | None = None
        self.command = command

    def values(self, **kwargs: ColumnElement[Any]) -> Self:
        self.on_sets = kwargs
        return self

    def where(self, expr: ColumnElement[bool]) -> Self:
        self.predicate = expr
        return self


@compiles(MergeClause)  # type: ignore[no-untyped-call, misc]
def visit_merge_into_clause(element: MergeClause, compiler: StrSQLCompiler, **kw: Any) -> str:
    case_predicate = ""
    if element.predicate is not None:
        case_predicate = f" AND {element.predicate._compiler_dispatch(compiler, **kw)!s}"

    if element.command == "INSERT":
        sets, sets_tos = list(element.on_sets), list(element.on_sets.values())
        if kw.get("deterministic", False):
            sorted_on_sets = dict(sorted(element.on_sets.items(), key=lambda x: x[0]))
            sets, sets_tos = list(sorted_on_sets), list(sorted_on_sets.values())

        merge_insert = ", ".join(sets)
        values = ", ".join(e._compiler_dispatch(compiler, **kw) for e in sets_tos)
        return f"WHEN NOT MATCHED{case_predicate} THEN {element.command} ({merge_insert}) VALUES ({values})"

    set_list = list(element.on_sets.items())
    if kw.get("deterministic", False):
        set_list.sort(key=lambda x: x[0])

    # merge update or merge delete
    merge_action = ""
    values = ""

    if element.on_sets:
        values = ", ".join(f"{name} = {column._compiler_dispatch(compiler, **kw)}" for name, column in set_list)
        merge_action = f" SET {values}"

    return f"WHEN MATCHED{case_predicate} THEN {element.command}{merge_action}"


class MergeInto(UpdateBase):
    __visit_name__ = "merge_into"
    _bind = None
    inherit_cache = True

    def __init__(self, target: Any, source: Any, on: Any) -> None:
        self.target = target
        self.source = source
        self.on = on
        self.clauses: list[ClauseElement] = []

    def when_matched_then_update(self) -> MergeClause:
        self.clauses.append(clause := MergeClause("UPDATE"))
        return clause

    def when_matched_then_delete(self) -> MergeClause:
        self.clauses.append(clause := MergeClause("DELETE"))
        return clause

    def when_not_matched_then_insert(self) -> MergeClause:
        self.clauses.append(clause := MergeClause("INSERT"))
        return clause


@compiles(MergeInto)  # type: ignore[no-untyped-call, misc]
def visit_merge_into(element: MergeInto, compiler: StrSQLCompiler, **kw: Any) -> str:
    clauses = " ".join(clause._compiler_dispatch(compiler, **kw) for clause in element.clauses)
    sql_text = f"MERGE INTO {element.target} USING {element.source} ON {element.on}"

    if clauses:
        sql_text += f" {clauses}"

    return sql_text
