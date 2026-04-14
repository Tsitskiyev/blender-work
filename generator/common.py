from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable

import bpy


@dataclass(slots=True)
class StructureState:
    main_shell: bpy.types.Object
    foundation: bpy.types.Object
    floor_slabs: list[bpy.types.Object] = field(default_factory=list)
    roof_plate: bpy.types.Object | None = None
    lower_roof_deck: bpy.types.Object | None = None
    garage_shell: bpy.types.Object | None = None
    terrace_slab: bpy.types.Object | None = None
    balcony_slab: bpy.types.Object | None = None
    shell_by_floor: dict[int, bpy.types.Object] = field(default_factory=dict)


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for collection in list(bpy.data.collections):
        if collection.users == 0:
            bpy.data.collections.remove(collection)
    for block_list in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.curves,
        bpy.data.images,
    ):
        for block in list(block_list):
            if block.users == 0:
                block_list.remove(block)


def ensure_collection(name: str) -> bpy.types.Collection:
    existing = bpy.data.collections.get(name)
    if existing:
        return existing
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def link_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def tag_object(obj: bpy.types.Object, **metadata) -> None:
    for key, value in metadata.items():
        obj[key] = value


def add_box(
    name: str,
    size: tuple[float, float, float],
    location: tuple[float, float, float],
    collection: bpy.types.Collection,
    material: bpy.types.Material | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    link_to_collection(obj, collection)
    if material:
        assign_material(obj, material)
    return obj


def add_cylinder(
    name: str,
    radius: float,
    depth: float,
    location: tuple[float, float, float],
    collection: bpy.types.Collection,
    material: bpy.types.Material | None = None,
    vertices: int = 32,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    link_to_collection(obj, collection)
    if material:
        assign_material(obj, material)
    return obj


def create_mesh_object(
    name: str,
    verts: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    collection: bpy.types.Collection,
    material: bpy.types.Material | None = None,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    link_to_collection(obj, collection)
    if material:
        assign_material(obj, material)
    return obj


def create_empty(
    name: str,
    location: tuple[float, float, float],
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    bpy.context.scene.collection.objects.link(obj)
    link_to_collection(obj, collection)
    return obj


def parent_keep_world(child: bpy.types.Object, parent: bpy.types.Object) -> None:
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


def assign_material(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    if obj.data is None:
        return
    materials = obj.data.materials
    if materials:
        materials[0] = material
    else:
        materials.append(material)


def apply_boolean_difference(target: bpy.types.Object, cutter: bpy.types.Object) -> None:
    modifier = target.modifiers.new(name=f"Bool_{cutter.name}", type="BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.object = cutter
    modifier.solver = "EXACT"

    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    with bpy.context.temp_override(
        object=target,
        active_object=target,
        selected_objects=[target],
        selected_editable_objects=[target],
    ):
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    cutter.hide_render = True
    cutter.hide_viewport = True


def apply_bevel_modifier(
    target: bpy.types.Object,
    width: float,
    *,
    segments: int = 2,
    angle_limit_degrees: float = 34.0,
) -> None:
    if target.data is None or width <= 0.0:
        return
    modifier = target.modifiers.new(name="ArchitecturalBevel", type="BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = math.radians(angle_limit_degrees)
    modifier.harden_normals = True
    if hasattr(target.data, "use_auto_smooth"):
        target.data.use_auto_smooth = True


def apply_solidify_modifier(
    target: bpy.types.Object,
    thickness: float,
    *,
    offset: float = 0.0,
) -> None:
    if target.data is None or thickness <= 0.0:
        return
    modifier = target.modifiers.new(name="ArchitecturalSolidify", type="SOLIDIFY")
    modifier.thickness = thickness
    modifier.offset = offset
    modifier.use_even_offset = True
    modifier.use_quality_normals = True


def count_tagged_objects(asset_type: str, facade: str | None = None) -> int:
    count = 0
    for obj in bpy.data.objects:
        if obj.get("asset_type") != asset_type:
            continue
        if facade is not None and obj.get("facade") != facade:
            continue
        count += 1
    return count


def first_tagged(asset_type: str) -> bpy.types.Object | None:
    for obj in bpy.data.objects:
        if obj.get("asset_type") == asset_type:
            return obj
    return None


def tagged_objects(asset_type: str) -> Iterable[bpy.types.Object]:
    for obj in bpy.data.objects:
        if obj.get("asset_type") == asset_type:
            yield obj
