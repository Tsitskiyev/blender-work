from __future__ import annotations

import bpy


_CACHE: dict[str, bpy.types.Material] = {}


def _socket(node: bpy.types.ShaderNodeBsdfPrincipled, *names: str):
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            return socket
    raise KeyError(f"Socket not found: {names}")


def _configure_transparency(material: bpy.types.Material) -> None:
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "BLENDED"
    elif hasattr(material, "blend_method"):
        material.blend_method = "BLEND"

    if hasattr(material, "use_transparency_overlap"):
        material.use_transparency_overlap = True

    if hasattr(material, "use_transparent_shadow"):
        material.use_transparent_shadow = True
    elif hasattr(material, "shadow_method"):
        material.shadow_method = "HASHED"


def _new_material(name: str) -> tuple[bpy.types.Material, bpy.types.Nodes, bpy.types.NodeLinks, bpy.types.ShaderNodeBsdfPrincipled]:
    cached = _CACHE.get(name)
    if cached is not None:
        nodes = cached.node_tree.nodes
        links = cached.node_tree.links
        principled = next(node for node in nodes if node.bl_idname == "ShaderNodeBsdfPrincipled")
        return cached, nodes, links, principled

    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    principled = nodes.new("ShaderNodeBsdfPrincipled")
    output = nodes.new("ShaderNodeOutputMaterial")
    principled.location = (540, 0)
    output.location = (820, 0)
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    _CACHE[name] = material
    return material, nodes, links, principled


def _texture_mapping(nodes: bpy.types.Nodes, links: bpy.types.NodeLinks, scale: tuple[float, float, float]):
    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    texcoord.location = (-980, 0)
    mapping.location = (-760, 0)
    mapping.inputs["Scale"].default_value[0] = scale[0]
    mapping.inputs["Scale"].default_value[1] = scale[1]
    mapping.inputs["Scale"].default_value[2] = scale[2]
    links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
    return mapping


def _base_material(
    name: str,
    color: tuple[float, float, float],
    *,
    roughness: float,
    metallic: float = 0.0,
    transmission: float = 0.0,
    alpha: float = 1.0,
) -> bpy.types.Material:
    cached = _CACHE.get(name)
    if cached:
        return cached

    material, nodes, links, principled = _new_material(name)
    _socket(principled, "Base Color").default_value = (*color, 1.0)
    _socket(principled, "Roughness").default_value = roughness
    _socket(principled, "Metallic").default_value = metallic
    if transmission > 0.0:
        _socket(principled, "Transmission Weight", "Transmission").default_value = transmission
        _socket(principled, "IOR").default_value = 1.45
    if alpha < 1.0:
        _socket(principled, "Alpha").default_value = alpha
        _configure_transparency(material)
    return material


def _stucco_material() -> bpy.types.Material:
    cached = _CACHE.get("Wall_stucco")
    if cached:
        return cached

    material, nodes, links, principled = _new_material("Wall_stucco")
    mapping = _texture_mapping(nodes, links, (4.0, 4.0, 4.0))

    noise_large = nodes.new("ShaderNodeTexNoise")
    noise_large.location = (-520, 120)
    noise_large.inputs["Scale"].default_value = 5.0
    noise_large.inputs["Detail"].default_value = 8.0
    noise_large.inputs["Roughness"].default_value = 0.58

    noise_fine = nodes.new("ShaderNodeTexNoise")
    noise_fine.location = (-520, -120)
    noise_fine.inputs["Scale"].default_value = 38.0
    noise_fine.inputs["Detail"].default_value = 10.0
    noise_fine.inputs["Roughness"].default_value = 0.62

    color_ramp = nodes.new("ShaderNodeValToRGB")
    color_ramp.location = (-250, 120)
    color_ramp.color_ramp.elements[0].position = 0.30
    color_ramp.color_ramp.elements[0].color = (0.78, 0.75, 0.70, 1.0)
    color_ramp.color_ramp.elements[1].position = 0.82
    color_ramp.color_ramp.elements[1].color = (0.91, 0.88, 0.84, 1.0)

    bump = nodes.new("ShaderNodeBump")
    bump.location = (250, -140)
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.08

    links.new(mapping.outputs["Vector"], noise_large.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise_fine.inputs["Vector"])
    links.new(noise_large.outputs["Fac"], color_ramp.inputs["Fac"])
    links.new(noise_fine.outputs["Fac"], bump.inputs["Height"])
    links.new(color_ramp.outputs["Color"], _socket(principled, "Base Color"))
    links.new(bump.outputs["Normal"], _socket(principled, "Normal"))
    _socket(principled, "Roughness").default_value = 0.92
    return material


