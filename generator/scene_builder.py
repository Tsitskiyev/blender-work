from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Vector

from engine.specs import ResolvedSpec
from generator.common import (
    apply_bevel_modifier,
    count_tagged_objects,
    ensure_collection,
    first_tagged,
    reset_scene,
)
from generator.entrance import build_entrance
from generator.environment import build_environment
from generator.interior import build_interior
from generator.massing import build_massing
from generator.openings import apply_openings
from generator.props import build_props
from generator.roof import build_roof


def _object_min_z(obj: bpy.types.Object | None) -> float:
    if obj is None:
        return 0.0
    return min((obj.matrix_world @ vertex.co).z for vertex in obj.data.vertices)


def _room_bounds(room) -> tuple[float, float, float, float]:
    return (
        room.center_x - (room.width / 2.0),
        room.center_x + (room.width / 2.0),
        room.center_y - (room.depth / 2.0),
        room.center_y + (room.depth / 2.0),
    )


def _opening_probe(
    shell: bpy.types.Object,
    facade: str,
    center: float,
    bottom: float,
    height: float,
) -> tuple[Vector, Vector]:
    z = bottom + (height / 2.0)
    offset = 0.12
    if facade == "front":
        return Vector((center, float(shell.location.y) - (float(shell.dimensions.y) / 2.0) - offset, z)), Vector((0.0, 1.0, 0.0))
    if facade == "rear":
        return Vector((center, float(shell.location.y) + (float(shell.dimensions.y) / 2.0) + offset, z)), Vector((0.0, -1.0, 0.0))
    if facade == "left":
        return Vector((float(shell.location.x) - (float(shell.dimensions.x) / 2.0) - offset, center, z)), Vector((1.0, 0.0, 0.0))
    return Vector((float(shell.location.x) + (float(shell.dimensions.x) / 2.0) + offset, center, z)), Vector((-1.0, 0.0, 0.0))


def _shell_opening_clear(shell: bpy.types.Object | None, spec: ResolvedSpec, facade: str, center: float, bottom: float, height: float) -> bool:
    if shell is None:
        return False
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated_shell = shell.evaluated_get(depsgraph)
    origin_world, direction_world = _opening_probe(shell, facade, center, bottom, height)
    origin_local = evaluated_shell.matrix_world.inverted() @ origin_world
    direction_local = (evaluated_shell.matrix_world.inverted().to_3x3() @ direction_world).normalized()
    hit, _, _, _ = evaluated_shell.ray_cast(
        origin_local,
        direction_local,
        distance=(spec.wall_thickness + 0.16),
    )
    return not hit


def _opening_penetration_report(spec: ResolvedSpec, structure) -> tuple[int, bool]:
    blocked = 0
    facades = [
        spec.front_facade,
        spec.rear_facade,
        spec.left_facade,
        spec.right_facade,
    ]
    for facade in facades:
        for opening in facade.windows:
            shell = structure.shell_by_floor.get(opening.floor_index, structure.main_shell)
            if not _shell_opening_clear(shell, spec, opening.facade, opening.center, opening.bottom, opening.height):
                blocked += 1
    door = spec.entrance.door
    if not _shell_opening_clear(structure.shell_by_floor.get(0, structure.main_shell), spec, "front", door.center, door.bottom, door.height):
        blocked += 1
    return blocked, blocked == 0


