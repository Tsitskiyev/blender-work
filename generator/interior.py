from __future__ import annotations

from collections import defaultdict

import bpy

from engine.specs import FeatureSpec, ResolvedSpec, RoomSpec
from generator.common import StructureState, add_box, apply_boolean_difference, tag_object
from generator.materials import cedar_material, foundation_material, glass_material, metal_material, oak_material, room_floor_material, wall_material


def _segment_key(orientation: str, fixed: float, start: float, end: float) -> tuple[str, float, float, float]:
    return (orientation, round(fixed, 4), round(min(start, end), 4), round(max(start, end), 4))


def _room_bounds(room: RoomSpec) -> tuple[float, float, float, float]:
    half_w = room.width / 2.0
    half_d = room.depth / 2.0
    return (
        round(room.center_x - half_w, 4),
        round(room.center_x + half_w, 4),
        round(room.center_y - half_d, 4),
        round(room.center_y + half_d, 4),
    )


def _build_room_floor(room: RoomSpec, collection: bpy.types.Collection, slab_top: float) -> None:
    floor = add_box(
        f"RoomFloor_{room.room_id}",
        (max(0.1, room.width - 0.04), max(0.1, room.depth - 0.04), 0.025),
        (room.center_x, room.center_y, slab_top + 0.0125),
        collection,
        cedar_material() if room.finish == "cedar" or room.zone == "sauna" else room_floor_material(room.zone),
    )
    tag_object(floor, asset_type="room_floor", room_id=room.room_id, floor_index=room.floor_index)


def _should_skip_segment(
    orientation: str,
    fixed: float,
    start: float,
    end: float,
    interior_width: float,
    interior_depth: float,
    *,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
) -> bool:
    half_w = round(interior_width / 2.0, 4)
    half_d = round(interior_depth / 2.0, 4)
    if orientation == "v" and (abs(fixed - (offset_x - half_w)) < 0.03 or abs(fixed - (offset_x + half_w)) < 0.03):
        return True
    if orientation == "h" and (abs(fixed - (offset_y - half_d)) < 0.03 or abs(fixed - (offset_y + half_d)) < 0.03):
        return True
    if end - start < 0.2:
        return True
    return False


