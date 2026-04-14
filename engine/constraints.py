from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class HardConstraint:
    name: str
    value: Any
    source: str = "gui"
    required: bool = True


@dataclass(slots=True)
class ConstraintGraph:
    values: dict[str, HardConstraint] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def set(
        self,
        name: str,
        value: Any,
        *,
        source: str = "gui",
        required: bool = True,
        replace: bool = True,
    ) -> HardConstraint:
        existing = self.values.get(name)
        if existing and existing.value != value:
            self.warnings.append(
                f"Constraint '{name}' changed from {existing.value!r} "
                f"({existing.source}) to {value!r} ({source})."
            )
        if existing and not replace:
            return existing
        constraint = HardConstraint(name=name, value=value, source=source, required=required)
        self.values[name] = constraint
        return constraint

    def get(self, name: str) -> HardConstraint | None:
        return self.values.get(name)

    def value(self, name: str, default: Any = None) -> Any:
        constraint = self.get(name)
        return constraint.value if constraint else default

    def has(self, name: str) -> bool:
        return name in self.values

    def all_constraints(self) -> list[HardConstraint]:
        return list(self.values.values())
