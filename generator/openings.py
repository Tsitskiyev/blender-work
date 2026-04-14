from __future__ import annotations

import bpy

from engine.specs import DoorSpec, OpeningSpec, ResolvedSpec
from generator.common import (
    StructureState,
    add_box,
    apply_boolean_difference,
    create_empty,
    parent_keep_world,
    tag_object,
    tagged_objects,
)
from generator.facade import opening_size
from generator.materials import door_material, frame_material, glass_material, metal_material, trim_material


def _shell_for_floor(structure: StructureState, floor_index: int) -> bpy.types.Object:
    return structure.shell_by_floor.get(floor_index, structure.main_shell)


def _opening_location_on_shell(
    shell: bpy.types.Object,
    facade: str,
    center: float,
    bottom: float,
    height: float,
    *,
    inset: float = 0.0,
) -> tuple[float, float, float]:
    z = bottom + (height / 2.0)
    if facade == "front":
        return (center, float(shell.location.y) - (float(shell.dimensions.y) / 2.0) + inset, z)
    if facade == "rear":
        return (center, float(shell.location.y) + (float(shell.dimensions.y) / 2.0) - inset, z)
    if facade == "left":
        return (float(shell.location.x) - (float(shell.dimensions.x) / 2.0) + inset, center, z)
    return (float(shell.location.x) + (float(shell.dimensions.x) / 2.0) - inset, center, z)


def _cut_targets(floor_index: int):
    for target in tagged_objects("facade_panel"):
        if int(target.get("floor_index", floor_index)) == floor_index:
            yield target
    for target in tagged_objects("upper_cladding"):
        yield target


def _cut_opening(
    shell: bpy.types.Object,
    spec: ResolvedSpec,
    opening: OpeningSpec,
    collection: bpy.types.Collection,
    name: str,
) -> None:
    depth = max((spec.wall_thickness * 2.0) + 0.12, 0.30)
    cutter = add_box(
        name,
        opening_size(spec, opening.facade, opening.width + 0.02, opening.height + 0.02, depth),
        _opening_location_on_shell(
            shell,
            opening.facade,
            opening.center,
            opening.bottom,
            opening.height,
            inset=spec.wall_thickness / 2.0,
        ),
        collection,
        None,
    )
    apply_boolean_difference(shell, cutter)
    for target in _cut_targets(opening.floor_index):
        apply_boolean_difference(target, cutter)


def _frame_depth(spec: ResolvedSpec, opening: OpeningSpec) -> float:
    if spec.design_profile == "suburban":
        return min(0.16, spec.wall_thickness * 0.62)
    if opening.frame_style == "frameless":
        return min(0.05, spec.wall_thickness * 0.24)
    if opening.frame_style == "slit":
        return min(0.06, spec.wall_thickness * 0.28)
    return min(0.12, spec.wall_thickness * 0.52)


def _assembly_inset(spec: ResolvedSpec, opening: OpeningSpec) -> float:
    if spec.design_profile == "suburban":
        return min(0.20, max(0.12, spec.wall_thickness * 0.50))
    if opening.frame_style == "frameless":
        return min(0.06, max(0.02, spec.wall_thickness * 0.20))
    return min(0.18, max(0.10, spec.wall_thickness * 0.46))


def _window_profile(spec: ResolvedSpec, opening: OpeningSpec) -> float:
    if opening.frame_style == "frameless":
        return 0.025
    if opening.frame_style == "slit":
        return 0.03
    if spec.window_style == "classic":
        return 0.08
    if spec.window_style == "square":
        return 0.07
    return 0.06