def _wall_piece(
    orientation: str,
    fixed: float,
    start: float,
    end: float,
    z_center: float,
    thickness: float,
    height: float,
    name: str,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    length = max(0.1, end - start)
    if orientation == "v":
        location = (fixed, (start + end) / 2.0, z_center)
        size = (thickness, length, height)
    else:
        location = ((start + end) / 2.0, fixed, z_center)
        size = (length, thickness, height)
    wall = add_box(name, size, location, collection, wall_material("stucco"))
    tag_object(wall, asset_type="interior_wall")
    return wall


def _build_partitions(
    rooms: list[RoomSpec],
    spec: ResolvedSpec,
    collection: bpy.types.Collection,
) -> None:
    segments: dict[int, dict[tuple[str, float, float, float], list[RoomSpec]]] = defaultdict(lambda: defaultdict(list))
    for room in rooms:
        x1, x2, y1, y2 = _room_bounds(room)
        segments[room.floor_index][_segment_key("v", x1, y1, y2)].append(room)
        segments[room.floor_index][_segment_key("v", x2, y1, y2)].append(room)
        segments[room.floor_index][_segment_key("h", y1, x1, x2)].append(room)
        segments[room.floor_index][_segment_key("h", y2, x1, x2)].append(room)

    interior_width = spec.width - (spec.wall_thickness * 2.0)
    interior_depth = spec.depth - (spec.wall_thickness * 2.0)
    for floor_index, floor_segments in segments.items():
        height = spec.floor_height - 0.22
        z_center = (floor_index * spec.floor_height) + (height / 2.0) + spec.floor_slab_thickness
        offset_x = float(spec.design_options.get("upper_shift_x", 0.0)) if spec.design_profile == "cubism" and floor_index >= 1 else 0.0
        for (orientation, fixed, start, end), owners in floor_segments.items():
            if _should_skip_segment(
                orientation,
                fixed,
                start,
                end,
                interior_width,
                interior_depth,
                offset_x=offset_x,
            ):
                continue
            gap = 0.0 if len(owners) <= 1 else 1.05
            if gap > 0.0 and end - start > gap + 0.45:
                midpoint = (start + end) / 2.0
                _wall_piece(
                    orientation,
                    fixed,
                    start,
                    midpoint - (gap / 2.0),
                    z_center,
                    0.12,
                    height,
                    f"Partition_{floor_index}_{orientation}_{fixed}_{start}_A",
                    collection,
                )
                _wall_piece(
                    orientation,
                    fixed,
                    midpoint + (gap / 2.0),
                    end,
                    z_center,
                    0.12,
                    height,
                    f"Partition_{floor_index}_{orientation}_{fixed}_{start}_B",
                    collection,
                )
            else:
                _wall_piece(
                    orientation,
                    fixed,
                    start,
                    end,
                    z_center,
                    0.12,
                    height,
                    f"Partition_{floor_index}_{orientation}_{fixed}_{start}",
                    collection,
                )


def _build_fireplace(feature: FeatureSpec, collection: bpy.types.Collection) -> None:
    body = add_box(
        "Fireplace",
        (feature.width, feature.depth, feature.height),
        (feature.center_x, feature.center_y, feature.height / 2.0 + 0.18),
        collection,
        foundation_material(),
    )
    tag_object(body, asset_type="fireplace")


def _build_lift(feature: FeatureSpec, collection: bpy.types.Collection) -> None:
    shaft = bpy.ops.mesh.primitive_cylinder_add
    shaft(
        vertices=40,
        radius=feature.width / 2.0,
        depth=feature.height,
        location=(feature.center_x, feature.center_y, feature.height / 2.0),
    )
    glass = bpy.context.object
    glass.name = "LiftShaft"
    if collection not in glass.users_collection:
        collection.objects.link(glass)
    for current in list(glass.users_collection):
        if current != collection:
            current.objects.unlink(glass)
    if glass.data.materials:
        glass.data.materials[0] = glass_material()
    else:
        glass.data.materials.append(glass_material())
    tag_object(glass, asset_type="lift")

    cabin = add_box(
        "LiftCabin",
        (feature.width * 0.72, feature.depth * 0.72, 2.3),
        (feature.center_x, feature.center_y, 1.4),
        collection,
        glass_material(),
    )
    tag_object(cabin, asset_type="lift")


def _cut_horizontal_element(
    target: bpy.types.Object | None,
    name: str,
    width: float,
    depth: float,
    center_x: float,
    center_y: float,
    collection: bpy.types.Collection,
) -> None:
    if target is None:
        return
    cutter = add_box(
        name,
        (
            width,
            depth,
            max(0.14, float(target.dimensions.z) + 0.14),
        ),
        (
            center_x,
            center_y,
            float(target.location.z),
        ),
        collection,
        None,
    )
    apply_boolean_difference(target, cutter)


def _build_skylight(feature: FeatureSpec, structure: StructureState, collection: bpy.types.Collection) -> None:
    if len(structure.floor_slabs) < 2:
        return
    _cut_horizontal_element(
        structure.floor_slabs[-1],
        "SkylightCut_Floor",
        feature.width + 0.06,
        feature.depth + 0.06,
        feature.center_x,
        feature.center_y,
        collection,
    )
    _cut_horizontal_element(
        structure.roof_plate,
        "SkylightCut_RoofPlate",
        feature.width + 0.08,
        feature.depth + 0.08,
        feature.center_x,
        feature.center_y,
        collection,
    )

    guard_height = 1.02
    guard_thickness = 0.035
    segments = [
        (
            "SkylightGuard_Front",
            (feature.width + 0.08, guard_thickness, guard_height),
            (
                feature.center_x,
                feature.center_y - (feature.depth / 2.0) - (guard_thickness / 2.0),
                float(structure.floor_slabs[-1].location.z) + (guard_height / 2.0),
            ),
        ),
        (
            "SkylightGuard_Rear",
            (feature.width + 0.08, guard_thickness, guard_height),
            (
                feature.center_x,
                feature.center_y + (feature.depth / 2.0) + (guard_thickness / 2.0),
                float(structure.floor_slabs[-1].location.z) + (guard_height / 2.0),
            ),
        ),
        (
            "SkylightGuard_Left",
            (guard_thickness, feature.depth + 0.08, guard_height),
            (
                feature.center_x - (feature.width / 2.0) - (guard_thickness / 2.0),
                feature.center_y,
                float(structure.floor_slabs[-1].location.z) + (guard_height / 2.0),
            ),
        ),
        (
            "SkylightGuard_Right",
            (guard_thickness, feature.depth + 0.08, guard_height),
            (
                feature.center_x + (feature.width / 2.0) + (guard_thickness / 2.0),
                feature.center_y,
                float(structure.floor_slabs[-1].location.z) + (guard_height / 2.0),
            ),
        ),
    ]
    for name, size, location in segments:
        guard = add_box(name, size, location, collection, glass_material())
        tag_object(guard, asset_type="skylight")


def _build_stair(
    feature: FeatureSpec,
    structure: StructureState,
    collection: bpy.types.Collection,
    spec: ResolvedSpec,
) -> None:
    tread_count_per_run = 10
    riser = (feature.height / 2.0) / tread_count_per_run
    tread = 0.30
    run_width = feature.width
    lower_y_start = feature.center_y - (feature.depth / 2.0) + (tread / 2.0)
    run_x = feature.center_x - (run_width / 2.0)
    step_material = metal_material() if spec.design_profile == "cubism" else oak_material()
    landing_material = glass_material() if spec.design_profile == "cubism" else oak_material()

    for index in range(tread_count_per_run):
        step = add_box(
            f"StairStep_Lower_{index}",
            (run_width, tread, 0.05),
            (
                feature.center_x,
                lower_y_start + (index * tread),
                0.18 + ((index + 1) * riser),
            ),
            collection,
            step_material,
        )
        tag_object(step, asset_type="stair")

    landing_height = 0.18 + (tread_count_per_run * riser)
    landing_size = run_width
    landing = add_box(
        "StairLanding",
        (landing_size, landing_size, 0.06),
        (
            feature.center_x,
            feature.center_y - (feature.depth / 2.0) + (tread_count_per_run * tread) + (landing_size / 2.0),
            landing_height + 0.03,
        ),
        collection,
        landing_material,
    )
    tag_object(landing, asset_type="stair")

    upper_x_start = feature.center_x + (run_width / 2.0) - (tread / 2.0)
    upper_y = landing.location.y
    for index in range(tread_count_per_run):
        step = add_box(
            f"StairStep_Upper_{index}",
            (tread, run_width, 0.05),
            (
                upper_x_start - (index * tread),
                upper_y,
                landing_height + ((index + 1) * riser),
            ),
            collection,
            step_material,
        )
        tag_object(step, asset_type="stair")

    for side in (-1.0, 1.0):
        rail = add_box(
            f"StairRail_{'L' if side < 0 else 'R'}",
            (0.04, feature.depth * 0.55, 0.9),
            (
                feature.center_x + side * ((run_width / 2.0) + 0.08),
                feature.center_y - 0.35,
                landing_height * 0.6,
            ),
            collection,
            metal_material(),
        )
        tag_object(rail, asset_type="stair")

    if len(structure.floor_slabs) > 1:
        _cut_horizontal_element(
            structure.floor_slabs[1],
            "StairVoidCut",
            feature.width + 0.45,
            feature.depth + 0.55,
            feature.center_x,
            feature.center_y,
            collection,
        )


def _build_feature(
    feature: FeatureSpec,
    structure: StructureState,
    collection: bpy.types.Collection,
    spec: ResolvedSpec,
) -> None:
    if feature.kind == "fireplace":
        _build_fireplace(feature, collection)
    elif feature.kind == "stair":
        _build_stair(feature, structure, collection, spec)
    elif feature.kind == "stair_landing":
        landing = add_box(
            "UpperLanding",
            (feature.width, feature.depth, feature.height),
            (
                feature.center_x,
                feature.center_y,
                (feature.floor_index * spec.floor_height) + spec.floor_slab_thickness + (feature.height / 2.0),
            ),
            collection,
            glass_material() if spec.design_profile == "cubism" else oak_material(),
        )
        tag_object(landing, asset_type="stair")
    elif feature.kind == "lift":
        _build_lift(feature, collection)
        cut_width = feature.width + 0.18
        cut_depth = feature.depth + 0.18
        for index, slab in enumerate(structure.floor_slabs):
            if index == 0:
                continue
            _cut_horizontal_element(
                slab,
                f"LiftVoidCut_Slab_{index}",
                cut_width,
                cut_depth,
                feature.center_x,
                feature.center_y,
                collection,
            )
        _cut_horizontal_element(
            structure.roof_plate,
            "LiftVoidCut_RoofPlate",
            cut_width,
            cut_depth,
            feature.center_x,
            feature.center_y,
            collection,
        )
        if structure.lower_roof_deck is not None:
            _cut_horizontal_element(
                structure.lower_roof_deck,
                "LiftVoidCut_LowerDeck",
                cut_width,
                cut_depth,
                feature.center_x,
                feature.center_y,
                collection,
            )
    elif feature.kind == "skylight":
        _build_skylight(feature, structure, collection)


def build_interior(
    spec: ResolvedSpec,
    structure: StructureState,
    collection: bpy.types.Collection,
) -> None:
    if not spec.room_specs:
        return

    for room in spec.room_specs:
        slab_top = (room.floor_index * spec.floor_height) + spec.floor_slab_thickness
        _build_room_floor(room, collection, slab_top)

    _build_partitions(spec.room_specs, spec, collection)

    for feature in spec.feature_specs:
        _build_feature(feature, structure, collection, spec)