def _room_graph(spec: ResolvedSpec) -> tuple[int, int, bool]:
    rooms = list(spec.room_specs)
    if not rooms:
        return 0, 0, True

    adjacency: dict[str, set[str]] = {room.room_id: set() for room in rooms}
    for index, room in enumerate(rooms):
        ax1, ax2, ay1, ay2 = _room_bounds(room)
        for other in rooms[index + 1 :]:
            if room.floor_index != other.floor_index:
                continue
            bx1, bx2, by1, by2 = _room_bounds(other)
            vertical_touch = abs(ax2 - bx1) < 0.05 or abs(bx2 - ax1) < 0.05
            vertical_overlap = min(ay2, by2) - max(ay1, by1)
            horizontal_touch = abs(ay2 - by1) < 0.05 or abs(by2 - ay1) < 0.05
            horizontal_overlap = min(ax2, bx2) - max(ax1, bx1)
            if vertical_touch and vertical_overlap > 0.6:
                adjacency[room.room_id].add(other.room_id)
                adjacency[other.room_id].add(room.room_id)
            elif horizontal_touch and horizontal_overlap > 0.6:
                adjacency[room.room_id].add(other.room_id)
                adjacency[other.room_id].add(room.room_id)

    def preferred_vertical_room(floor_index: int):
        candidates = [room for room in rooms if room.floor_index == floor_index]
        if not candidates:
            return None
        for zone in ("circulation", "entry", "public", "service", "private"):
            match = next((room for room in candidates if room.zone == zone), None)
            if match is not None:
                return match
        return candidates[0]

    has_vertical_connector = any(feature.kind in {"stair", "stair_landing", "lift"} for feature in spec.feature_specs)
    if has_vertical_connector:
        for floor_index in range(spec.floors - 1):
            lower = preferred_vertical_room(floor_index)
            upper = preferred_vertical_room(floor_index + 1)
            if lower is None or upper is None:
                continue
            adjacency[lower.room_id].add(upper.room_id)
            adjacency[upper.room_id].add(lower.room_id)

    roots = [
        room.room_id
        for room in rooms
        if room.floor_index == 0 and room.zone in {"entry", "circulation", "public"}
    ]
    if not roots:
        roots = [rooms[0].room_id]

    visited: set[str] = set()
    queue = list(roots)
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        queue.extend(sorted(adjacency[current] - visited))

    return len(visited), len(rooms) - len(visited), len(visited) == len(rooms)


def _build_report(spec: ResolvedSpec, structure) -> dict:
    roof_main = first_tagged("roof_main")
    reachable_room_count, isolated_room_count, room_access_pass = _room_graph(spec)
    blocked_opening_count, opening_penetration_pass = _opening_penetration_report(spec, structure)
    return {
        "status": "built",
        "roof_type": roof_main.get("roof_type") if roof_main else "",
        "roof_base_elevation": round(_object_min_z(roof_main), 4) if roof_main else 0.0,
        "floors": spec.floors,
        "shell_width": round(float(spec.width), 4),
        "shell_depth": round(float(spec.depth), 4),
        "wall_height": round(float(spec.wall_height), 4),
        "front_window_count": count_tagged_objects("window_unit", "front"),
        "rear_window_count": count_tagged_objects("window_unit", "rear"),
        "left_window_count": count_tagged_objects("window_unit", "left"),
        "right_window_count": count_tagged_objects("window_unit", "right"),
        "door_present": first_tagged("door") is not None,
        "has_columns": count_tagged_objects("entrance_column") > 0,
        "has_pediment": first_tagged("entrance_pediment") is not None,
        "has_portico": count_tagged_objects("entrance_portico") > 0,
        "garage_enabled": first_tagged("garage_shell") is not None,
        "terrace_enabled": first_tagged("terrace") is not None,
        "balcony_enabled": first_tagged("balcony") is not None,
        "has_fence": count_tagged_objects("fence") > 0,
        "room_count": count_tagged_objects("room_floor"),
        "interior_wall_count": count_tagged_objects("interior_wall"),
        "stair_present": count_tagged_objects("stair") > 0,
        "fireplace_present": first_tagged("fireplace") is not None,
        "lift_present": first_tagged("lift") is not None,
        "skylight_present": first_tagged("skylight") is not None,
        "reachable_room_count": reachable_room_count,
        "isolated_room_count": isolated_room_count,
        "room_access_pass": room_access_pass,
        "blocked_opening_count": blocked_opening_count,
        "opening_penetration_pass": opening_penetration_pass,
        "object_count": len(bpy.data.objects),
    }


def write_scene_report(report: dict, output_path: str | Path) -> None:
    Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")


def build_scene(spec: ResolvedSpec) -> dict:
    reset_scene()

    structure_collection = ensure_collection("Structure")
    openings_collection = ensure_collection("Openings")
    entrance_collection = ensure_collection("Entrance")
    roof_collection = ensure_collection("Roof")
    environment_collection = ensure_collection("Environment")
    props_collection = ensure_collection("Props")

    structure = build_massing(spec, structure_collection)
    apply_openings(spec, structure, openings_collection)
    apply_bevel_modifier(structure.main_shell, 0.012, segments=2)
    apply_bevel_modifier(structure.foundation, 0.01, segments=2)
    if structure.garage_shell is not None:
        apply_bevel_modifier(structure.garage_shell, 0.01, segments=2)
    build_interior(spec, structure, structure_collection)
    build_entrance(spec, entrance_collection)
    build_roof(spec, roof_collection)
    build_environment(spec, environment_collection)
    build_props(spec, props_collection)

    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080
    return _build_report(spec, structure)
