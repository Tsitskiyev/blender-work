from __future__ import annotations

import math

from engine.specs import ResolvedSpec
from generator.common import (
    add_box,
    add_cylinder,
    apply_bevel_modifier,
    apply_boolean_difference,
    apply_solidify_modifier,
    create_mesh_object,
    tag_object,
)
from generator.materials import glass_material, metal_material, roof_material, trim_material, wall_material


def _apply_flat_roof_skylights(spec: ResolvedSpec, slab, collection) -> None:
    skylights = [feature for feature in spec.feature_specs if feature.kind == "skylight"]
    for index, feature in enumerate(skylights):
        cutter = add_box(
            f"RoofSkylightCut_{index}",
            (feature.width + 0.08, feature.depth + 0.08, spec.roof.thickness + 0.18),
            (
                feature.center_x,
                feature.center_y,
                spec.roof.base_elevation + (spec.roof.thickness / 2.0),
            ),
            collection,
            None,
        )
        apply_boolean_difference(slab, cutter)
        glass = add_box(
            f"RoofSkylightGlass_{index}",
            (feature.width - 0.04, feature.depth - 0.04, 0.03),
            (
                feature.center_x,
                feature.center_y,
                spec.roof.base_elevation + spec.roof.thickness + 0.015,
            ),
            collection,
            glass_material(str(spec.design_options.get("glass_tint", "clear"))),
        )
        tag_object(glass, asset_type="skylight")


def _gable_roof(spec: ResolvedSpec, collection):
    half_w = (spec.width / 2.0) + spec.roof.overhang
    half_d = (spec.depth / 2.0) + spec.roof.overhang
    base_z = spec.roof.base_elevation
    ridge_z = base_z + spec.roof.ridge_height
    verts = [
        (-half_w, -half_d, base_z),
        (half_w, -half_d, base_z),
        (half_w, half_d, base_z),
        (-half_w, half_d, base_z),
        (0.0, -half_d, ridge_z),
        (0.0, half_d, ridge_z),
    ]
    faces = [
        (0, 1, 4),
        (1, 2, 5, 4),
        (2, 3, 5),
        (3, 0, 4, 5),
    ]
    roof = create_mesh_object("MainRoof_Gable", verts, faces, collection, roof_material("gable", spec.design_profile))
    apply_solidify_modifier(roof, max(0.14, spec.roof.thickness), offset=0.0)
    apply_bevel_modifier(roof, 0.018, segments=2)
    tag_object(roof, asset_type="roof_main", roof_type="gable")
    return roof


def _hip_roof(spec: ResolvedSpec, collection):
    half_w = (spec.width / 2.0) + spec.roof.overhang
    half_d = (spec.depth / 2.0) + spec.roof.overhang
    base_z = spec.roof.base_elevation
    ridge_z = base_z + spec.roof.ridge_height
    ridge_half = max(0.18, half_d - half_w)
    verts = [
        (-half_w, -half_d, base_z),
        (half_w, -half_d, base_z),
        (half_w, half_d, base_z),
        (-half_w, half_d, base_z),
        (0.0, -ridge_half, ridge_z),
        (0.0, ridge_half, ridge_z),
    ]
    faces = [
        (0, 1, 4),
        (1, 2, 5, 4),
        (2, 3, 5),
        (3, 0, 4, 5),
    ]
    roof = create_mesh_object("MainRoof_Hip", verts, faces, collection, roof_material("hip", spec.design_profile))
    apply_solidify_modifier(roof, max(0.14, spec.roof.thickness), offset=0.0)
    apply_bevel_modifier(roof, 0.018, segments=2)
    tag_object(roof, asset_type="roof_main", roof_type="hip")
    return roof