def _build_window_unit(
    spec: ResolvedSpec,
    opening: OpeningSpec,
    shell: bpy.types.Object,
    collection: bpy.types.Collection,
) -> None:
    profile = _window_profile(spec, opening)
    frame_depth = _frame_depth(spec, opening)
    glass_depth = max(0.02, frame_depth * 0.60 if opening.frame_style == "frameless" else frame_depth * 0.35)
    glass_style = str(spec.design_options.get("glass_tint", "clear")) if spec.design_profile == "cubism" else "clear"
    joinery_material = trim_material(spec.design_profile) if spec.design_options.get("window_trim") or spec.design_profile == "suburban" else frame_material()
    mullion_material = trim_material(spec.design_profile) if spec.design_options.get("window_grids") or spec.design_profile == "suburban" else metal_material()
    base_location = _opening_location_on_shell(
        shell,
        opening.facade,
        opening.center,
        opening.bottom,
        opening.height,
        inset=_assembly_inset(spec, opening),
    )
    parent = create_empty(f"Window_{opening.opening_id}", base_location, collection)
    tag_object(parent, asset_type="window_unit", facade=opening.facade, floor_index=opening.floor_index)

    def place(size: tuple[float, float, float], offset: tuple[float, float, float], name: str, material):
        world = (
            base_location[0] + offset[0],
            base_location[1] + offset[1],
            base_location[2] + offset[2],
        )
        obj = add_box(name, size, world, collection, material)
        parent_keep_world(obj, parent)
        return obj

    if opening.facade in {"front", "rear"}:
        sign = 1.0 if opening.facade == "front" else -1.0
        reveal_depth = max(frame_depth + 0.03, min(spec.wall_thickness * 0.68, frame_depth + 0.09))
        reveal_offset = sign * ((reveal_depth - frame_depth) / 2.0)
        glass = place(
            (
                max(0.05, opening.width - (profile * (0.8 if opening.frame_style == "frameless" else 2.0))),
                glass_depth,
                max(0.05, opening.height - (profile * (0.8 if opening.frame_style == "frameless" else 2.0))),
            ),
            (0.0, sign * (reveal_depth * 0.22), 0.0),
            f"{parent.name}_Glass",
            glass_material(glass_style),
        )
        tag_object(glass, asset_type="window_glass")

        if opening.frame_style == "frameless":
            for side, x in (("L", -1.0), ("R", 1.0)):
                fin = place(
                    (profile, frame_depth, opening.height),
                    (x * ((opening.width - profile) / 2.0), 0.0, 0.0),
                    f"{parent.name}_Fin_{side}",
                    mullion_material,
                )
                tag_object(fin, asset_type="window_frame")
            return

        place((opening.width, frame_depth, profile), (0.0, 0.0, (opening.height - profile) / 2.0), f"{parent.name}_Top", joinery_material)
        place((opening.width, frame_depth, profile), (0.0, 0.0, -(opening.height - profile) / 2.0), f"{parent.name}_Bottom", joinery_material)
        place((profile, frame_depth, opening.height), (-(opening.width - profile) / 2.0, 0.0, 0.0), f"{parent.name}_Left", joinery_material)
        place((profile, frame_depth, opening.height), ((opening.width - profile) / 2.0, 0.0, 0.0), f"{parent.name}_Right", joinery_material)
        place((opening.width - (profile * 0.8), reveal_depth, profile * 0.65), (0.0, reveal_offset, (opening.height - profile * 0.65) / 2.0), f"{parent.name}_RevealTop", joinery_material)
        place((opening.width - (profile * 0.8), reveal_depth, profile * 0.65), (0.0, reveal_offset, -(opening.height - profile * 0.65) / 2.0), f"{parent.name}_RevealBottom", joinery_material)
        place((profile * 0.65, reveal_depth, opening.height - (profile * 0.6)), (-(opening.width - profile * 0.65) / 2.0, reveal_offset, 0.0), f"{parent.name}_RevealLeft", joinery_material)
        place((profile * 0.65, reveal_depth, opening.height - (profile * 0.6)), ((opening.width - profile * 0.65) / 2.0, reveal_offset, 0.0), f"{parent.name}_RevealRight", joinery_material)

        if opening.frame_style != "slit" and spec.window_style != "square":
            mullion_width = 0.04 if spec.window_style == "modern" else 0.05
            mullion_count = max(0, int(opening.mullion_count))
            if mullion_count > 1:
                mullion_positions = [
                    (-(opening.width - (profile * 2.0)) / 2.0) + ((opening.width - (profile * 2.0)) / mullion_count) * index
                    for index in range(1, mullion_count)
                ]
                for index, mullion_x in enumerate(mullion_positions):
                    place(
                        (mullion_width, frame_depth, opening.height - (profile * 2.0)),
                        (mullion_x, 0.0, 0.0),
                        f"{parent.name}_Mullion_{index}",
                        mullion_material,
                    )
            if spec.design_profile == "suburban" or spec.design_options.get("window_grids"):
                place(
                    (opening.width - (profile * 2.0), frame_depth, 0.05),
                    (0.0, 0.0, 0.0),
                    f"{parent.name}_MidRail",
                    mullion_material,
                )
        if spec.design_profile == "suburban" or spec.design_options.get("window_trim"):
            outer_depth = 0.05
            outer_y = sign * ((frame_depth / 2.0) + (outer_depth / 2.0) + 0.01)
            place((opening.width + 0.16, outer_depth, 0.08), (0.0, outer_y, (opening.height / 2.0) + 0.04), f"{parent.name}_TrimTop", joinery_material)
            place((0.08, outer_depth, opening.height + 0.16), (-(opening.width / 2.0) - 0.04, outer_y, 0.0), f"{parent.name}_TrimLeft", joinery_material)
            place((0.08, outer_depth, opening.height + 0.16), ((opening.width / 2.0) + 0.04, outer_y, 0.0), f"{parent.name}_TrimRight", joinery_material)
        return

    sign = 1.0 if opening.facade == "left" else -1.0
    reveal_depth = max(frame_depth + 0.03, min(spec.wall_thickness * 0.68, frame_depth + 0.09))
    reveal_offset = sign * ((reveal_depth - frame_depth) / 2.0)
    glass = place(
        (
            glass_depth,
            max(0.05, opening.width - (profile * (0.8 if opening.frame_style == "frameless" else 2.0))),
            max(0.05, opening.height - (profile * (0.8 if opening.frame_style == "frameless" else 2.0))),
        ),
        (sign * (reveal_depth * 0.22), 0.0, 0.0),
        f"{parent.name}_Glass",
        glass_material(glass_style),
    )
    tag_object(glass, asset_type="window_glass")

    if opening.frame_style == "frameless":
        for side, y in (("B", -1.0), ("T", 1.0)):
            fin = place(
                (frame_depth, profile, opening.height),
                (0.0, y * ((opening.width - profile) / 2.0), 0.0),
                f"{parent.name}_Fin_{side}",
                mullion_material,
            )
            tag_object(fin, asset_type="window_frame")
        return

    place((frame_depth, opening.width, profile), (0.0, 0.0, (opening.height - profile) / 2.0), f"{parent.name}_Top", joinery_material)
    place((frame_depth, opening.width, profile), (0.0, 0.0, -(opening.height - profile) / 2.0), f"{parent.name}_Bottom", joinery_material)
    place((frame_depth, profile, opening.height), (0.0, -(opening.width - profile) / 2.0, 0.0), f"{parent.name}_Left", joinery_material)
    place((frame_depth, profile, opening.height), (0.0, (opening.width - profile) / 2.0, 0.0), f"{parent.name}_Right", joinery_material)
    place((reveal_depth, opening.width - (profile * 0.8), profile * 0.65), (reveal_offset, 0.0, (opening.height - profile * 0.65) / 2.0), f"{parent.name}_RevealTop", joinery_material)
    place((reveal_depth, opening.width - (profile * 0.8), profile * 0.65), (reveal_offset, 0.0, -(opening.height - profile * 0.65) / 2.0), f"{parent.name}_RevealBottom", joinery_material)
    place((reveal_depth, profile * 0.65, opening.height - (profile * 0.6)), (reveal_offset, -(opening.width - profile * 0.65) / 2.0, 0.0), f"{parent.name}_RevealLeft", joinery_material)
    place((reveal_depth, profile * 0.65, opening.height - (profile * 0.6)), (reveal_offset, (opening.width - profile * 0.65) / 2.0, 0.0), f"{parent.name}_RevealRight", joinery_material)

    if opening.frame_style != "slit" and spec.window_style != "square":
        mullion_width = 0.04 if spec.window_style == "modern" else 0.05
        mullion_count = max(0, int(opening.mullion_count))
        if mullion_count > 1:
            mullion_positions = [
                (-(opening.width - (profile * 2.0)) / 2.0) + ((opening.width - (profile * 2.0)) / mullion_count) * index
                for index in range(1, mullion_count)
            ]
            for index, mullion_y in enumerate(mullion_positions):
                place(
                    (frame_depth, mullion_width, opening.height - (profile * 2.0)),
                    (0.0, mullion_y, 0.0),
                    f"{parent.name}_Mullion_{index}",
                    mullion_material,
                )
        if spec.design_profile == "suburban" or spec.design_options.get("window_grids"):
            place(
                (frame_depth, opening.width - (profile * 2.0), 0.05),
                (0.0, 0.0, 0.0),
                f"{parent.name}_MidRail",
                mullion_material,
            )
    if spec.design_profile == "suburban" or spec.design_options.get("window_trim"):
        outer_depth = 0.05
        outer_x = sign * ((frame_depth / 2.0) + (outer_depth / 2.0) + 0.01)
        place((outer_depth, opening.width + 0.16, 0.08), (outer_x, 0.0, (opening.height / 2.0) + 0.04), f"{parent.name}_TrimTop", joinery_material)
        place((outer_depth, 0.08, opening.height + 0.16), (outer_x, -(opening.width / 2.0) - 0.04, 0.0), f"{parent.name}_TrimLeft", joinery_material)
        place((outer_depth, 0.08, opening.height + 0.16), (outer_x, (opening.width / 2.0) + 0.04, 0.0), f"{parent.name}_TrimRight", joinery_material)


