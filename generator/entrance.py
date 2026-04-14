from __future__ import annotations

import bpy

from engine.specs import ResolvedSpec
from generator.common import add_box, add_cylinder, create_mesh_object, tag_object
from generator.materials import frame_material, metal_material, terrace_material, trim_material


def _build_steps(
    spec: ResolvedSpec,
    landing_depth: float,
    landing_height: float,
    collection: bpy.types.Collection,
) -> None:
    center_x = spec.entrance.door.center
    step_count = max(1, min(4, round(landing_height / 0.08)))
    step_height = landing_height / step_count
    for index in range(step_count):
        depth = landing_depth + ((step_count - index - 1) * 0.18)
        z = (step_height / 2.0) + (index * step_height)
        y = -(spec.depth / 2.0) - (depth / 2.0) + 0.04
        step = add_box(
            f"EntranceStep_{index}",
            (spec.entrance.stoop_width, depth, step_height),
            (center_x, y, z),
            collection,
            terrace_material(spec.design_profile),
        )
        tag_object(step, asset_type="entrance_step")


def _build_columns(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    if not spec.entrance.has_columns:
        return
    column_material = trim_material(spec.design_profile) if spec.design_profile == "suburban" else frame_material()
    center_x = spec.entrance.door.center
    x_positions = [
        center_x - (spec.entrance.stoop_width / 2.0) + 0.42,
        center_x + (spec.entrance.stoop_width / 2.0) - 0.42,
    ]
    if spec.design_profile == "cabin" and spec.design_options.get("requested_porch"):
        y = -(spec.depth / 2.0) - spec.entrance.stoop_depth + 0.28
    elif spec.design_options.get("porch_gable"):
        y = -(spec.depth / 2.0) - max(0.85, spec.entrance.stoop_depth * 0.55)
    else:
        y = -(spec.depth / 2.0) - max(0.45, spec.entrance.canopy_depth * 0.72)
    z = spec.entrance.column_height / 2.0
    for index, x in enumerate(x_positions):
        if spec.entrance.style == "classic" and spec.design_profile != "suburban":
            column = add_cylinder(
                f"EntranceColumn_{index}",
                spec.entrance.column_radius,
                spec.entrance.column_height,
                (x, y, z),
                collection,
                column_material,
            )
        else:
            column = add_box(
                f"EntranceColumn_{index}",
                (
                    spec.entrance.column_radius * 1.8,
                    spec.entrance.column_radius * 1.8,
                    spec.entrance.column_height,
                ),
                (x, y, z),
                collection,
                column_material,
            )
        tag_object(column, asset_type="entrance_column")


def _build_cabin_porch(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    if spec.design_profile != "cabin" or not spec.design_options.get("requested_porch"):
        return

    porch_width = max(4.8, spec.entrance.stoop_width)
    porch_depth = max(2.2, spec.entrance.stoop_depth)
    deck_height = max(0.22, spec.entrance.door.bottom + 0.04)
    center_x = spec.entrance.door.center + min(0.8, porch_width * 0.10)
    center_y = -(spec.depth / 2.0) - (porch_depth / 2.0) + 0.14

    deck = add_box(
        "CabinPorchDeck",
        (porch_width, porch_depth, deck_height),
        (center_x, center_y, deck_height / 2.0),
        collection,
        terrace_material(spec.design_profile),
    )
    tag_object(deck, asset_type="entrance_landing")

    if spec.design_options.get("porch_balustrade"):
        rail_material = trim_material(spec.design_profile)
        rail_height = 0.86
        front_y = center_y - (porch_depth / 2.0) + 0.06
        left_x = center_x - (porch_width / 2.0) + 0.10
        right_x = center_x + (porch_width / 2.0) - 0.10

        def baluster_row(prefix: str, start_x: float, end_x: float, y_value: float) -> None:
            span = end_x - start_x
            count = max(8, int(span / 0.32))
            for index in range(count + 1):
                x = start_x + (span / count) * index
                baluster = add_box(
                    f"{prefix}_Baluster_{index}",
                    (0.06, 0.06, rail_height - 0.18),
                    (x, y_value, deck_height + ((rail_height - 0.18) / 2.0)),
                    collection,
                    rail_material,
                )
                tag_object(baluster, asset_type="entrance_porch")
            rail = add_box(
                f"{prefix}_RailTop",
                (span + 0.12, 0.08, 0.08),
                ((start_x + end_x) / 2.0, y_value, deck_height + rail_height),
                collection,
                rail_material,
            )
            tag_object(rail, asset_type="entrance_porch")

        baluster_row("PorchFront", left_x, spec.entrance.door.center - 0.65, front_y)
        side_span = porch_depth - 0.26
        side_count = max(5, int(side_span / 0.34))
        for index in range(side_count + 1):
            y_value = center_y - (side_span / 2.0) + (side_span / side_count) * index
            baluster = add_box(
                f"PorchSide_Baluster_{index}",
                (0.06, 0.06, rail_height - 0.18),
                (right_x, y_value, deck_height + ((rail_height - 0.18) / 2.0)),
                collection,
                rail_material,
            )
            tag_object(baluster, asset_type="entrance_porch")
        side_rail = add_box(
            "PorchSide_RailTop",
            (0.08, side_span + 0.08, 0.08),
            (right_x, center_y, deck_height + rail_height),
            collection,
            rail_material,
        )
        tag_object(side_rail, asset_type="entrance_porch")


def _build_portico(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    if not spec.entrance.has_portico:
        return
    trim = trim_material(spec.design_profile) if spec.design_profile == "suburban" else frame_material()
    center_x = spec.entrance.door.center
    canopy = add_box(
        "EntrancePortico",
        (
            spec.entrance.stoop_width + 0.5,
            spec.entrance.canopy_depth,
            spec.entrance.canopy_thickness,
        ),
        (
            center_x,
            -(spec.depth / 2.0) - (spec.entrance.canopy_depth / 2.0) + 0.05,
            spec.entrance.door.bottom
            + spec.entrance.door.height
            + 0.18
            + (spec.entrance.canopy_thickness / 2.0),
        ),
        collection,
        trim,
    )
    tag_object(canopy, asset_type="entrance_portico")
    if not spec.entrance.has_columns:
        for side in (-1.0, 1.0):
            bracket = add_box(
                f"PorticoBracket_{int(side)}",
                (0.10, spec.entrance.canopy_depth * 0.55, 0.20),
                (
                    center_x + side * ((spec.entrance.stoop_width / 2.0) - 0.25),
                    -(spec.depth / 2.0) - (spec.entrance.canopy_depth / 2.0) + 0.05,
                    spec.entrance.door.bottom + spec.entrance.door.height + 0.08,
                ),
                collection,
                metal_material(),
            )
            tag_object(bracket, asset_type="entrance_portico")


def _build_porch_gable(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    if not spec.design_options.get("porch_gable"):
        return

    trim = trim_material(spec.design_profile)
    center_x = spec.entrance.door.center
    porch_width = spec.entrance.stoop_width + 0.55
    porch_depth = max(1.7, spec.entrance.stoop_depth)
    eave = 0.18
    half_w = (porch_width / 2.0) + eave
    half_d = (porch_depth / 2.0) + eave
    base_z = spec.entrance.door.bottom + spec.entrance.door.height + 0.16
    ridge_z = base_z + 0.62
    center_y = -(spec.depth / 2.0) - (porch_depth / 2.0) + 0.02

    soffit = add_box(
        "PorchGable_Soffit",
        (porch_width + 0.18, porch_depth + 0.18, 0.06),
        (center_x, center_y, base_z - 0.03),
        collection,
        trim,
    )
    tag_object(soffit, asset_type="entrance_portico")

    verts = [
        (center_x - half_w, center_y - half_d, base_z),
        (center_x + half_w, center_y - half_d, base_z),
        (center_x + half_w, center_y + half_d, base_z),
        (center_x - half_w, center_y + half_d, base_z),
        (center_x, center_y - half_d, ridge_z),
        (center_x, center_y + half_d, ridge_z),
    ]
    faces = [
        (0, 1, 4),
        (1, 2, 5, 4),
        (2, 3, 5),
        (3, 0, 4, 5),
        (0, 3, 2, 1),
    ]
    roof = create_mesh_object("PorchGable_Roof", verts, faces, collection, metal_material())
    tag_object(roof, asset_type="entrance_portico")

    fascia_front = add_box(
        "PorchGable_FasciaFront",
        (porch_width + 0.12, 0.07, 0.16),
        (center_x, center_y - half_d + 0.035, base_z + 0.04),
        collection,
        trim,
    )
    tag_object(fascia_front, asset_type="entrance_portico")

    ledger = add_box(
        "PorchGable_Ledger",
        (porch_width + 0.12, 0.08, 0.16),
        (center_x, -(spec.depth / 2.0) + 0.04, base_z + 0.05),
        collection,
        trim,
    )
    tag_object(ledger, asset_type="entrance_portico")


def _build_pediment(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    if not spec.entrance.has_pediment:
        return
    center_x = spec.entrance.door.center
    pediment_width = spec.entrance.stoop_width + (0.4 if spec.entrance.has_portico else 0.1)
    depth = max(0.26, spec.entrance.canopy_depth * 0.18 if spec.entrance.canopy_depth else 0.28)
    base_z = (
        spec.entrance.door.bottom
        + spec.entrance.door.height
        + (0.24 if spec.entrance.has_portico else 0.12)
    )
    front_y = -(spec.depth / 2.0) - depth + 0.10
    back_y = front_y + depth
    half_w = pediment_width / 2.0
    peak_z = base_z + spec.entrance.pediment_height
    verts = [
        (center_x - half_w, front_y, base_z),
        (center_x + half_w, front_y, base_z),
        (center_x, front_y, peak_z),
        (center_x - half_w, back_y, base_z),
        (center_x + half_w, back_y, base_z),
        (center_x, back_y, peak_z),
    ]
    faces = [
        (0, 1, 2),
        (3, 5, 4),
        (0, 2, 5, 3),
        (1, 4, 5, 2),
        (0, 3, 4, 1),
    ]
    pediment = create_mesh_object("EntrancePediment", verts, faces, collection, frame_material())
    tag_object(pediment, asset_type="entrance_pediment")


def build_entrance(
    spec: ResolvedSpec,
    collection: bpy.types.Collection,
) -> None:
    if spec.design_profile == "cabin" and spec.design_options.get("requested_porch"):
        _build_cabin_porch(spec, collection)
        _build_steps(spec, max(1.2, spec.entrance.stoop_depth * 0.56), max(0.12, spec.entrance.door.bottom + 0.06), collection)
        _build_columns(spec, collection)
        _build_portico(spec, collection)
        _build_pediment(spec, collection)
        return

    center_x = spec.entrance.door.center
    landing_height = max(0.08, spec.entrance.door.bottom)
    landing_depth = 1.10 if not spec.terrace.enabled else 0.86
    landing = add_box(
        "EntranceLanding",
        (spec.entrance.stoop_width, landing_depth, landing_height),
        (
            center_x,
            -(spec.depth / 2.0) - (landing_depth / 2.0) + 0.05,
            landing_height / 2.0,
        ),
        collection,
        terrace_material(spec.design_profile),
    )
    tag_object(landing, asset_type="entrance_landing")

    _build_steps(spec, landing_depth, landing_height, collection)
    _build_columns(spec, collection)
    _build_porch_gable(spec, collection)
    _build_portico(spec, collection)
    _build_pediment(spec, collection)