def _flat_roof(spec: ResolvedSpec, collection):
    center_x = float(spec.design_options.get("upper_shift_x", 0.0)) if spec.design_profile == "cubism" and spec.floors >= 2 else 0.0
    slab = add_box(
        "MainRoof_Flat",
        (
            spec.width + (spec.roof.overhang * 2.0),
            spec.depth + (spec.roof.overhang * 2.0),
            spec.roof.thickness,
        ),
        (center_x, 0.0, spec.roof.base_elevation + (spec.roof.thickness / 2.0)),
        collection,
        roof_material("flat", spec.design_profile),
    )
    apply_bevel_modifier(slab, 0.012, segments=2)
    tag_object(slab, asset_type="roof_main", roof_type="flat")
    _apply_flat_roof_skylights(spec, slab, collection)
    return slab


def _suburban_cross_gable(spec: ResolvedSpec, collection) -> None:
    if not spec.design_options.get("cross_gable") or spec.roof.roof_type != "gable":
        return
    width = max(3.6, spec.width * 0.34)
    depth = max(3.0, spec.depth * 0.34)
    overhang = max(0.18, spec.roof.overhang * 0.45)
    half_w = (width / 2.0) + overhang
    half_d = (depth / 2.0) + overhang
    base_z = spec.roof.base_elevation + 0.18
    rise = (depth / 2.0) * math.tan(math.radians(spec.roof.pitch_degrees))
    ridge_z = base_z + rise
    center_y = -(spec.depth / 2.0) + (depth / 2.0) + 0.18
    verts = [
        (-half_w, center_y - half_d, base_z),
        (half_w, center_y - half_d, base_z),
        (half_w, center_y + half_d, base_z),
        (-half_w, center_y + half_d, base_z),
        (-half_w, center_y, ridge_z),
        (half_w, center_y, ridge_z),
    ]
    faces = [
        (0, 1, 5, 4),
        (1, 2, 5),
        (2, 3, 4, 5),
        (3, 0, 4),
    ]
    roof = create_mesh_object("CrossGable_Roof", verts, faces, collection, roof_material("gable", spec.design_profile))
    apply_solidify_modifier(roof, max(0.12, spec.roof.thickness * 0.92), offset=0.0)
    apply_bevel_modifier(roof, 0.016, segments=2)
    tag_object(roof, asset_type="roof_feature", roof_type="cross_gable")


def _generic_pitched_eaves(spec: ResolvedSpec, collection) -> None:
    if spec.roof.roof_type == "flat" or spec.design_profile == "suburban":
        return
    trim = trim_material(spec.design_profile)
    fascia_depth = 0.09
    fascia_height = 0.16
    soffit_depth = max(0.14, spec.roof.overhang * 0.60)
    base_z = spec.roof.base_elevation - (fascia_height / 2.0)

    front = add_box(
        "RoofFascia_Front",
        (spec.width + (spec.roof.overhang * 2.0), fascia_depth, fascia_height),
        (0.0, -(spec.depth / 2.0) - spec.roof.overhang + (fascia_depth / 2.0), base_z),
        collection,
        trim,
    )
    rear = add_box(
        "RoofFascia_Rear",
        (spec.width + (spec.roof.overhang * 2.0), fascia_depth, fascia_height),
        (0.0, (spec.depth / 2.0) + spec.roof.overhang - (fascia_depth / 2.0), base_z),
        collection,
        trim,
    )
    soffit_front = add_box(
        "RoofSoffit_Front",
        (spec.width + (spec.roof.overhang * 2.0), soffit_depth, 0.04),
        (0.0, -(spec.depth / 2.0) - (soffit_depth / 2.0), spec.roof.base_elevation - 0.02),
        collection,
        trim,
    )
    soffit_rear = add_box(
        "RoofSoffit_Rear",
        (spec.width + (spec.roof.overhang * 2.0), soffit_depth, 0.04),
        (0.0, (spec.depth / 2.0) + (soffit_depth / 2.0), spec.roof.base_elevation - 0.02),
        collection,
        trim,
    )
    for obj in (front, rear, soffit_front, soffit_rear):
        apply_bevel_modifier(obj, 0.008, segments=2)
        tag_object(obj, asset_type="roof_trim")


