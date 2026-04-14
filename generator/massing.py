from __future__ import annotations

import bpy

from engine.specs import ResolvedSpec
from generator.facade import opening_location, opening_size
from generator.common import StructureState, add_box, apply_boolean_difference, tag_object
from generator.materials import (
    door_material,
    foundation_material,
    glass_material,
    metal_material,
    roof_material,
    terrace_material,
    trim_material,
    wall_material,
    wood_cladding_material,
    wood_dark_material,
)


def _make_hollow_shell(
    name: str,
    width: float,
    depth: float,
    height: float,
    wall_thickness: float,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
    *,
    location: tuple[float, float, float] | None = None,
) -> bpy.types.Object:
    center = location if location is not None else (0.0, 0.0, height / 2.0)
    shell = add_box(
        name,
        (width, depth, height),
        center,
        collection,
        material,
    )
    inner_width = max(0.4, width - (wall_thickness * 2.0))
    inner_depth = max(0.4, depth - (wall_thickness * 2.0))
    cutter = add_box(
        f"{name}_Void",
        (inner_width, inner_depth, height + 0.08),
        center,
        collection,
        None,
    )
    apply_boolean_difference(shell, cutter)
    return shell


def _build_foundation(spec: ResolvedSpec, collection: bpy.types.Collection) -> bpy.types.Object:
    foundation_height = spec.foundation_height + 0.18
    foundation_surface = wall_material("brick") if spec.design_options.get("brick_plinth") or spec.design_profile == "cabin" else foundation_material()
    foundation = add_box(
        "Foundation",
        (spec.width + 0.6, spec.depth + 0.6, foundation_height),
        (0.0, 0.0, (foundation_height / 2.0) - 0.08),
        collection,
        foundation_surface,
    )
    tag_object(foundation, asset_type="foundation")
    return foundation


def _build_floor_slabs(spec: ResolvedSpec, collection: bpy.types.Collection) -> list[bpy.types.Object]:
    slabs: list[bpy.types.Object] = []
    interior_width = max(0.5, spec.width - (spec.wall_thickness * 2.0))
    interior_depth = max(0.5, spec.depth - (spec.wall_thickness * 2.0))
    shift_x = float(spec.design_options.get("upper_shift_x", 0.0)) if spec.design_profile == "cubism" else 0.0
    for level in range(spec.floors):
        elevation = (level * spec.floor_height) + (spec.floor_slab_thickness / 2.0)
        center_x = shift_x if spec.design_profile == "cubism" and level >= 1 else 0.0
        slab = add_box(
            f"FloorSlab_{level}",
            (interior_width, interior_depth, spec.floor_slab_thickness),
            (center_x, 0.0, elevation),
            collection,
            foundation_material(),
        )
        tag_object(slab, asset_type="floor_slab", level=level)
        slabs.append(slab)
    return slabs


def _build_roof_plate(spec: ResolvedSpec, collection: bpy.types.Collection) -> bpy.types.Object:
    shift_x = float(spec.design_options.get("upper_shift_x", 0.0)) if spec.design_profile == "cubism" and spec.floors >= 2 else 0.0
    roof_plate = add_box(
        "RoofPlate",
        (
            max(0.5, spec.width - (spec.wall_thickness * 2.0)),
            max(0.5, spec.depth - (spec.wall_thickness * 2.0)),
            spec.floor_slab_thickness,
        ),
        (shift_x, 0.0, spec.wall_height - (spec.floor_slab_thickness / 2.0)),
        collection,
        foundation_material(),
    )
    tag_object(roof_plate, asset_type="roof_plate")
    return roof_plate


def _build_cubism_lower_roof_deck(spec: ResolvedSpec, collection: bpy.types.Collection) -> bpy.types.Object | None:
    if spec.design_profile != "cubism" or spec.floors < 2:
        return None
    shift_x = float(spec.design_options.get("upper_shift_x", 0.0))
    strip_width = min(spec.width, max(0.65, abs(shift_x)))
    if strip_width < 0.65:
        return None
    center_x = (
        (-(spec.width / 2.0) + (strip_width / 2.0))
        if shift_x >= 0.0
        else ((spec.width / 2.0) - (strip_width / 2.0))
    )
    deck = add_box(
        "LowerRoofDeck",
        (strip_width, spec.depth, spec.floor_slab_thickness),
        (
            center_x,
            0.0,
            spec.floor_height + (spec.floor_slab_thickness / 2.0),
        ),
        collection,
        foundation_material(),
    )
    tag_object(deck, asset_type="lower_roof_deck")
    return deck