def _dark_stucco_material() -> bpy.types.Material:
    cached = _CACHE.get("Wall_stucco_dark")
    if cached:
        return cached

    material, nodes, links, principled = _new_material("Wall_stucco_dark")
    mapping = _texture_mapping(nodes, links, (4.0, 4.0, 4.0))

    noise_large = nodes.new("ShaderNodeTexNoise")
    noise_large.location = (-520, 120)
    noise_large.inputs["Scale"].default_value = 5.8
    noise_large.inputs["Detail"].default_value = 8.0
    noise_large.inputs["Roughness"].default_value = 0.58

    noise_fine = nodes.new("ShaderNodeTexNoise")
    noise_fine.location = (-520, -120)
    noise_fine.inputs["Scale"].default_value = 42.0
    noise_fine.inputs["Detail"].default_value = 10.0
    noise_fine.inputs["Roughness"].default_value = 0.60

    color_ramp = nodes.new("ShaderNodeValToRGB")
    color_ramp.location = (-250, 120)
    color_ramp.color_ramp.elements[0].position = 0.28
    color_ramp.color_ramp.elements[0].color = (0.20, 0.21, 0.22, 1.0)
    color_ramp.color_ramp.elements[1].position = 0.86
    color_ramp.color_ramp.elements[1].color = (0.32, 0.33, 0.34, 1.0)

    bump = nodes.new("ShaderNodeBump")
    bump.location = (250, -140)
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.08

    links.new(mapping.outputs["Vector"], noise_large.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise_fine.inputs["Vector"])
    links.new(noise_large.outputs["Fac"], color_ramp.inputs["Fac"])
    links.new(noise_fine.outputs["Fac"], bump.inputs["Height"])
    links.new(color_ramp.outputs["Color"], _socket(principled, "Base Color"))
    links.new(bump.outputs["Normal"], _socket(principled, "Normal"))
    _socket(principled, "Roughness").default_value = 0.94
    return material


