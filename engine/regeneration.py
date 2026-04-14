from __future__ import annotations

from engine.compliance import Violation


def should_full_rebuild(violations: list[Violation]) -> bool:
    return any(violation.severity == "HARD" for violation in violations)


def describe_violations(violations: list[Violation]) -> str:
    if not violations:
        return "No compliance violations."
    return "\n".join(str(violation) for violation in violations)


def build_regeneration_plan(violations: list[Violation]) -> list[str]:
    plan: list[str] = []
    for violation in violations:
        if violation.constraint_name in {"roof_type", "roof_base_elevation"}:
            plan.append("Rebuild roof module.")
        elif "window_count" in violation.constraint_name or violation.constraint_name == "door_present":
            plan.append("Rebuild facade/openings modules.")
        elif violation.constraint_name in {"garage_enabled", "terrace_enabled", "balcony_enabled"}:
            plan.append("Rebuild optional volume modules.")
        else:
            plan.append("Full rebuild recommended.")
    return sorted(set(plan))