def _suburban_soffits(spec: ResolvedSpec, collection) -> None:
    if spec.design_profile != "suburban":
        return
    trim = trim_material(spec.design_profile)
    fascia_depth = 0.09
    fascia_height = 0.18
    soffit_depth = max(0.12, spec.roof.overhang * 0.45)
    base_z = spec.roof.base_elevation - (fascia_height / 2.0)

    front = add_box(
        "RoofFascia_Front",
        (spec.width + (spec.roof.overhang * 2.0), fascia_depth, fascia_height),
        (0.0, -(spec.depth / 2.0) - spec.roof.overhang + (fascia_depth / 2.0), base_z),
        collection,
        trim,
    )
    rear = add_box(
        "RoofFascia_Rear",
        (spec.width + (spec.roof.overhang * 2.0), fascia_depth, fascia_height),
        (0.0, (spec.depth / 2.0) + spec.roof.overhang - (fascia_depth / 2.0), base_z),
        collection,
        trim,
    )
    tag_object(front, asset_type="roof_trim")
    tag_object(rear, asset_type="roof_trim")

    soffit_front = add_box(
        "RoofSoffit_Front",
        (spec.width + (spec.roof.overhang * 2.0), soffit_depth, 0.04),
        (0.0, -(spec.depth / 2.0) - (soffit_depth / 2.0), spec.roof.base_elevation - 0.02),
        collection,
        trim,
    )
    soffit_rear = add_box(
        "RoofSoffit_Rear",
        (spec.width + (spec.roof.overhang * 2.0), soffit_depth, 0.04),
        (0.0, (spec.depth / 2.0) + (soffit_depth / 2.0), spec.roof.base_elevation - 0.02),
        collection,
        trim,
    )
    tag_object(soffit_front, asset_type="roof_trim")
    tag_object(soffit_rear, asset_type="roof_trim")


def _build_chimney(spec: ResolvedSpec, collection) -> None:
    if not spec.design_options.get("chimney") or spec.roof.roof_type == "flat":
        return
    chimney = add_box(
        "ChimneyStack",
        (0.78, 0.78, 1.95),
        (-1.55, 0.85, spec.roof.base_elevation + (spec.roof.ridge_height * 0.58)),
        collection,
        wall_material("brick"),
    )
    cap = add_box(
        "ChimneyCap",
        (0.92, 0.92, 0.08),
        (-1.55, 0.85, chimney.location.z + 1.02),
        collection,
        metal_material(),
    )
    tag_object(chimney, asset_type="chimney")
    tag_object(cap, asset_type="chimney")


def _build_gutters(spec: ResolvedSpec, collection) -> None:
    if not spec.design_options.get("gutters"):
        return
    trim = trim_material(spec.design_profile)
    gutter_radius = 0.055
    front_y = -(spec.depth / 2.0) - spec.roof.overhang + 0.05
    rear_y = (spec.depth / 2.0) + spec.roof.overhang - 0.05
    z = spec.roof.base_elevation - 0.02

    for index, y in enumerate((front_y, rear_y)):
        gutter = add_cylinder(
            f"Gutter_{index}",
            gutter_radius,
            spec.width + (spec.roof.overhang * 2.0),
            (0.0, y, z),
            collection,
            trim,
            vertices=14,
        )
        gutter.rotation_euler[1] = math.radians(90.0)
        tag_object(gutter, asset_type="gutter")

    for name, x, y in (
        ("Downspout_FL", -(spec.width / 2.0) - spec.roof.overhang + 0.12, front_y),
        ("Downspout_FR", (spec.width / 2.0) + spec.roof.overhang - 0.12, front_y),
        ("Downspout_RL", -(spec.width / 2.0) - spec.roof.overhang + 0.12, rear_y),
        ("Downspout_RR", (spec.width / 2.0) + spec.roof.overhang - 0.12, rear_y),
    ):
        pipe = add_box(
            name,
            (0.08, 0.08, spec.wall_height - 0.18),
            (x, y, (spec.wall_height - 0.18) / 2.0),
            collection,
            trim,
        )
        tag_object(pipe, asset_type="gutter")