def _siding_material() -> bpy.types.Material:
    cached = _CACHE.get("Wall_Siding")
    if cached:
        return cached

    material, nodes, links, principled = _new_material("Wall_Siding")
    mapping = _texture_mapping(nodes, links, (1.2, 1.2, 8.8))

    siding_wave = nodes.new("ShaderNodeTexWave")
    siding_wave.location = (-620, 80)
    siding_wave.wave_type = "BANDS"
    siding_wave.bands_direction = "Z"
    siding_wave.inputs["Scale"].default_value = 34.0
    siding_wave.inputs["Distortion"].default_value = 0.0
    siding_wave.inputs["Detail"].default_value = 1.0

    lap_shadow = nodes.new("ShaderNodeTexWave")
    lap_shadow.location = (-620, -110)
    lap_shadow.wave_type = "BANDS"
    lap_shadow.bands_direction = "Z"
    lap_shadow.inputs["Scale"].default_value = 34.0
    lap_shadow.inputs["Distortion"].default_value = 0.0
    lap_shadow.inputs["Detail"].default_value = 0.0

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-620, -300)
    noise.inputs["Scale"].default_value = 10.0
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.46

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-220, 60)
    ramp.color_ramp.elements[0].position = 0.34
    ramp.color_ramp.elements[0].color = (0.78, 0.76, 0.72, 1.0)
    ramp.color_ramp.elements[1].position = 0.84
    ramp.color_ramp.elements[1].color = (0.92, 0.90, 0.87, 1.0)

    lap_profile = nodes.new("ShaderNodeValToRGB")
    lap_profile.location = (-220, -120)
    lap_profile.color_ramp.elements[0].position = 0.44
    lap_profile.color_ramp.elements[0].color = (0.05, 0.05, 0.05, 1.0)
    lap_profile.color_ramp.elements[1].position = 0.56
    lap_profile.color_ramp.elements[1].color = (0.82, 0.82, 0.82, 1.0)

    mix = nodes.new("ShaderNodeMixRGB")
    mix.location = (20, 40)
    mix.blend_type = "MULTIPLY"
    mix.inputs["Fac"].default_value = 0.12

    shadow_mix = nodes.new("ShaderNodeMixRGB")
    shadow_mix.location = (20, -90)
    shadow_mix.blend_type = "MULTIPLY"
    shadow_mix.inputs["Fac"].default_value = 0.18

    roughness_map = nodes.new("ShaderNodeMapRange")
    roughness_map.location = (260, -270)
    roughness_map.inputs["From Min"].default_value = 0.0
    roughness_map.inputs["From Max"].default_value = 1.0
    roughness_map.inputs["To Min"].default_value = 0.70
    roughness_map.inputs["To Max"].default_value = 0.86

    bump = nodes.new("ShaderNodeBump")
    bump.location = (260, -130)
    bump.inputs["Strength"].default_value = 0.14
    bump.inputs["Distance"].default_value = 0.025

    links.new(mapping.outputs["Vector"], siding_wave.inputs["Vector"])
    links.new(mapping.outputs["Vector"], lap_shadow.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(siding_wave.outputs["Color"], ramp.inputs["Fac"])
    links.new(lap_shadow.outputs["Fac"], lap_profile.inputs["Fac"])
    links.new(ramp.outputs["Color"], mix.inputs["Color1"])
    links.new(noise.outputs["Color"], mix.inputs["Color2"])
    links.new(mix.outputs["Color"], shadow_mix.inputs["Color1"])
    links.new(lap_profile.outputs["Color"], shadow_mix.inputs["Color2"])
    links.new(lap_profile.outputs["Fac"], bump.inputs["Height"])
    links.new(shadow_mix.outputs["Color"], _socket(principled, "Base Color"))
    links.new(noise.outputs["Fac"], roughness_map.inputs["Value"])
    links.new(roughness_map.outputs["Result"], _socket(principled, "Roughness"))
    links.new(bump.outputs["Normal"], _socket(principled, "Normal"))
    return material


def _brick_material() -> bpy.types.Material:
    cached = _CACHE.get("Wall_brick")
    if cached:
        return cached

    material, nodes, links, principled = _new_material("Wall_brick")
    mapping = _texture_mapping(nodes, links, (1.6, 1.6, 1.6))

    brick = nodes.new("ShaderNodeTexBrick")
    brick.location = (-520, 60)
    brick.inputs["Scale"].default_value = 8.0
    brick.inputs["Brick Width"].default_value = 0.48
    brick.inputs["Row Height"].default_value = 0.22
    brick.inputs["Mortar Size"].default_value = 0.025
    brick.inputs["Mortar Smooth"].default_value = 0.02
    brick.inputs["Bias"].default_value = 0.02
    brick.inputs["Color1"].default_value = (0.47, 0.22, 0.15, 1.0)
    brick.inputs["Color2"].default_value = (0.63, 0.31, 0.22, 1.0)
    brick.inputs["Mortar"].default_value = (0.76, 0.73, 0.69, 1.0)

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-520, -190)
    noise.inputs["Scale"].default_value = 18.0
    noise.inputs["Detail"].default_value = 5.0

    noise_ramp = nodes.new("ShaderNodeValToRGB")
    noise_ramp.location = (-260, -190)
    noise_ramp.color_ramp.elements[0].position = 0.25
    noise_ramp.color_ramp.elements[0].color = (0.80, 0.80, 0.80, 1.0)
    noise_ramp.color_ramp.elements[1].position = 0.88
    noise_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)

    color_mix = nodes.new("ShaderNodeMixRGB")
    color_mix.location = (20, 20)
    color_mix.blend_type = "MULTIPLY"
    color_mix.inputs["Fac"].default_value = 0.24

    bump = nodes.new("ShaderNodeBump")
    bump.location = (250, -140)
    bump.inputs["Strength"].default_value = 0.20
    bump.inputs["Distance"].default_value = 0.08

    links.new(mapping.outputs["Vector"], brick.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], noise_ramp.inputs["Fac"])
    links.new(brick.outputs["Color"], color_mix.inputs["Color1"])
    links.new(noise_ramp.outputs["Color"], color_mix.inputs["Color2"])
    links.new(brick.outputs["Fac"], bump.inputs["Height"])
    links.new(color_mix.outputs["Color"], _socket(principled, "Base Color"))
    links.new(bump.outputs["Normal"], _socket(principled, "Normal"))
    _socket(principled, "Roughness").default_value = 0.90
    return material


