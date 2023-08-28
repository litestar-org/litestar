from typing import Any, Literal, Self

from sqlalchemy import ClauseElement, UpdateBase


class MergeClause(ClauseElement):
    __visit_name__ = "merge_into_clause"

    def __init__(self, command: Literal["INSERT", "UPDATE", "DELETE"]) -> None:
        self._on_sets: dict[Any, Any] = {}
        self.predicate = None
        self.command = command

    def __repr__(self) -> str:
        case_predicate = f" AND {self.predicate!s}" if self.predicate is not None else ""
        if self.command == "INSERT":
            sets, sets_tos = zip(*self._on_sets.items())
            return f'WHEN NOT MATCHED{case_predicate} THEN {self.command} ({", ".join(sets)}) VALUES ({", ".join(map(str, sets_tos))})'

        # WHEN MATCHED clause
        sets = (
            ", ".join([f"{match_set[0]} = {match_set[1]}" for match_set in self._on_sets.items()])
            if self._on_sets
            else ""
        )
        return f'WHEN MATCHED{case_predicate} THEN {self.command}{f" SET {sets!s}" if self._on_sets else ""}'

    def values(self, **kwargs: Any) -> Self:
        self._on_sets = kwargs
        return self

    def where(self, expr: Any) -> Self:
        self.predicate = expr
        return self


class MergeInto(UpdateBase):
    __visit_name__ = "merge_into"
    _bind = None

    def __init__(self, target: Any, source: Any, on: Any) -> None:
        self.target = target
        self.source = source
        self.on = on
        self.clauses: list[ClauseElement] = []

    def __repr__(self) -> str:
        clauses = " ".join([repr(clause) for clause in self.clauses])
        return f"MERGE INTO {self.target} USING {self.source} ON {self.on}" + (f" {clauses}" if clauses else "")

    def when_matched_then_update(self) -> MergeClause:
        clause = MergeClause("UPDATE")
        self.clauses.append(clause)
        return clause

    def when_matched_then_delete(self) -> MergeClause:
        clause = MergeClause("DELETE")
        self.clauses.append(clause)
        return clause

    def when_not_matched_then_insert(self) -> MergeClause:
        clause = MergeClause("INSERT")
        self.clauses.append(clause)
        return clause
