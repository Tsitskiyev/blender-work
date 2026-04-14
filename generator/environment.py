from __future__ import annotations

import math

import bpy

from engine.specs import ResolvedSpec
from generator.common import add_box, add_cylinder, apply_bevel_modifier, create_empty, link_to_collection, tag_object
from generator.materials import frame_material, ground_material, paving_material


def _garage_center(spec: ResolvedSpec) -> tuple[float, float]:
    if spec.design_profile == "cubism" and spec.design_options.get("cantilever_carport"):
        shift_x = float(spec.design_options.get("upper_shift_x", 0.0))
        x_sign = 1.0 if shift_x >= 0.0 else -1.0
        return shift_x + (x_sign * max(0.8, (spec.garage.width * 0.35))), -(spec.depth * 0.12)
    x_sign = 1.0 if spec.garage.side == "right" else -1.0
    center_x = x_sign * ((spec.width / 2.0) + (spec.garage.width / 2.0) - (spec.wall_thickness / 2.0))
    center_y = (spec.garage.depth / 2.0) - (spec.depth / 2.0) + spec.garage.front_setback
    return center_x, center_y


def _build_ground(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    size_x = spec.width + (spec.environment.lot_margin * 2.0)
    size_y = spec.depth + (spec.environment.lot_margin * 2.0)
    ground = add_box(
        "Ground",
        (size_x, size_y, 0.06),
        (0.0, 0.0, -0.05),
        collection,
        ground_material(spec.design_profile),
    )
    apply_bevel_modifier(ground, 0.006, segments=1)
    tag_object(ground, asset_type="ground")


def _build_path(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    path = add_box(
        "FrontPath",
        (spec.environment.path_width, spec.environment.path_length, 0.05),
        (
            spec.entrance.door.center,
            -(spec.depth / 2.0) - (spec.environment.path_length / 2.0) + 0.05,
            0.01,
        ),
        collection,
        paving_material("gravel" if spec.design_options.get("gravel_path") else "default"),
    )
    tag_object(path, asset_type="path")


def _build_driveway(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    if not spec.garage.enabled:
        return
    center_x, center_y = _garage_center(spec)
    garage_front = center_y - (spec.garage.depth / 2.0)
    front_edge = -(spec.depth / 2.0) - spec.environment.lot_margin
    driveway_length = abs(garage_front - front_edge)
    driveway_center_y = (garage_front + front_edge) / 2.0
    driveway = add_box(
        "Driveway",
        (spec.environment.driveway_width, driveway_length, 0.05),
        (center_x, driveway_center_y, 0.01),
        collection,
        paving_material("gravel" if spec.design_options.get("gravel_path") else "default"),
    )
    tag_object(driveway, asset_type="driveway")


def _build_minimal_landscape(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    if not spec.design_options.get("minimal_landscape"):
        return

    shrub_positions = [
        (spec.entrance.door.center - 2.2, -(spec.depth / 2.0) - 1.8),
        (spec.entrance.door.center + 2.0, -(spec.depth / 2.0) - 2.4),
        (-(spec.width / 2.0) + 1.6, -(spec.depth / 2.0) - 1.4),
    ]
    for index, (x, y) in enumerate(shrub_positions):
        shrub = add_cylinder(
            f"Shrub_{index}",
            0.42 + (index * 0.05),
            0.55 + (index * 0.08),
            (x, y, 0.28 + (index * 0.04)),
            collection,
            ground_material(spec.design_profile),
            vertices=18,
        )
        tag_object(shrub, asset_type="landscape")


def _build_suburban_landscape(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    if spec.design_profile != "suburban":
        return

    if spec.design_options.get("shrubs"):
        positions = [
            (-4.4, -(spec.depth / 2.0) + 0.65),
            (-2.7, -(spec.depth / 2.0) + 0.60),
            (2.9, -(spec.depth / 2.0) + 0.60),
            (4.5, -(spec.depth / 2.0) + 0.68),
            (-(spec.width / 2.0) + 0.6, -1.8),
            (-(spec.width / 2.0) + 0.6, 0.2),
        ]
        for index, (x, y) in enumerate(positions):
            shrub = add_cylinder(
                f"FoundationShrub_{index}",
                0.30 + ((index % 2) * 0.04),
                0.52 + ((index % 3) * 0.08),
                (x, y, 0.28),
                collection,
                ground_material(spec.design_profile),
                vertices=18,
            )
            tag_object(shrub, asset_type="landscape")

    if spec.design_options.get("lawn"):
        tuft_positions = [
            (-3.8, -7.0),
            (-2.4, -6.2),
            (-0.6, -6.9),
            (1.8, -6.4),
            (4.9, -5.8),
            (5.5, -2.0),
            (-5.7, -1.6),
        ]
        for index, (x, y) in enumerate(tuft_positions):
            tuft = add_cylinder(
                f"LawnTuft_{index}",
                0.12,
                0.18 + ((index % 3) * 0.04),
                (x, y, 0.08),
                collection,
                ground_material(spec.design_profile),
                vertices=8,
            )
            tag_object(tuft, asset_type="landscape")


def _build_backdrop_trees(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    if not spec.design_options.get("backdrop_trees"):
        return

    rear_y = (spec.depth / 2.0) + spec.environment.lot_margin - 2.0
    x_positions = [-(spec.width * 0.55), -(spec.width * 0.25), spec.width * 0.05, spec.width * 0.38]
    for index, x in enumerate(x_positions):
        trunk = add_cylinder(
            f"BackdropTreeTrunk_{index}",
            0.08,
            4.5 + (index * 0.5),
            (x, rear_y + (index * 0.5), 2.25 + (index * 0.25)),
            collection,
            frame_material(),
            vertices=10,
        )
        tag_object(trunk, asset_type="backdrop_tree")
        crown = add_box(
            f"BackdropTreeCrown_{index}",
            (0.9, 0.9, 2.4 + (index * 0.3)),
            (x, rear_y + (index * 0.5), 5.0 + (index * 0.35)),
            collection,
            ground_material(spec.design_profile),
        )
        tag_object(crown, asset_type="backdrop_tree")


def _build_interior_glow(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    if not spec.design_options.get("warm_interior_glow"):
        return

    public_rooms = [room for room in spec.room_specs if room.zone == "public"]
    for index, room in enumerate(public_rooms[:2]):
        bpy.ops.object.light_add(
            type="POINT",
            location=(room.center_x, room.center_y, room.height * 0.72),
        )
        light = bpy.context.object
        light.name = f"InteriorGlow_{index}"
        link_to_collection(light, collection)
        light.data.energy = 240.0 + (min(room.width, room.depth) * 22.0)
        if hasattr(light.data, "shadow_soft_size"):
            light.data.shadow_soft_size = 0.45 + (min(room.width, room.depth) * 0.05)
        light.data.color = (1.0, 0.74, 0.50)
        tag_object(light, asset_type="interior_glow")
        if min(room.width, room.depth) > 4.5:
            bpy.ops.object.light_add(
                type="AREA",
                location=(room.center_x, room.center_y, room.height * 0.78),
            )
            area = bpy.context.object
            area.name = f"InteriorGlowFill_{index}"
            link_to_collection(area, collection)
            area.data.energy = 90.0
            area.data.size = min(room.width, room.depth) * 0.38
            area.data.color = (1.0, 0.80, 0.62)
            tag_object(area, asset_type="interior_glow")


def _configure_render(spec: ResolvedSpec) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    if hasattr(scene, "cycles"):
        scene.cycles.samples = 128 if spec.design_profile != "barnhouse" else 160
        scene.cycles.preview_samples = 48
        if hasattr(scene.cycles, "use_adaptive_sampling"):
            scene.cycles.use_adaptive_sampling = True
        if hasattr(scene.cycles, "use_denoising"):
            scene.cycles.use_denoising = True
        if hasattr(scene.cycles, "max_bounces"):
            scene.cycles.max_bounces = 8
    scene.render.use_motion_blur = False
    if hasattr(scene, "eevee"):
        if hasattr(scene.eevee, "use_gtao"):
            scene.eevee.use_gtao = True
        if hasattr(scene.eevee, "gtao_factor"):
            scene.eevee.gtao_factor = 1.4
    scene.view_settings.exposure = 0.10 if spec.design_options.get("golden_hour") else 0.0
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "AgX - Base Contrast", "None"):
        try:
            scene.view_settings.look = look
            break
        except Exception:
            continue


def _build_fence(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    if not spec.environment.fence_enabled:
        return

    half_w = (spec.width / 2.0) + spec.environment.lot_margin
    half_d = (spec.depth / 2.0) + spec.environment.lot_margin
    height = 1.15
    thickness = 0.08
    front_y = -half_d
    rear_y = half_d
    left_x = -half_w
    right_x = half_w

    gaps = [(0.0, spec.environment.path_width + 1.0)]
    if spec.garage.enabled:
        garage_x, _ = _garage_center(spec)
        gaps.append((garage_x, spec.environment.driveway_width + 0.8))
    gaps.sort(key=lambda item: item[0])

    cursor = -half_w
    for index, (gap_center, gap_width) in enumerate(gaps):
        start = cursor
        end = max(start, gap_center - (gap_width / 2.0))
        if end - start > 0.2:
            segment = add_box(
                f"FenceFront_{index}",
                (end - start, thickness, height),
                ((start + end) / 2.0, front_y, height / 2.0),
                collection,
                frame_material(),
            )
            tag_object(segment, asset_type="fence")
        cursor = gap_center + (gap_width / 2.0)
    if half_w - cursor > 0.2:
        segment = add_box(
            "FenceFront_End",
            (half_w - cursor, thickness, height),
            ((cursor + half_w) / 2.0, front_y, height / 2.0),
            collection,
            frame_material(),
        )
        tag_object(segment, asset_type="fence")

    for name, size, location in (
        ("FenceRear", (half_w * 2.0, thickness, height), (0.0, rear_y, height / 2.0)),
        ("FenceLeft", (thickness, half_d * 2.0, height), (left_x, 0.0, height / 2.0)),
        ("FenceRight", (thickness, half_d * 2.0, height), (right_x, 0.0, height / 2.0)),
    ):
        segment = add_box(name, size, location, collection, frame_material())
        tag_object(segment, asset_type="fence")


def setup_camera_and_lights(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    _configure_render(spec)
    target_x = float(spec.design_options.get("upper_shift_x", 0.0)) * 0.32 if spec.design_profile == "cubism" else 0.0
    target = create_empty(
        "CameraTarget",
        (target_x, 0.0, spec.wall_height * 0.58),
        collection,
    )
    if spec.design_profile == "cubism":
        camera_location = (
            spec.width * 1.55,
            -(spec.depth * 1.75),
            spec.wall_height * 0.96 + spec.roof.ridge_height,
        )
    elif spec.design_profile == "barnhouse":
        camera_location = (
            spec.width * 1.45,
            -(spec.depth * 1.95),
            spec.wall_height * 0.78 + spec.roof.ridge_height,
        )
    else:
        camera_location = (
            spec.width * 1.8,
            -(spec.depth * 2.1),
            spec.wall_height * 0.92 + spec.roof.ridge_height,
        )
    bpy.ops.object.camera_add(location=camera_location)
    camera = bpy.context.object
    camera.name = "MainCamera"
    link_to_collection(camera, collection)
    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    bpy.context.scene.camera = camera
    if spec.design_profile == "barnhouse":
        camera.data.dof.use_dof = True
        camera.data.dof.focus_object = target
        camera.data.dof.aperture_fstop = 4.0
    tag_object(camera, asset_type="camera")

    bpy.ops.object.light_add(
        type="SUN",
        location=(spec.width * 2.5, -spec.depth * 2.0, spec.wall_height * 2.8),
    )
    sun = bpy.context.object
    sun.name = "SunKey"
    link_to_collection(sun, collection)
    sun.data.energy = 2.0 if spec.design_profile == "barnhouse" else 2.8
    sun.data.angle = 0.12 if spec.design_profile == "barnhouse" else 0.18
    if spec.design_options.get("golden_hour"):
        sun.data.color = (1.0, 0.78, 0.56)
    tag_object(sun, asset_type="light")

    bpy.ops.object.light_add(
        type="AREA",
        location=(-spec.width * 1.2, -spec.depth * 1.4, spec.wall_height * 1.3),
    )
    fill = bpy.context.object
    fill.name = "FillArea"
    link_to_collection(fill, collection)
    fill.data.energy = 520.0 if spec.design_profile == "barnhouse" else 850.0
    fill.data.size = 9.0 if spec.design_profile == "barnhouse" else 8.0
    tag_object(fill, asset_type="light")

    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputWorld")
    output.location = (420, 0)
    background = nodes.new("ShaderNodeBackground")
    background.location = (140, 0)
    sky = nodes.new("ShaderNodeTexSky")
    sky.location = (-140, 0)
    for sky_type in ("NISHITA", "MULTIPLE_SCATTERING", "HOSEK_WILKIE", "PREETHAM"):
        try:
            sky.sky_type = sky_type
            break
        except Exception:
            continue
    sky.sun_elevation = math.radians(8.0 if spec.design_options.get("golden_hour") else 26.0)
    sky.sun_rotation = math.radians(135.0 if spec.design_options.get("golden_hour") else 105.0)
    background.inputs["Strength"].default_value = 0.42 if spec.design_options.get("golden_hour") else 0.55
    links.new(sky.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])


def build_environment(spec: ResolvedSpec, collection: bpy.types.Collection) -> None:
    _build_ground(spec, collection)
    _build_path(spec, collection)
    _build_driveway(spec, collection)
    _build_minimal_landscape(spec, collection)
    _build_suburban_landscape(spec, collection)
    _build_backdrop_trees(spec, collection)
    _build_fence(spec, collection)
    setup_camera_and_lights(spec, collection)
    _build_interior_glow(spec, collection)