def _stone_like_material(
    name: str,
    dark: tuple[float, float, float],
    light: tuple[float, float, float],
    *,
    scale: tuple[float, float, float],
    bump_strength: float,
) -> bpy.types.Material:
    cached = _CACHE.get(name)
    if cached:
        return cached

    material, nodes, links, principled = _new_material(name)
    mapping = _texture_mapping(nodes, links, scale)

    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.location = (-520, 90)
    voronoi.feature = "F1"
    voronoi.inputs["Scale"].default_value = 6.0
    voronoi.inputs["Randomness"].default_value = 0.68

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-520, -160)
    noise.inputs["Scale"].default_value = 20.0
    noise.inputs["Detail"].default_value = 7.0
    noise.inputs["Roughness"].default_value = 0.65

    color_ramp = nodes.new("ShaderNodeValToRGB")
    color_ramp.location = (-240, 90)
    color_ramp.color_ramp.elements[0].position = 0.16
    color_ramp.color_ramp.elements[0].color = (*dark, 1.0)
    color_ramp.color_ramp.elements[1].position = 0.82
    color_ramp.color_ramp.elements[1].color = (*light, 1.0)

    bump = nodes.new("ShaderNodeBump")
    bump.location = (250, -140)
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.10

    links.new(mapping.outputs["Vector"], voronoi.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(voronoi.outputs["Distance"], color_ramp.inputs["Fac"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(color_ramp.outputs["Color"], _socket(principled, "Base Color"))
    links.new(bump.outputs["Normal"], _socket(principled, "Normal"))
    _socket(principled, "Roughness").default_value = 0.93
    return material


def _concrete_material() -> bpy.types.Material:
    cached = _CACHE.get("Wall_concrete")
    if cached:
        return cached

    material, nodes, links, principled = _new_material("Wall_concrete")
    mapping = _texture_mapping(nodes, links, (3.5, 3.5, 3.5))

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-520, 120)
    noise.inputs["Scale"].default_value = 16.0
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.57

    noise_fine = nodes.new("ShaderNodeTexNoise")
    noise_fine.location = (-520, -120)
    noise_fine.inputs["Scale"].default_value = 52.0
    noise_fine.inputs["Detail"].default_value = 8.0

    color_ramp = nodes.new("ShaderNodeValToRGB")
    color_ramp.location = (-250, 120)
    color_ramp.color_ramp.elements[0].position = 0.26
    color_ramp.color_ramp.elements[0].color = (0.38, 0.40, 0.42, 1.0)
    color_ramp.color_ramp.elements[1].position = 0.84
    color_ramp.color_ramp.elements[1].color = (0.56, 0.58, 0.60, 1.0)

    bump = nodes.new("ShaderNodeBump")
    bump.location = (250, -140)
    bump.inputs["Strength"].default_value = 0.10
    bump.inputs["Distance"].default_value = 0.08

    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise_fine.inputs["Vector"])
    links.new(noise.outputs["Fac"], color_ramp.inputs["Fac"])
    links.new(noise_fine.outputs["Fac"], bump.inputs["Height"])
    links.new(color_ramp.outputs["Color"], _socket(principled, "Base Color"))
    links.new(bump.outputs["Normal"], _socket(principled, "Normal"))
    _socket(principled, "Roughness").default_value = 0.88
    return material


def _wood_material(
    name: str,
    dark: tuple[float, float, float],
    light: tuple[float, float, float],
    roughness: float,
) -> bpy.types.Material:
    cached = _CACHE.get(name)
    if cached:
        return cached

    material, nodes, links, principled = _new_material(name)
    mapping = _texture_mapping(nodes, links, (3.0, 3.0, 3.0))

    wave = nodes.new("ShaderNodeTexWave")
    wave.location = (-520, 80)
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 15.0
    wave.inputs["Distortion"].default_value = 3.0
    wave.inputs["Detail"].default_value = 3.0

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-520, -140)
    noise.inputs["Scale"].default_value = 9.0
    noise.inputs["Detail"].default_value = 5.0

    mix = nodes.new("ShaderNodeMixRGB")
    mix.location = (-250, 20)
    mix.blend_type = "MULTIPLY"
    mix.inputs["Fac"].default_value = 0.35

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (10, 20)
    ramp.color_ramp.elements[0].position = 0.22
    ramp.color_ramp.elements[0].color = (*dark, 1.0)
    ramp.color_ramp.elements[1].position = 0.86
    ramp.color_ramp.elements[1].color = (*light, 1.0)

    bump = nodes.new("ShaderNodeBump")
    bump.location = (250, -140)
    bump.inputs["Strength"].default_value = 0.12

    links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(wave.outputs["Color"], mix.inputs["Color1"])
    links.new(noise.outputs["Color"], mix.inputs["Color2"])
    links.new(mix.outputs["Color"], ramp.inputs["Fac"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(ramp.outputs["Color"], _socket(principled, "Base Color"))
    links.new(bump.outputs["Normal"], _socket(principled, "Normal"))
    _socket(principled, "Roughness").default_value = roughness
    return material


def _log_wood_material() -> bpy.types.Material:
    cached = _CACHE.get("Wall_LogWood")
    if cached:
        return cached

    material, nodes, links, principled = _new_material("Wall_LogWood")
    mapping = _texture_mapping(nodes, links, (1.35, 1.35, 4.4))

    log_wave = nodes.new("ShaderNodeTexWave")
    log_wave.location = (-600, 100)
    log_wave.wave_type = "BANDS"
    log_wave.bands_direction = "Z"
    log_wave.inputs["Scale"].default_value = 8.5
    log_wave.inputs["Distortion"].default_value = 0.8
    log_wave.inputs["Detail"].default_value = 3.0

    grain_wave = nodes.new("ShaderNodeTexWave")
    grain_wave.location = (-600, -120)
    grain_wave.wave_type = "BANDS"
    grain_wave.bands_direction = "X"
    grain_wave.inputs["Scale"].default_value = 18.0
    grain_wave.inputs["Distortion"].default_value = 5.0
    grain_wave.inputs["Detail"].default_value = 4.0

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-600, -320)
    noise.inputs["Scale"].default_value = 9.5
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.55

    color_ramp = nodes.new("ShaderNodeValToRGB")
    color_ramp.location = (-260, 90)
    color_ramp.color_ramp.elements[0].position = 0.22
    color_ramp.color_ramp.elements[0].color = (0.18, 0.10, 0.06, 1.0)
    color_ramp.color_ramp.elements[1].position = 0.84
    color_ramp.color_ramp.elements[1].color = (0.34, 0.20, 0.11, 1.0)

    grain_mix = nodes.new("ShaderNodeMixRGB")
    grain_mix.location = (10, 40)
    grain_mix.blend_type = "MULTIPLY"
    grain_mix.inputs["Fac"].default_value = 0.22

    bump = nodes.new("ShaderNodeBump")
    bump.location = (270, -120)
    bump.inputs["Strength"].default_value = 0.28
    bump.inputs["Distance"].default_value = 0.06

    links.new(mapping.outputs["Vector"], log_wave.inputs["Vector"])
    links.new(mapping.outputs["Vector"], grain_wave.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(log_wave.outputs["Fac"], color_ramp.inputs["Fac"])
    links.new(color_ramp.outputs["Color"], grain_mix.inputs["Color1"])
    links.new(grain_wave.outputs["Color"], grain_mix.inputs["Color2"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(grain_mix.outputs["Color"], _socket(principled, "Base Color"))
    links.new(bump.outputs["Normal"], _socket(principled, "Normal"))
    _socket(principled, "Roughness").default_value = 0.68
    return material


def wall_material(style: str, profile: str = "default") -> bpy.types.Material:
    if style == "log_wood":
        return _log_wood_material()
    if style == "siding":
        return _siding_material()
    if style == "brick":
        return _brick_material()
    if style == "stone":
        return _stone_like_material(
            "Wall_stone",
            (0.42, 0.41, 0.39),
            (0.68, 0.66, 0.63),
            scale=(3.1, 3.1, 3.1),
            bump_strength=0.18,
        )
    if style == "concrete":
        return _concrete_material()
    if profile == "barnhouse":
        return _dark_stucco_material()
    return _stucco_material()


def foundation_material() -> bpy.types.Material:
    return _stone_like_material(
        "Foundation",
        (0.30, 0.30, 0.31),
        (0.49, 0.48, 0.46),
        scale=(2.6, 2.6, 2.6),
        bump_strength=0.22,
    )


def wood_dark_material() -> bpy.types.Material:
    return _wood_material("Wood_Dark", (0.12, 0.08, 0.05), (0.24, 0.18, 0.11), 0.70)


def wood_cladding_material() -> bpy.types.Material:
    return _wood_material("Wood_Cladding", (0.08, 0.06, 0.05), (0.19, 0.15, 0.11), 0.74)


def cedar_material() -> bpy.types.Material:
    return _wood_material("Wood_Cedar", (0.53, 0.34, 0.17), (0.75, 0.56, 0.33), 0.64)


def oak_material() -> bpy.types.Material:
    return _wood_material("Wood_Oak", (0.42, 0.28, 0.13), (0.64, 0.47, 0.25), 0.58)


def room_floor_material(zone: str) -> bpy.types.Material:
    palette = {
        "public": ((0.66, 0.55, 0.39), 0.60),
        "private": ((0.63, 0.50, 0.33), 0.62),
        "service": ((0.48, 0.48, 0.46), 0.86),
        "entry": ((0.52, 0.49, 0.44), 0.80),
        "circulation": ((0.61, 0.47, 0.31), 0.60),
        "sauna": ((0.74, 0.60, 0.38), 0.66),
    }
    color, roughness = palette.get(zone, palette["public"])
    return _base_material(f"RoomFloor_{zone}", color, roughness=roughness)


def frame_material() -> bpy.types.Material:
    return _base_material("Frame", (0.18, 0.19, 0.21), roughness=0.26, metallic=0.22)


def trim_material(profile: str = "default") -> bpy.types.Material:
    if profile == "suburban":
        return _base_material("Trim_OffWhite", (0.93, 0.93, 0.90), roughness=0.58, metallic=0.0)
    if profile == "cabin":
        return _base_material("Trim_ArcticWhite", (0.95, 0.95, 0.93), roughness=0.50, metallic=0.0)
    return frame_material()


def glass_material(style: str = "clear") -> bpy.types.Material:
    presets = {
        "clear": ("Glass", (0.86, 0.94, 1.0, 1.0), 0.015, 1.45, 0.06),
        "graphite": ("Glass_Graphite", (0.28, 0.32, 0.36, 1.0), 0.028, 1.46, 0.18),
        "mirror": ("Glass_Mirror", (0.42, 0.46, 0.49, 1.0), 0.008, 1.50, 0.30),
    }
    material_name, tint, roughness, ior, _transparent_mix = presets.get(style, presets["clear"])
    cached = _CACHE.get(material_name)
    if cached:
        return cached

    material = bpy.data.materials.new(name=material_name)
    material.use_nodes = True
    _configure_transparency(material)
    if hasattr(material, "use_raytrace_refraction"):
        material.use_raytrace_refraction = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (780, 0)

    glass = nodes.new("ShaderNodeBsdfGlass")
    glass.location = (70, -40)
    glass.inputs["Color"].default_value = tint
    glass.inputs["Roughness"].default_value = roughness
    glass.inputs["IOR"].default_value = ior

    glossy = nodes.new("ShaderNodeBsdfGlossy")
    glossy.location = (70, 180)
    glossy.inputs["Color"].default_value = (*tint[:3], 1.0)
    glossy.inputs["Roughness"].default_value = max(0.02, roughness * 1.4)

    transparent = nodes.new("ShaderNodeBsdfTransparent")
    transparent.location = (70, -250)

    fresnel = nodes.new("ShaderNodeFresnel")
    fresnel.location = (-170, 110)
    fresnel.inputs["IOR"].default_value = ior

    mix_reflect = nodes.new("ShaderNodeMixShader")
    mix_reflect.location = (320, 60)

    light_path = nodes.new("ShaderNodeLightPath")
    light_path.location = (-180, -210)

    mix_shadow = nodes.new("ShaderNodeMixShader")
    mix_shadow.location = (560, 0)

    links.new(fresnel.outputs["Fac"], mix_reflect.inputs["Fac"])
    links.new(glossy.outputs["BSDF"], mix_reflect.inputs[1])
    links.new(glass.outputs["BSDF"], mix_reflect.inputs[2])
    links.new(light_path.outputs["Is Shadow Ray"], mix_shadow.inputs["Fac"])
    links.new(mix_reflect.outputs["Shader"], mix_shadow.inputs[1])
    links.new(transparent.outputs["BSDF"], mix_shadow.inputs[2])
    links.new(mix_shadow.outputs["Shader"], output.inputs["Surface"])

    _CACHE[material_name] = material
    return material


def door_material(style: str) -> bpy.types.Material:
    if style == "classic":
        return _wood_material("Door_Classic", (0.10, 0.15, 0.25), (0.24, 0.30, 0.44), 0.42)
    return _base_material("Door_Modern", (0.11, 0.12, 0.14), roughness=0.30, metallic=0.10)


def roof_material(roof_type: str, profile: str = "default") -> bpy.types.Material:
    if profile == "suburban":
        cached = _CACHE.get("Roof_Shingle")
        if cached:
            return cached

        material, nodes, links, principled = _new_material("Roof_Shingle")
        mapping = _texture_mapping(nodes, links, (4.2, 16.0, 4.2))

        wave = nodes.new("ShaderNodeTexWave")
        wave.location = (-520, 70)
        wave.wave_type = "BANDS"
        wave.bands_direction = "Y"
        wave.inputs["Scale"].default_value = 28.0
        wave.inputs["Distortion"].default_value = 0.35
        wave.inputs["Detail"].default_value = 2.0

        noise = nodes.new("ShaderNodeTexNoise")
        noise.location = (-520, -160)
        noise.inputs["Scale"].default_value = 20.0
        noise.inputs["Detail"].default_value = 8.0
        noise.inputs["Roughness"].default_value = 0.55

        mix = nodes.new("ShaderNodeMixRGB")
        mix.location = (-220, 30)
        mix.blend_type = "MULTIPLY"
        mix.inputs["Fac"].default_value = 0.18

        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.location = (20, 30)
        ramp.color_ramp.elements[0].position = 0.22
        ramp.color_ramp.elements[0].color = (0.16, 0.17, 0.19, 1.0)
        ramp.color_ramp.elements[1].position = 0.84
        ramp.color_ramp.elements[1].color = (0.25, 0.26, 0.29, 1.0)

        bump = nodes.new("ShaderNodeBump")
        bump.location = (260, -120)
        bump.inputs["Strength"].default_value = 0.20
        bump.inputs["Distance"].default_value = 0.05

        links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
        links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
        links.new(wave.outputs["Color"], mix.inputs["Color1"])
        links.new(noise.outputs["Color"], mix.inputs["Color2"])
        links.new(mix.outputs["Color"], ramp.inputs["Fac"])
        links.new(wave.outputs["Fac"], bump.inputs["Height"])
        links.new(ramp.outputs["Color"], _socket(principled, "Base Color"))
        links.new(bump.outputs["Normal"], _socket(principled, "Normal"))
        _socket(principled, "Roughness").default_value = 0.82
        return material

    if profile == "barnhouse":
        cached = _CACHE.get("Roof_StandingSeam")
        if cached:
            return cached

        material, nodes, links, principled = _new_material("Roof_StandingSeam")
        mapping = _texture_mapping(nodes, links, (2.8, 18.0, 2.8))

        wave = nodes.new("ShaderNodeTexWave")
        wave.location = (-520, 60)
        wave.wave_type = "BANDS"
        wave.bands_direction = "Y"
        wave.inputs["Scale"].default_value = 22.0
        wave.inputs["Distortion"].default_value = 0.4
        wave.inputs["Detail"].default_value = 1.0

        noise = nodes.new("ShaderNodeTexNoise")
        noise.location = (-520, -160)
        noise.inputs["Scale"].default_value = 11.0
        noise.inputs["Detail"].default_value = 6.0

        mix = nodes.new("ShaderNodeMixRGB")
        mix.location = (-220, 40)
        mix.blend_type = "MULTIPLY"
        mix.inputs["Fac"].default_value = 0.18

        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.location = (20, 40)
        ramp.color_ramp.elements[0].position = 0.32
        ramp.color_ramp.elements[0].color = (0.16, 0.17, 0.18, 1.0)
        ramp.color_ramp.elements[1].position = 0.84
        ramp.color_ramp.elements[1].color = (0.24, 0.25, 0.27, 1.0)

        bump = nodes.new("ShaderNodeBump")
        bump.location = (250, -120)
        bump.inputs["Strength"].default_value = 0.18
        bump.inputs["Distance"].default_value = 0.08

        links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
        links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
        links.new(wave.outputs["Color"], mix.inputs["Color1"])
        links.new(noise.outputs["Color"], mix.inputs["Color2"])
        links.new(mix.outputs["Color"], ramp.inputs["Fac"])
        links.new(wave.outputs["Fac"], bump.inputs["Height"])
        links.new(ramp.outputs["Color"], _socket(principled, "Base Color"))
        links.new(bump.outputs["Normal"], _socket(principled, "Normal"))
        _socket(principled, "Roughness").default_value = 0.62
        _socket(principled, "Metallic").default_value = 0.72
        return material

    if profile == "cabin":
        cached = _CACHE.get("Roof_BarrelTile")
        if cached:
            return cached

        material, nodes, links, principled = _new_material("Roof_BarrelTile")
        mapping = _texture_mapping(nodes, links, (2.4, 9.0, 2.4))

        wave = nodes.new("ShaderNodeTexWave")
        wave.location = (-520, 70)
        wave.wave_type = "BANDS"
        wave.bands_direction = "Y"
        wave.inputs["Scale"].default_value = 15.0
        wave.inputs["Distortion"].default_value = 0.25
        wave.inputs["Detail"].default_value = 1.0

        noise = nodes.new("ShaderNodeTexNoise")
        noise.location = (-520, -160)
        noise.inputs["Scale"].default_value = 14.0
        noise.inputs["Detail"].default_value = 6.0
        noise.inputs["Roughness"].default_value = 0.55

        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.location = (-220, 30)
        ramp.color_ramp.elements[0].position = 0.22
        ramp.color_ramp.elements[0].color = (0.31, 0.17, 0.11, 1.0)
        ramp.color_ramp.elements[1].position = 0.82
        ramp.color_ramp.elements[1].color = (0.45, 0.24, 0.16, 1.0)

        mix = nodes.new("ShaderNodeMixRGB")
        mix.location = (20, 20)
        mix.blend_type = "MULTIPLY"
        mix.inputs["Fac"].default_value = 0.18

        bump = nodes.new("ShaderNodeBump")
        bump.location = (250, -120)
        bump.inputs["Strength"].default_value = 0.20
        bump.inputs["Distance"].default_value = 0.05

        links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
        links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
        links.new(wave.outputs["Color"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], mix.inputs["Color1"])
        links.new(noise.outputs["Color"], mix.inputs["Color2"])
        links.new(wave.outputs["Fac"], bump.inputs["Height"])
        links.new(mix.outputs["Color"], _socket(principled, "Base Color"))
        links.new(bump.outputs["Normal"], _socket(principled, "Normal"))
        _socket(principled, "Roughness").default_value = 0.62
        return material

    if roof_type == "flat":
        return _base_material("Roof_Flat", (0.21, 0.22, 0.24), roughness=0.88)
    return _base_material("Roof_Slope", (0.16, 0.13, 0.12), roughness=0.90)


def ground_material(profile: str = "default") -> bpy.types.Material:
    if profile == "barnhouse":
        return _base_material("Ground_Barnhouse", (0.30, 0.41, 0.27), roughness=0.99)
    if profile == "suburban":
        return _base_material("Ground_Suburban", (0.48, 0.60, 0.38), roughness=0.97)
    return _base_material("Ground", (0.28, 0.38, 0.23), roughness=0.98)


def paving_material(kind: str = "default") -> bpy.types.Material:
    if kind == "gravel":
        return _stone_like_material(
            "Gravel",
            (0.34, 0.33, 0.31),
            (0.56, 0.54, 0.50),
            scale=(8.0, 8.0, 8.0),
            bump_strength=0.18,
        )
    return _stone_like_material(
        "Paving",
        (0.43, 0.42, 0.40),
        (0.60, 0.58, 0.55),
        scale=(4.0, 4.0, 4.0),
        bump_strength=0.12,
    )


def terrace_material(profile: str = "default") -> bpy.types.Material:
    if profile == "cabin":
        return _wood_material("Terrace_Cabin", (0.33, 0.22, 0.14), (0.49, 0.34, 0.20), 0.70)
    if profile == "barnhouse":
        return _base_material("Terrace_Barnhouse", (0.34, 0.28, 0.21), roughness=0.82)
    return _base_material("Terrace", (0.69, 0.66, 0.61), roughness=0.88)


def metal_material() -> bpy.types.Material:
    return _base_material("Metal", (0.55, 0.57, 0.60), roughness=0.30, metallic=0.65)
