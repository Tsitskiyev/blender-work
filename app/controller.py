from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from math import isclose
from pathlib import Path

from app.validators import validate_generation_inputs
from engine.compliance import Violation, audit, save_audit
from engine.parser import parse_raw_input, save_raw_input
from engine.regeneration import build_regeneration_plan
from engine.resolver import resolve


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
BLENDER_SCRIPT = PROJECT_ROOT / "blender" / "run_generator.py"
OUTPUT_FILES = {
    "raw_input": OUTPUT_DIR / "raw_input.json",
    "resolved": OUTPUT_DIR / "resolved.json",
    "scene_report": OUTPUT_DIR / "scene_report.json",
    "audit": OUTPUT_DIR / "audit_report.json",
    "blend": OUTPUT_DIR / "scene.blend",
    "glb": OUTPUT_DIR / "scene.glb",
}
AI_PLAN_FILE = OUTPUT_DIR / "ai_design_plan.json"


def _matches_float(left: object, right: object, tolerance: float = 0.02) -> bool:
    try:
        return isclose(float(left), float(right), abs_tol=tolerance)
    except (TypeError, ValueError):
        return False


def _matches_ai_payload(raw_params: dict, payload: dict | None) -> bool:
    if not isinstance(payload, dict):
        return False
    gui = payload.get("gui_parameters")
    if not isinstance(gui, dict):
        return False

    float_keys = ("width", "depth", "floor_height", "roof_pitch")
    exact_keys = (
        "floors",
        "window_count_front",
        "roof_type",
        "window_style",
        "wall_material",
        "entrance_style",
        "has_columns",
        "has_pediment",
        "has_portico",
        "has_garage",
        "has_terrace",
        "has_balcony",
        "has_fence",
        "arch_style",
        "special_notes",
    )
    if any(not _matches_float(raw_params.get(key), gui.get(key)) for key in float_keys):
        return False
    if any(raw_params.get(key) != gui.get(key) for key in exact_keys):
        return False
    return True