def _build_cubism_upper_soffit(spec: ResolvedSpec, collection: bpy.types.Collection) -> bpy.types.Object | None:
    if spec.design_profile != "cubism" or spec.floors < 2:
        return None
    shift_x = float(spec.design_options.get("upper_shift_x", 0.0))
    soffit_thickness = 0.06
    soffit = add_box(
        "UpperCantileverSoffit",
        (spec.width, spec.depth, soffit_thickness),
        (
            shift_x,
            0.0,
            spec.floor_height - (soffit_thickness / 2.0),
        ),
        collection,
        roof_material("flat", spec.design_profile),
    )
    tag_object(soffit, asset_type="cubism_soffit")
    return soffit


def _build_garage(spec: ResolvedSpec, collection: bpy.types.Collection) -> bpy.types.Object | None:
    if not spec.garage.enabled:
        return None
    if spec.design_profile == "cubism" and spec.design_options.get("cantilever_carport"):
        shift_x = float(spec.design_options.get("upper_shift_x", 0.0))
        x_sign = 1.0 if shift_x >= 0.0 else -1.0
        center_x = shift_x + (x_sign * max(0.8, (spec.garage.width * 0.35)))
        center_y = -(spec.depth * 0.12)
        carport = add_box(
            "CarportPad",
            (spec.garage.width, spec.garage.depth * 0.72, 0.08),
            (center_x, center_y, 0.04),
            collection,
            foundation_material(),
        )
        tag_object(carport, asset_type="garage_shell")

        charger = add_box(
            "EVCharger",
            (0.16, 0.14, 1.35),
            (center_x - (x_sign * ((spec.garage.width / 2.0) - 0.32)), center_y + (spec.garage.depth * 0.22), 0.675),
            collection,
            metal_material(),
        )
        tag_object(charger, asset_type="garage_feature")
        return carport

    x_sign = 1.0 if spec.garage.side == "right" else -1.0
    center_x = x_sign * ((spec.width / 2.0) + (spec.garage.width / 2.0) - (spec.wall_thickness / 2.0))
    center_y = (spec.garage.depth / 2.0) - (spec.depth / 2.0) + spec.garage.front_setback
    shell = add_box(
        "GarageShell",
        (spec.garage.width, spec.garage.depth, spec.garage.height),
        (center_x, center_y, spec.garage.height / 2.0),
        collection,
        wall_material(spec.wall_material, spec.design_profile),
    )
    inner = add_box(
        "GarageVoid",
        (
            max(0.4, spec.garage.width - (spec.wall_thickness * 2.0)),
            max(0.4, spec.garage.depth - (spec.wall_thickness * 2.0)),
            spec.garage.height,
        ),
        (center_x, center_y, spec.garage.height / 2.0),
        collection,
        None,
    )
    apply_boolean_difference(shell, inner)

    dual_doors = bool(spec.design_options.get("garage_dual_doors"))
    door_centers = [center_x]
    if dual_doors:
        spacing = spec.garage.door_width + 0.28
        door_centers = [center_x - (spacing / 2.0), center_x + (spacing / 2.0)]

    for index, door_center in enumerate(door_centers):
        door_cut = add_box(
            f"GarageDoorCut_{index}",
            (spec.garage.door_width, (spec.wall_thickness * 2.0) + 0.10, spec.garage.door_height),
            (
                door_center,
                center_y - (spec.garage.depth / 2.0) + (spec.wall_thickness / 2.0),
                spec.garage.door_height / 2.0,
            ),
            collection,
            None,
        )
        apply_boolean_difference(shell, door_cut)

        door = add_box(
            f"GarageDoor_{index}",
            (
                spec.garage.door_width - 0.08,
                0.06,
                spec.garage.door_height - 0.06,
            ),
            (
                door_center,
                center_y - (spec.garage.depth / 2.0) + min(0.12, max(0.04, spec.wall_thickness * 0.40)),
                (spec.garage.door_height / 2.0) + 0.02,
            ),
            collection,
            door_material("modern"),
        )
        tag_object(door, asset_type="garage_door")

        if spec.design_options.get("garage_panels"):
            panel_step = (spec.garage.door_height - 0.20) / 4.0
            for panel_index in range(4):
                relief = add_box(
                    f"GarageDoor_{index}_Panel_{panel_index}",
                    (spec.garage.door_width - 0.22, 0.012, panel_step - 0.08),
                    (
                        door_center,
                        door.location.y + 0.032,
                        0.20 + (panel_step / 2.0) + (panel_index * panel_step),
                    ),
                    collection,
                    metal_material(),
                )
                tag_object(relief, asset_type="garage_door_detail")

        if spec.design_options.get("garage_top_windows"):
            top_y = door.location.y + 0.038
            lite_count = 3
            lite_width = (spec.garage.door_width - 0.34) / lite_count
            for lite_index in range(lite_count):
                lite_x = door_center - ((spec.garage.door_width - 0.34) / 2.0) + (lite_width / 2.0) + (lite_index * lite_width)
                lite = add_box(
                    f"GarageDoor_{index}_Lite_{lite_index}",
                    (lite_width - 0.05, 0.018, 0.22),
                    (lite_x, top_y, spec.garage.door_height - 0.22),
                    collection,
                    glass_material(),
                )
                tag_object(lite, asset_type="garage_door_detail")
    tag_object(shell, asset_type="garage_shell")
    return shell