def _garage_center(spec: ResolvedSpec) -> tuple[float, float]:
    x_sign = 1.0 if spec.garage.side == "right" else -1.0
    center_x = x_sign * ((spec.width / 2.0) + (spec.garage.width / 2.0) - (spec.wall_thickness / 2.0))
    center_y = (spec.garage.depth / 2.0) - (spec.depth / 2.0) + spec.garage.front_setback
    return center_x, center_y


def _build_porch_lean_to(spec: ResolvedSpec, collection) -> None:
    if spec.design_profile != "cabin" or not spec.design_options.get("porch_lean_to"):
        return
    trim = trim_material(spec.design_profile)
    porch_width = max(4.6, spec.entrance.stoop_width)
    porch_depth = max(2.2, spec.entrance.stoop_depth)
    center_x = spec.entrance.door.center + min(0.9, porch_width * 0.10)
    center_y = -(spec.depth / 2.0) - (porch_depth / 2.0) + 0.18
    roof_height = spec.entrance.door.bottom + spec.entrance.door.height + 0.72
    roof = add_box(
        "PorchLeanToRoof",
        (porch_width + 0.42, porch_depth + 0.24, 0.14),
        (center_x, center_y, roof_height),
        collection,
        roof_material("gable", spec.design_profile),
    )
    roof.rotation_euler[0] = math.radians(12.0)
    apply_bevel_modifier(roof, 0.012, segments=2)
    tag_object(roof, asset_type="roof_feature", roof_type="porch_lean_to")

    fascia = add_box(
        "PorchLeanToFascia",
        (porch_width + 0.48, 0.08, 0.16),
        (center_x, center_y - (porch_depth / 2.0) + 0.02, roof_height - 0.06),
        collection,
        trim,
    )
    tag_object(fascia, asset_type="roof_trim")

    ledger = add_box(
        "PorchLeanToLedger",
        (porch_width + 0.20, 0.10, 0.16),
        (center_x, -(spec.depth / 2.0) + 0.05, roof_height + 0.12),
        collection,
        trim,
    )
    tag_object(ledger, asset_type="roof_trim")


def _garage_roof(spec: ResolvedSpec, collection):
    if not spec.garage.enabled:
        return None
    center_x, center_y = _garage_center(spec)
    if spec.roof.roof_type == "flat":
        roof = add_box(
            "GarageRoof_Flat",
            (
                spec.garage.width + 0.2,
                spec.garage.depth + 0.2,
                0.16,
            ),
            (center_x, center_y, spec.garage.height + 0.08),
            collection,
            roof_material("flat", spec.design_profile),
        )
        apply_bevel_modifier(roof, 0.012, segments=2)
        tag_object(roof, asset_type="garage_roof")
        return roof

    half_w = (spec.garage.width / 2.0) + 0.2
    half_d = (spec.garage.depth / 2.0) + 0.18
    base_z = spec.garage.height
    ridge_z = base_z + min(1.15, spec.roof.ridge_height * 0.42)
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
    ]
    roof = create_mesh_object("GarageRoof_Sloped", verts, faces, collection, roof_material(spec.roof.roof_type, spec.design_profile))
    apply_solidify_modifier(roof, max(0.12, spec.roof.thickness * 0.9), offset=0.0)
    apply_bevel_modifier(roof, 0.016, segments=2)
    tag_object(roof, asset_type="garage_roof")
    return roof


def build_roof(spec: ResolvedSpec, collection):
    if spec.roof.roof_type == "gable":
        roof = _gable_roof(spec, collection)
    elif spec.roof.roof_type == "hip":
        roof = _hip_roof(spec, collection)
    else:
        roof = _flat_roof(spec, collection)
    _generic_pitched_eaves(spec, collection)
    _suburban_cross_gable(spec, collection)
    _suburban_soffits(spec, collection)
    _build_porch_lean_to(spec, collection)
    _build_chimney(spec, collection)
    _build_gutters(spec, collection)
    _garage_roof(spec, collection)
    return roof
