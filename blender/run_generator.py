from __future__ import annotations

import os
import sys
from pathlib import Path

import bpy


def _parse_args() -> tuple[Path, Path]:
    if "--" not in sys.argv:
        raise RuntimeError("Expected: blender --background --python run_generator.py -- <resolved.json> <output_dir>")
    arguments = sys.argv[sys.argv.index("--") + 1 :]
    if len(arguments) != 2:
        raise RuntimeError("Expected exactly 2 arguments: <resolved.json> <output_dir>")
    return Path(arguments[0]).resolve(), Path(arguments[1]).resolve()


def main() -> None:
    resolved_path, output_dir = _parse_args()
    project_root = resolved_path.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from engine.specs import ResolvedSpec
    from generator.scene_builder import build_scene, write_scene_report

    output_dir.mkdir(parents=True, exist_ok=True)
    spec = ResolvedSpec.from_json(resolved_path)

    print(f"[Generator] Loaded resolved spec: {resolved_path}")
    report = build_scene(spec)

    scene_report_path = output_dir / "scene_report.json"
    write_scene_report(report, scene_report_path)
    print(f"[Generator] Wrote scene report: {scene_report_path}")

    blend_path = output_dir / "scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"[Generator] Saved blend file: {blend_path}")

    glb_path = output_dir / "scene.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        export_apply=True,
    )
    print(f"[Generator] Exported glb file: {glb_path}")


if __name__ == "__main__":
    main()