def _build_terrace(spec: ResolvedSpec, collection: bpy.types.Collection) -> bpy.types.Object | None:
    if not spec.terrace.enabled:
        return None
    glass_style = str(spec.design_options.get("glass_tint", "clear")) if spec.design_profile == "cubism" else "clear"
    terrace_y = spec.terrace.center_y
    slab_thickness = spec.terrace.elevation
    slab_center_z = spec.terrace.elevation / 2.0
    if spec.design_profile != "cubism":
        terrace_y = -(spec.depth / 2.0) - (spec.terrace.depth / 2.0) + 0.04
    else:
        slab_thickness = 0.04
        slab_center_z = spec.floor_height + spec.floor_slab_thickness + (slab_thickness / 2.0)
    slab = add_box(
        "FrontTerrace",
        (spec.terrace.width, spec.terrace.depth, slab_thickness),
        (
            spec.terrace.center_x,
            terrace_y,
            slab_center_z,
        ),
        collection,
        terrace_material(spec.design_profile),
    )
    tag_object(slab, asset_type="terrace")
    if spec.design_profile == "cubism":
        outer_side = -1.0 if spec.terrace.center_x < 0.0 else 1.0
        side_guard = add_box(
            f"TerraceGlass_{'L' if outer_side < 0 else 'R'}",
            (0.04, spec.terrace.depth, 1.05),
            (
                spec.terrace.center_x + outer_side * ((spec.terrace.width / 2.0) - 0.02),
                terrace_y,
                spec.terrace.elevation + 0.52,
            ),
            collection,
            glass_material(glass_style),
        )
        tag_object(side_guard, asset_type="terrace_guard")
        front_guard = add_box(
            "TerraceGlass_Front",
            (spec.terrace.width, 0.04, 1.05),
            (
                spec.terrace.center_x,
                terrace_y - (spec.terrace.depth / 2.0) + 0.02,
                spec.terrace.elevation + 0.52,
            ),
            collection,
            glass_material(glass_style),
        )
        tag_object(front_guard, asset_type="terrace_guard")
        rear_guard = add_box(
            "TerraceGlass_Rear",
            (spec.terrace.width, 0.04, 1.05),
            (
                spec.terrace.center_x,
                terrace_y + (spec.terrace.depth / 2.0) - 0.02,
                spec.terrace.elevation + 0.52,
            ),
            collection,
            glass_material(glass_style),
        )
        tag_object(rear_guard, asset_type="terrace_guard")
    return slab