def _build_door(
    spec: ResolvedSpec,
    door: DoorSpec,
    shell: bpy.types.Object,
    collection: bpy.types.Collection,
) -> None:
    frame_depth = min(0.14, spec.wall_thickness * 0.65)
    profile = 0.07 if door.style == "modern" else 0.09
    joinery_material = trim_material(spec.design_profile) if spec.design_profile == "suburban" else frame_material()
    location = _opening_location_on_shell(
        shell,
        "front",
        door.center,
        door.bottom,
        door.height,
        inset=min(0.18, max(0.10, spec.wall_thickness * 0.48)),
    )
    parent = create_empty("FrontDoor", location, collection)
    tag_object(parent, asset_type="door", facade="front")

    def place(size: tuple[float, float, float], offset: tuple[float, float, float], name: str, material):
        world = (
            location[0] + offset[0],
            location[1] + offset[1],
            location[2] + offset[2],
        )
        obj = add_box(name, size, world, collection, material)
        parent_keep_world(obj, parent)
        return obj

    panel = place(
        (door.width - 0.05, 0.05, door.height - 0.04),
        (0.0, frame_depth * 0.22, 0.0),
        "FrontDoor_Panel",
        trim_material(spec.design_profile) if spec.design_profile == "cabin" else door_material(door.style),
    )
    tag_object(panel, asset_type="door_panel")
    place((door.width, frame_depth, profile), (0.0, 0.0, (door.height - profile) / 2.0), "FrontDoor_Top", joinery_material)
    place((profile, frame_depth, door.height), (-(door.width - profile) / 2.0, 0.0, 0.0), "FrontDoor_Left", joinery_material)
    place((profile, frame_depth, door.height), ((door.width - profile) / 2.0, 0.0, 0.0), "FrontDoor_Right", joinery_material)
    reveal_depth = max(frame_depth + 0.03, min(spec.wall_thickness * 0.70, frame_depth + 0.10))
    reveal_offset = (reveal_depth - frame_depth) / 2.0
    place((door.width - (profile * 0.8), reveal_depth, profile * 0.65), (0.0, reveal_offset, (door.height - profile * 0.65) / 2.0), "FrontDoor_RevealTop", joinery_material)
    place((profile * 0.65, reveal_depth, door.height - 0.02), (-(door.width - profile * 0.65) / 2.0, reveal_offset, 0.0), "FrontDoor_RevealLeft", joinery_material)
    place((profile * 0.65, reveal_depth, door.height - 0.02), ((door.width - profile * 0.65) / 2.0, reveal_offset, 0.0), "FrontDoor_RevealRight", joinery_material)

    if spec.design_options.get("door_six_lites") and door.style == "classic":
        glass_height = door.height * 0.46
        glass_bottom_offset = (door.height * 0.22)
        glass = place(
            (door.width * 0.60, 0.028, glass_height),
            (0.0, 0.038, glass_bottom_offset),
            "FrontDoor_Glass",
            glass_material(),
        )
        tag_object(glass, asset_type="door_glass")
        lite_width = 0.028
        for index, x in enumerate((-door.width * 0.18, 0.0, door.width * 0.18)):
            mullion = place((lite_width, 0.03, glass_height - 0.04), (x, 0.04, glass_bottom_offset), f"FrontDoor_Mullion_{index}", joinery_material)
            tag_object(mullion, asset_type="door_frame")
        rail = place((door.width * 0.60, 0.03, 0.03), (0.0, 0.04, glass_bottom_offset), "FrontDoor_MidRail", joinery_material)
        tag_object(rail, asset_type="door_frame")
    elif spec.design_profile == "cabin" and door.style == "classic":
        arch_glass = place(
            (door.width * 0.46, 0.028, door.height * 0.18),
            (0.0, 0.04, (door.height * 0.26)),
            "FrontDoor_ArchGlass",
            glass_material(),
        )
        tag_object(arch_glass, asset_type="door_glass")

    if door.style == "modern":
        handle = place((0.02, 0.06, 0.55), ((door.width * 0.32), 0.03, 0.0), "FrontDoor_Handle", metal_material())
    else:
        handle = place((0.03, 0.06, 0.14), ((door.width * 0.28), 0.03, -0.15), "FrontDoor_Handle", metal_material())
    tag_object(handle, asset_type="door_hardware")


