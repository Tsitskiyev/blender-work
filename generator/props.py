from __future__ import annotations

from engine.specs import ResolvedSpec
from generator.common import add_box, add_cylinder, tag_object
from generator.materials import door_material, glass_material, ground_material, metal_material, trim_material


def _build_mailbox(spec: ResolvedSpec, collection) -> None:
    if not spec.design_options.get("mailbox"):
        return
    x = (spec.environment.driveway_width / 2.0) + (spec.garage.width / 2.0 if spec.garage.enabled else 3.6)
    y = -(spec.depth / 2.0) - (spec.environment.path_length * 0.55)
    post = add_box("MailboxPost", (0.09, 0.09, 1.2), (x, y, 0.60), collection, trim_material(spec.design_profile))
    box = add_box("MailboxBox", (0.34, 0.22, 0.22), (x + 0.08, y, 1.05), collection, metal_material())
    flag = add_box("MailboxFlag", (0.02, 0.12, 0.03), (x + 0.26, y, 1.08), collection, door_material("modern"))
    tag_object(post, asset_type="prop")
    tag_object(box, asset_type="prop")
    tag_object(flag, asset_type="prop")


def _build_garden_lights(spec: ResolvedSpec, collection) -> None:
    if not spec.design_options.get("garden_lights"):
        return
    y_positions = [
        -(spec.depth / 2.0) - (spec.environment.path_length * 0.26),
        -(spec.depth / 2.0) - (spec.environment.path_length * 0.52),
        -(spec.depth / 2.0) - (spec.environment.path_length * 0.78),
    ]
    x_offset = (spec.environment.path_width / 2.0) + 0.28
    for index, y in enumerate(y_positions):
        for side, x in (("L", spec.entrance.door.center - x_offset), ("R", spec.entrance.door.center + x_offset)):
            stem = add_cylinder(
                f"GardenLight_{index}_{side}_Stem",
                0.018,
                0.48,
                (x, y, 0.24),
                collection,
                metal_material(),
                vertices=12,
            )
            head = add_box(
                f"GardenLight_{index}_{side}_Head",
                (0.10, 0.10, 0.08),
                (x, y, 0.50),
                collection,
                glass_material(),
            )
            tag_object(stem, asset_type="prop")
            tag_object(head, asset_type="prop")


def _build_welcome_mat(spec: ResolvedSpec, collection) -> None:
    if not spec.design_options.get("welcome_mat"):
        return
    y = -(spec.depth / 2.0) - (spec.entrance.stoop_depth * 0.30)
    mat = add_box(
        "WelcomeMat",
        (0.9, 0.42, 0.015),
        (spec.entrance.door.center, y, 0.018),
        collection,
        door_material("classic"),
    )
    tag_object(mat, asset_type="prop")


def _build_hanging_pot(spec: ResolvedSpec, collection) -> None:
    if not spec.design_options.get("hanging_pot"):
        return
    x = spec.entrance.door.center + (spec.entrance.stoop_width / 2.0) - 0.45
    y = -(spec.depth / 2.0) - 0.55
    chain = add_box("PorchPot_Chain", (0.02, 0.02, 0.48), (x, y, spec.entrance.door.height + 0.55), collection, metal_material())
    pot = add_cylinder("PorchPot", 0.14, 0.18, (x, y, spec.entrance.door.height + 0.22), collection, door_material("classic"), vertices=16)
    plant = add_cylinder("PorchPot_Plant", 0.18, 0.22, (x, y, spec.entrance.door.height + 0.34), collection, ground_material(spec.design_profile), vertices=16)
    tag_object(chain, asset_type="prop")
    tag_object(pot, asset_type="prop")
    tag_object(plant, asset_type="prop")


def _build_utility_meter(spec: ResolvedSpec, collection) -> None:
    if not spec.design_options.get("utility_meter"):
        return
    x = -(spec.width / 2.0) - 0.03
    y = 1.6
    meter = add_box("ElectricMeter", (0.24, 0.10, 0.34), (x, y, 1.55), collection, metal_material())
    outlet = add_box("OutdoorOutlet", (0.12, 0.05, 0.16), (x, y + 0.42, 0.58), collection, trim_material(spec.design_profile))
    tag_object(meter, asset_type="prop")
    tag_object(outlet, asset_type="prop")


def _build_door_lantern(spec: ResolvedSpec, collection) -> None:
    if not spec.design_options.get("door_lantern"):
        return
    x = spec.entrance.door.center - (spec.entrance.door.width / 2.0) - 0.28
    y = -(spec.depth / 2.0) + 0.06
    z = spec.entrance.door.bottom + spec.entrance.door.height - 0.34
    base = add_box("DoorLantern_Base", (0.08, 0.10, 0.08), (x, y, z + 0.12), collection, metal_material())
    arm = add_box("DoorLantern_Arm", (0.06, 0.16, 0.03), (x + 0.03, y, z + 0.18), collection, metal_material())
    lantern = add_box("DoorLantern_Light", (0.12, 0.12, 0.22), (x + 0.07, y, z), collection, glass_material())
    tag_object(base, asset_type="prop")
    tag_object(arm, asset_type="prop")
    tag_object(lantern, asset_type="prop")


def build_props(spec: ResolvedSpec, collection) -> None:
    _build_mailbox(spec, collection)
    _build_garden_lights(spec, collection)
    _build_welcome_mat(spec, collection)
    _build_hanging_pot(spec, collection)
    _build_utility_meter(spec, collection)
    _build_door_lantern(spec, collection)