def _build_balcony(spec: ResolvedSpec, collection: bpy.types.Collection) -> bpy.types.Object | None:
    if not spec.balcony.enabled:
        return None

    slab = add_box(
        "FrontBalcony",
        (spec.balcony.width, spec.balcony.depth, 0.14),
        (
            spec.balcony.center_x,
            -(spec.depth / 2.0) - (spec.balcony.depth / 2.0) + 0.03,
            spec.balcony.elevation,
        ),
        collection,
        terrace_material(spec.design_profile),
    )
    tag_object(slab, asset_type="balcony")

    rail_height = 0.92
    post_spacing = 0.9
    post_count = max(2, int(spec.balcony.width / post_spacing))
    for index in range(post_count + 1):
        x = spec.balcony.center_x + (-spec.balcony.width / 2.0) + (index * (spec.balcony.width / post_count))
        post = add_box(
            f"BalconyPost_{index}",
            (0.05, 0.05, rail_height),
            (
                x,
                -(spec.depth / 2.0) - spec.balcony.depth + 0.08,
                spec.balcony.elevation + (rail_height / 2.0),
            ),
            collection,
            metal_material(),
        )
        tag_object(post, asset_type="balcony_rail")
    rail = add_box(
        "BalconyRail",
        (spec.balcony.width, 0.05, 0.06),
        (
            spec.balcony.center_x,
            -(spec.depth / 2.0) - spec.balcony.depth + 0.08,
            spec.balcony.elevation + rail_height,
        ),
        collection,
        metal_material(),
    )
    tag_object(rail, asset_type="balcony_rail")
    return slab