def _find_matching_ai_payload(raw_params: dict) -> dict | None:
    if not AI_PLAN_FILE.exists():
        return None
    try:
        payload = json.loads(AI_PLAN_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    gui = payload.get("gui_parameters")
    if not isinstance(gui, dict):
        return None
    return payload if _matches_ai_payload(raw_params, payload) else None


@dataclass(slots=True)
class GenerationResult:
    success: bool = False
    message: str = ""
    blend_path: str = ""
    glb_path: str = ""
    resolved_path: str = ""
    scene_report_path: str = ""
    audit_path: str = ""
    stdout: str = ""
    stderr: str = ""
    violations: list[Violation] = field(default_factory=list)
    parse_notes: list[str] = field(default_factory=list)


def validate_blender_path(path: str) -> tuple[bool, str]:
    if not path:
        return False, "Blender path is empty."

    candidate = Path(path)
    if not candidate.exists():
        return False, f"Blender executable not found: {path}"
    if not candidate.is_file():
        return False, f"Blender path is not a file: {path}"

    file_name = candidate.name.lower()
    if file_name == "blender-launcher.exe" or "launcher" in file_name:
        return False, "Select blender.exe, not blender-launcher.exe."

    try:
        process = subprocess.run(
            [str(candidate), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        return False, "Blender --version timed out."
    except OSError as exc:
        return False, f"Unable to execute Blender: {exc}"

    combined_output = f"{process.stdout}\n{process.stderr}".strip()
    if process.returncode != 0:
        return False, f"Blender --version failed with exit code {process.returncode}."
    if "Blender" not in combined_output:
        return False, "The selected file did not identify itself as Blender."
    return True, combined_output.splitlines()[0]


def _cleanup_previous_outputs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in OUTPUT_FILES.values():
        if path.exists():
            path.unlink()


def _verify_output_file(path: Path, label: str, min_size: int) -> tuple[bool, str]:
    if not path.exists():
        return False, f"{label} was not created."
    if path.stat().st_size < min_size:
        return False, f"{label} looks suspiciously small ({path.stat().st_size} bytes)."
    return True, ""


def run_generation(raw_params: dict, blender_path: str, progress_callback=None) -> GenerationResult:
    result = GenerationResult()
    enriched_params = dict(raw_params)

    def progress(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    validation_errors = validate_generation_inputs(enriched_params)
    if validation_errors:
        result.message = "\n".join(validation_errors)
        return result

    valid_blender, blender_info = validate_blender_path(blender_path)
    if not valid_blender:
        result.message = blender_info
        return result

    _cleanup_previous_outputs()

    attached_payload = enriched_params.get("ai_design_payload")
    if attached_payload is not None and not _matches_ai_payload(enriched_params, attached_payload):
        enriched_params.pop("ai_design_payload", None)
        progress("Dropped stale AI payload because it does not match the current prompt/GUI state.")

    ai_payload = _find_matching_ai_payload(enriched_params)
    if ai_payload:
        enriched_params["ai_design_payload"] = ai_payload
        progress("Attached matching AI space program to generation request.")

    progress("Saving raw input...")
    save_raw_input(enriched_params, OUTPUT_FILES["raw_input"])

    progress("Parsing constraints...")
    graph = parse_raw_input(enriched_params)
    result.parse_notes = list(graph.notes) + list(graph.warnings)

    progress("Resolving final spec...")
    spec = resolve(graph)
    spec.to_json(OUTPUT_FILES["resolved"])
    result.resolved_path = str(OUTPUT_FILES["resolved"])

    progress(f"Blender validated: {blender_info}")
    progress("Launching Blender in background mode...")
    command = [
        blender_path,
        "--background",
        "--python",
        str(BLENDER_SCRIPT),
        "--",
        str(OUTPUT_FILES["resolved"]),
        str(OUTPUT_DIR),
    ]

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        result.message = "Blender generation timed out after 10 minutes."
        return result
    except OSError as exc:
        result.message = f"Failed to launch Blender: {exc}"
        return result

    result.stdout = process.stdout
    result.stderr = process.stderr

    if process.returncode != 0:
        result.message = (
            f"Blender exited with code {process.returncode}.\n"
            f"{process.stderr[-2500:] if process.stderr else process.stdout[-2500:]}"
        )
        return result

    progress("Verifying generated files...")
    for label, min_size in (("blend", 4096), ("glb", 2048), ("scene_report", 128)):
        ok, message = _verify_output_file(OUTPUT_FILES[label], label, min_size)
        if not ok:
            result.message = message
            return result

    report_payload = json.loads(OUTPUT_FILES["scene_report"].read_text(encoding="utf-8"))
    if report_payload.get("status") != "built":
        result.message = "scene_report.json exists, but build status is not 'built'."
        return result

    progress("Running compliance audit...")
    violations = audit(OUTPUT_FILES["resolved"], OUTPUT_FILES["scene_report"])
    save_audit(violations, OUTPUT_FILES["audit"])
    result.violations = violations
    result.blend_path = str(OUTPUT_FILES["blend"])
    result.glb_path = str(OUTPUT_FILES["glb"])
    result.scene_report_path = str(OUTPUT_FILES["scene_report"])
    result.audit_path = str(OUTPUT_FILES["audit"])

    if violations:
        plan = build_regeneration_plan(violations)
        result.message = (
            "Compliance audit failed.\n"
            + "\n".join(str(violation) for violation in violations)
            + ("\nSuggested repair plan:\n" + "\n".join(plan) if plan else "")
        )
        return result

    result.success = True
    result.message = (
        "Generation completed successfully.\n"
        f"Resolved spec: {OUTPUT_FILES['resolved'].name}\n"
        f"Scene: {OUTPUT_FILES['blend'].name}\n"
        f"Export: {OUTPUT_FILES['glb'].name}\n"
        "Compliance: PASS"
    )
    return result
