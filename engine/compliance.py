from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from engine.specs import ResolvedSpec


@dataclass(slots=True)
class Violation:
    constraint_name: str
    expected: object
    actual: object
    severity: str = "HARD"

    def __str__(self) -> str:
        return (
            f"[{self.severity}] {self.constraint_name}: "
            f"expected={self.expected!r}, actual={self.actual!r}"
        )


def _approx_equal(expected: float, actual: float, tolerance: float = 0.03) -> bool:
    return abs(expected - actual) <= tolerance


def audit(resolved_path: str | Path, report_path: str | Path) -> list[Violation]:
    spec = ResolvedSpec.from_json(resolved_path)
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    violations: list[Violation] = []

    def check(name: str, expected, actual, *, severity: str = "HARD") -> None:
        if expected != actual:
            violations.append(Violation(name, expected, actual, severity))

    def check_float(name: str, expected: float, actual: float, tolerance: float = 0.03) -> None:
        if not _approx_equal(expected, actual, tolerance):
            violations.append(Violation(name, expected, actual, "HARD"))

    check("status", "built", report.get("status"))
    check("roof_type", spec.roof.roof_type, report.get("roof_type"))
    check("floors", spec.floors, report.get("floors"))
    check("has_columns", spec.entrance.has_columns, report.get("has_columns"))
    check("has_pediment", spec.entrance.has_pediment, report.get("has_pediment"))
    check("has_portico", spec.entrance.has_portico, report.get("has_portico"))
    check("garage_enabled", spec.garage.enabled, report.get("garage_enabled"))
    check("terrace_enabled", spec.terrace.enabled, report.get("terrace_enabled"))
    check("balcony_enabled", spec.balcony.enabled, report.get("balcony_enabled"))
    check("has_fence", spec.environment.fence_enabled, report.get("has_fence"))
    check("door_present", True, report.get("door_present"))
    check("opening_penetration_pass", True, report.get("opening_penetration_pass"))
    check("front_window_count", len(spec.front_facade.windows), report.get("front_window_count"))
    check("rear_window_count", len(spec.rear_facade.windows), report.get("rear_window_count"))
    check("left_window_count", len(spec.left_facade.windows), report.get("left_window_count"))
    check("right_window_count", len(spec.right_facade.windows), report.get("right_window_count"))
    check_float("shell_width", spec.width, float(report.get("shell_width", 0.0)), 0.04)
    check_float("shell_depth", spec.depth, float(report.get("shell_depth", 0.0)), 0.04)
    check_float("wall_height", spec.wall_height, float(report.get("wall_height", 0.0)), 0.04)
    check_float(
        "roof_base_elevation",
        spec.roof.base_elevation,
        float(report.get("roof_base_elevation", 0.0)),
        0.04,
    )
    if spec.room_specs:
        check("room_count", len(spec.room_specs), report.get("room_count"))
        check("room_access_pass", True, report.get("room_access_pass"))
    if any(feature.kind == "stair" for feature in spec.feature_specs):
        check("stair_present", True, report.get("stair_present"))
    if any(feature.kind == "fireplace" for feature in spec.feature_specs):
        check("fireplace_present", True, report.get("fireplace_present"))
    if any(feature.kind == "lift" for feature in spec.feature_specs):
        check("lift_present", True, report.get("lift_present"))
    if any(feature.kind == "skylight" for feature in spec.feature_specs):
        check("skylight_present", True, report.get("skylight_present"))
    return violations


def save_audit(violations: list[Violation], path: str | Path) -> None:
    payload = {
        "pass": not violations,
        "violation_count": len(violations),
        "violations": [
            {
                "constraint": violation.constraint_name,
                "expected": violation.expected,
                "actual": violation.actual,
                "severity": violation.severity,
            }
            for violation in violations
        ],
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