def _build_upper_cladding(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    if spec.upper_wall_material != "wood_dark" or spec.floors < 2:
        return

    cladding_height = max(0.8, spec.wall_height - spec.floor_height)
    center_z = spec.floor_height + (cladding_height / 2.0)
    thickness = 0.04
    material = wood_dark_material()
    segments = [
        (
            "UpperCladding_Front",
            (spec.width + 0.02, thickness, cladding_height),
            (0.0, -(spec.depth / 2.0) - (thickness / 2.0), center_z),
        ),
        (
            "UpperCladding_Rear",
            (spec.width + 0.02, thickness, cladding_height),
            (0.0, (spec.depth / 2.0) + (thickness / 2.0), center_z),
        ),
        (
            "UpperCladding_Left",
            (thickness, spec.depth + 0.02, cladding_height),
            (-(spec.width / 2.0) - (thickness / 2.0), 0.0, center_z),
        ),
        (
            "UpperCladding_Right",
            (thickness, spec.depth + 0.02, cladding_height),
            ((spec.width / 2.0) + (thickness / 2.0), 0.0, center_z),
        ),
    ]
    facade_openings = {
        "front": [opening for opening in spec.front_facade.windows if opening.floor_index >= 1],
        "rear": [opening for opening in spec.rear_facade.windows if opening.floor_index >= 1],
        "left": [opening for opening in spec.left_facade.windows if opening.floor_index >= 1],
        "right": [opening for opening in spec.right_facade.windows if opening.floor_index >= 1],
    }

    for name, size, location in segments:
        segment = add_box(name, size, location, collection, material)
        tag_object(segment, asset_type="upper_cladding")
        facade = name.split("_")[-1].lower()
        for opening in facade_openings.get(facade, []):
            cutter = add_box(
                f"{name}_{opening.opening_id}_Cut",
                opening_size(spec, opening.facade, opening.width + 0.08, opening.height + 0.08, 0.18),
                opening_location(spec, opening.facade, opening.center, opening.bottom, opening.width, opening.height),
                collection,
                None,
            )
            apply_boolean_difference(segment, cutter)


def _build_barnhouse_cladding(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    if spec.design_profile != "barnhouse" or not spec.design_options.get("wood_cladding_mix"):
        return

    thickness = 0.045
    material = wood_cladding_material()
    force_symmetry = bool(spec.design_options.get("force_symmetry", False))

    if force_symmetry:
        front_width = max(4.4, spec.width * 0.42)
        front_center_x = 0.0
    else:
        left_limit = -(spec.width / 2.0)
        right_limit = spec.entrance.door.center - (spec.entrance.door.width / 2.0) - 0.48
        front_width = max(3.8, right_limit - left_limit)
        front_center_x = left_limit + (front_width / 2.0)

    panels = [
        (
            "BarnhouseCladding_Front",
            "front",
            (front_width, thickness, spec.wall_height + 0.02),
            (front_center_x, -(spec.depth / 2.0) - (thickness / 2.0), spec.wall_height / 2.0),
        ),
        (
            "BarnhouseCladding_Left",
            "left",
            (thickness, spec.depth + 0.02, spec.wall_height + 0.02),
            (-(spec.width / 2.0) - (thickness / 2.0), 0.0, spec.wall_height / 2.0),
        ),
    ]

    facade_openings = {
        "front": list(spec.front_facade.windows),
        "left": list(spec.left_facade.windows),
    }

    for name, facade, size, location in panels:
        panel = add_box(name, size, location, collection, material)
        tag_object(panel, asset_type="barnhouse_cladding")
        for opening in facade_openings.get(facade, []):
            cutter = add_box(
                f"{name}_{opening.opening_id}_Cut",
                opening_size(spec, opening.facade, opening.width + 0.08, opening.height + 0.08, 0.18),
                opening_location(spec, opening.facade, opening.center, opening.bottom, opening.width, opening.height),
                collection,
                None,
            )
            apply_boolean_difference(panel, cutter)


def _build_cubism_panel_cladding(
    spec: ResolvedSpec,
    shell_by_floor: dict[int, bpy.types.Object],
    collection: bpy.types.Collection,
) -> None:
    if spec.design_profile != "cubism":
        return

    panel_style = str(spec.design_options.get("panel_cladding", "anthracite_panels"))
    panel_surface = roof_material("flat", spec.design_profile) if panel_style == "anthracite_panels" else wall_material("concrete", spec.design_profile)
    thickness = 0.035

    def _joint_hits_opening(floor_index: int, x_position: float) -> bool:
        opening_margin = 0.18
        front_openings = [opening for opening in spec.front_facade.windows if opening.floor_index == floor_index]
        if floor_index == 0:
            front_openings.append(
                type(
                    "DoorOpeningProxy",
                    (),
                    {
                        "center": spec.entrance.door.center,
                        "width": spec.entrance.door.width,
                    },
                )()
            )
        for opening in front_openings:
            if abs(x_position - float(opening.center)) <= ((float(opening.width) / 2.0) + opening_margin):
                return True
        return False

    for floor_index, shell in shell_by_floor.items():
        center_x = float(shell.location.x)
        center_y = float(shell.location.y)
        center_z = float(shell.location.z)
        width = float(shell.dimensions.x)
        depth = float(shell.dimensions.y)
        height = float(shell.dimensions.z)
        segments = [
            (
                f"Panel_Front_F{floor_index}",
                (width + 0.03, thickness, height + 0.02),
                (center_x, center_y - (depth / 2.0) - (thickness / 2.0), center_z),
            ),
            (
                f"Panel_Rear_F{floor_index}",
                (width + 0.03, thickness, height + 0.02),
                (center_x, center_y + (depth / 2.0) + (thickness / 2.0), center_z),
            ),
            (
                f"Panel_Left_F{floor_index}",
                (thickness, depth + 0.03, height + 0.02),
                (center_x - (width / 2.0) - (thickness / 2.0), center_y, center_z),
            ),
            (
                f"Panel_Right_F{floor_index}",
                (thickness, depth + 0.03, height + 0.02),
                (center_x + (width / 2.0) + (thickness / 2.0), center_y, center_z),
            ),
        ]
        for name, size, location in segments:
            panel = add_box(name, size, location, collection, panel_surface)
            tag_object(panel, asset_type="facade_panel", floor_index=floor_index)

        if spec.design_options.get("emissive_joints"):
            joint_count = max(2, int(width / 2.4))
            for index in range(1, joint_count):
                x = center_x - (width / 2.0) + (width / joint_count) * index
                if _joint_hits_opening(floor_index, x):
                    continue
                joint = add_box(
                    f"PanelJoint_Front_F{floor_index}_{index}",
                    (0.04, 0.02, height - 0.12),
                    (x, center_y - (depth / 2.0) - 0.01, center_z),
                    collection,
                    metal_material(),
                )
                tag_object(joint, asset_type="facade_joint")


def _build_cubism_massing(
    spec: ResolvedSpec,
    collection: bpy.types.Collection,
) -> tuple[bpy.types.Object, dict[int, bpy.types.Object]]:
    shift_x = float(spec.design_options.get("upper_shift_x", 0.0))
    shell_material = wall_material(
        "concrete" if spec.design_options.get("panel_cladding") == "dark_concrete" else spec.wall_material,
        spec.design_profile,
    )

    lower_shell = _make_hollow_shell(
        "HouseShell_Lower",
        spec.width,
        spec.depth,
        spec.floor_height,
        spec.wall_thickness,
        collection,
        shell_material,
        location=(0.0, 0.0, spec.floor_height / 2.0),
    )
    tag_object(lower_shell, asset_type="house_shell", floor_index=0)

    shell_by_floor = {0: lower_shell}
    if spec.floors <= 1:
        return lower_shell, shell_by_floor

    upper_height = max(spec.floor_height, spec.wall_height - spec.floor_height)
    upper_shell = _make_hollow_shell(
        "HouseShell_Upper",
        spec.width,
        spec.depth,
        upper_height,
        spec.wall_thickness,
        collection,
        shell_material,
        location=(shift_x, 0.0, spec.floor_height + (upper_height / 2.0)),
    )
    tag_object(upper_shell, asset_type="house_shell_upper", floor_index=1)
    for floor_index in range(1, spec.floors):
        shell_by_floor[floor_index] = upper_shell
    return lower_shell, shell_by_floor


def _build_suburban_trim(spec: ResolvedSpec, shell_by_floor: dict[int, bpy.types.Object], garage_shell: bpy.types.Object | None, collection: bpy.types.Collection) -> None:
    if spec.design_profile != "suburban" or not spec.design_options.get("trim_boards"):
        return
    trim = trim_material(spec.design_profile)
    board_width = 0.12

    shell = shell_by_floor.get(0)
    if shell is not None:
        half_w = float(shell.dimensions.x) / 2.0
        half_d = float(shell.dimensions.y) / 2.0
        for name, x, y in (
            ("CornerTrim_FL", -half_w - (board_width / 2.0), -half_d, ),
            ("CornerTrim_FR", half_w + (board_width / 2.0), -half_d, ),
            ("CornerTrim_RL", -half_w - (board_width / 2.0), half_d, ),
            ("CornerTrim_RR", half_w + (board_width / 2.0), half_d, ),
        ):
            board = add_box(
                name,
                (board_width, 0.08, spec.wall_height + 0.04),
                (x, y, spec.wall_height / 2.0),
                collection,
                trim,
            )
            tag_object(board, asset_type="trim")

    if garage_shell is not None:
        gx = float(garage_shell.location.x)
        gy = float(garage_shell.location.y)
        half_w = float(garage_shell.dimensions.x) / 2.0
        half_d = float(garage_shell.dimensions.y) / 2.0
        for index, (x, y) in enumerate(
            (
                (gx - half_w - (board_width / 2.0), gy - half_d),
                (gx + half_w + (board_width / 2.0), gy - half_d),
            )
        ):
            board = add_box(
                f"GarageTrim_{index}",
                (board_width, 0.08, spec.garage.height + 0.04),
                (x, y, spec.garage.height / 2.0),
                collection,
                trim,
            )
            tag_object(board, asset_type="trim")


def build_massing(spec: ResolvedSpec, collection: bpy.types.Collection) -> StructureState:
    foundation = _build_foundation(spec, collection)
    if spec.design_profile == "cubism":
        shell, shell_by_floor = _build_cubism_massing(spec, collection)
    else:
        shell = _make_hollow_shell(
            "HouseShell",
            spec.width,
            spec.depth,
            spec.wall_height,
            spec.wall_thickness,
            collection,
            wall_material(spec.wall_material, spec.design_profile),
        )
        tag_object(shell, asset_type="house_shell")
        shell_by_floor = {floor_index: shell for floor_index in range(spec.floors)}

    slabs = _build_floor_slabs(spec, collection)
    roof_plate = _build_roof_plate(spec, collection)
    lower_roof_deck = _build_cubism_lower_roof_deck(spec, collection)
    _build_cubism_upper_soffit(spec, collection)
    _build_upper_cladding(spec, collection)
    _build_barnhouse_cladding(spec, collection)
    _build_cubism_panel_cladding(spec, shell_by_floor, collection)
    garage_shell = _build_garage(spec, collection)
    _build_suburban_trim(spec, shell_by_floor, garage_shell, collection)
    terrace_slab = _build_terrace(spec, collection)
    balcony_slab = _build_balcony(spec, collection)

    return StructureState(
        main_shell=shell,
        foundation=foundation,
        floor_slabs=slabs,
        roof_plate=roof_plate,
        lower_roof_deck=lower_roof_deck,
        garage_shell=garage_shell,
        terrace_slab=terrace_slab,
        balcony_slab=balcony_slab,
        shell_by_floor=shell_by_floor,
    )