def _cut_corner_glass_clearance(
    spec: ResolvedSpec,
    structure: StructureState,
    collection: bpy.types.Collection,
) -> None:
    if spec.design_profile != "cubism" or not spec.design_options.get("corner_glass"):
        return

    front_by_floor = {
        opening.floor_index: opening
        for opening in spec.front_facade.windows
        if opening.frame_style == "frameless" and "corner" in opening.opening_id
    }
    left_by_floor = {
        opening.floor_index: opening
        for opening in spec.left_facade.windows
        if opening.frame_style == "frameless" and "corner" in opening.opening_id
    }

    for floor_index in sorted(set(front_by_floor) & set(left_by_floor)):
        shell = _shell_for_floor(structure, floor_index)
        front = front_by_floor[floor_index]
        left = left_by_floor[floor_index]
        bottom = max(front.bottom, left.bottom)
        height = min(front.height, left.height)
        cutter = add_box(
            f"CornerGlassClear_F{floor_index}",
            (spec.wall_thickness * 2.8, spec.wall_thickness * 2.8, height + 0.04),
            (
                float(shell.location.x) - (float(shell.dimensions.x) / 2.0) + spec.wall_thickness,
                float(shell.location.y) - (float(shell.dimensions.y) / 2.0) + spec.wall_thickness,
                bottom + (height / 2.0),
            ),
            collection,
            None,
        )
        apply_boolean_difference(shell, cutter)
        for target in _cut_targets(floor_index):
            apply_boolean_difference(target, cutter)


def apply_openings(
    spec: ResolvedSpec,
    structure: StructureState,
    collection: bpy.types.Collection,
) -> None:
    facades = [
        spec.front_facade,
        spec.rear_facade,
        spec.left_facade,
        spec.right_facade,
    ]

    for facade in facades:
        for opening in facade.windows:
            shell = _shell_for_floor(structure, opening.floor_index)
            _cut_opening(
                shell,
                spec,
                opening,
                collection,
                f"Cut_{opening.opening_id}",
            )

    door_opening = OpeningSpec(
        opening_id="front_door",
        facade="front",
        kind="door",
        center=spec.entrance.door.center,
        bottom=spec.entrance.door.bottom,
        width=spec.entrance.door.width,
        height=spec.entrance.door.height,
        floor_index=0,
    )
    _cut_opening(
        _shell_for_floor(structure, 0),
        spec,
        door_opening,
        collection,
        "Cut_FrontDoor",
    )
    _cut_corner_glass_clearance(spec, structure, collection)

    for facade in facades:
        for opening in facade.windows:
            shell = _shell_for_floor(structure, opening.floor_index)
            _build_window_unit(spec, opening, shell, collection)

    _build_door(spec, spec.entrance.door, _shell_for_floor(structure, 0), collection)
