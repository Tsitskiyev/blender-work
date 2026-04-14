from __future__ import annotations

import math
import re
from typing import Any

from engine.constraints import ConstraintGraph
from engine.space_planner import plan_interior
from engine.specs import (
    BalconySpec,
    DoorSpec,
    EntranceSpec,
    EnvironmentSpec,
    FacadeLayoutSpec,
    FeatureSpec,
    GarageSpec,
    OpeningSpec,
    ResolvedSpec,
    RoomSpec,
    RoofSpec,
    TerraceSpec,
)


STYLE_RULES = {
    "modern_villa": {
        "edge_margin_ratio": 0.09,
        "window_height_factor": 0.56,
        "window_width_factor": 0.78,
        "wall_thickness": 0.30,
        "foundation_height": 0.20,
        "roof_overhang": 0.35,
    },
    "grand_estate": {
        "edge_margin_ratio": 0.10,
        "window_height_factor": 0.61,
        "window_width_factor": 0.72,
        "wall_thickness": 0.34,
        "foundation_height": 0.28,
        "roof_overhang": 0.48,
    },
    "classic_luxury_mansion": {
        "edge_margin_ratio": 0.11,
        "window_height_factor": 0.66,
        "window_width_factor": 0.68,
        "wall_thickness": 0.36,
        "foundation_height": 0.34,
        "roof_overhang": 0.58,
    },
    "scandinavian_barnhouse": {
        "edge_margin_ratio": 0.07,
        "window_height_factor": 0.72,
        "window_width_factor": 0.88,
        "wall_thickness": 0.28,
        "foundation_height": 0.18,
        "roof_overhang": 0.02,
    },
    "traditional_suburban": {
        "edge_margin_ratio": 0.09,
        "window_height_factor": 0.60,
        "window_width_factor": 0.66,
        "wall_thickness": 0.30,
        "foundation_height": 0.26,
        "roof_overhang": 0.62,
    },
    "rustic_log_cabin": {
        "edge_margin_ratio": 0.08,
        "window_height_factor": 0.64,
        "window_width_factor": 0.74,
        "wall_thickness": 0.32,
        "foundation_height": 0.24,
        "roof_overhang": 0.62,
    },
}

WINDOW_STYLE_FACTORS = {
    "modern": (0.84, 0.56),
    "classic": (0.70, 0.68),
    "square": (0.82, 0.52),
}


def _value(graph: ConstraintGraph, name: str, default):
    return graph.value(name, default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _pair_average(first: str | None, second: str | None) -> float | None:
    if not first:
        return None
    values = [float(first)]
    if second:
        values.append(float(second))
    return sum(values) / len(values)


def _special_design_payload(graph: ConstraintGraph) -> dict[str, Any]:
    payload = _value(graph, "ai_design_payload", {})
    return payload if isinstance(payload, dict) else {}


def _extract_special_design(graph: ConstraintGraph) -> dict[str, Any]:
    notes = str(_value(graph, "special_notes", ""))
    text = _normalize_text(notes)
    force_symmetry = any(token in text for token in ("symmetr", "симметр"))
    explicit_asymmetry = any(
        token in text
        for token in (
            "asymmetr",
            "асимметр",
            "offset",
            "shifted block",
            "shifted blocks",
            "cantilever",
            "смещен",
            "смещён",
            "г-образ",
            "l-shaped",
            "g-shaped",
            "tower in one corner",
            "в одном из углов",
        )
    )
    cube_language = any(
        token in text
        for token in (
            "cubism",
            "cube house",
            "cube-shaped",
            "cubic house",
            "shifted blocks",
            "glass-to-glass",
            "frameless",
            "corner glazing",
            "slit window",
            "light line",
            "smart glass",
            "пневмолифт",
            "угловое остекление",
            "безрам",
            "щелев",
            "куб",
            "кубизм",
        )
    )

    barnhouse_language = any(
        token in text
        for token in (
            "barnhouse",
            "modern barnhouse",
            "barn house",
            "scandinavian",
            "scandi",
            "minimal country house",
            "minimalist country house",
        )
    )

    design: dict[str, Any] = {
        "is_chalet": "chalet" in text or "шале" in text,
        "is_log_cabin": any(
            token in text
            for token in (
                "log cabin",
                "log house",
                "rustic cabin",
                "timber house",
                "stacked round logs",
                "round logs",
                "interlocking corner joints",
                "log construction",
                "сруб",
                "бревенчат",
                "бревно",
            )
        ),
        "panoramic_front": "panoramic" in text or "панорам" in text,
        "is_cubism": any(
            token in text
            for token in (
                "cubism",
                "cube house",
                "shifted blocks",
                "cantilever",
                "futuristic",
                "high-tech",
                "corner glazing",
                "glass-to-glass",
                "frameless",
                "slit window",
                "light line",
                "pneumatic lift",
                "smart glass",
                "углов",
                "щелев",
                "пневмолифт",
            )
        ),
        "upper_wall_material": "",
        "is_barnhouse": barnhouse_language,
        "arch_style_override": "",
        "wood_cladding_mix": False,
        "standing_seam_roof": False,
        "minimal_landscape": False,
        "gravel_path": False,
        "backdrop_trees": False,
        "golden_hour": False,
        "warm_interior_glow": False,
        "public_room_front": False,
    }
    design["is_cubism"] = cube_language
    design["force_symmetry"] = force_symmetry and not explicit_asymmetry
    design["strict_prompt_only"] = True
    if design["is_barnhouse"]:
        design["arch_style_override"] = "scandinavian_barnhouse"
        design["panoramic_front"] = True
        design["wood_cladding_mix"] = True
        design["standing_seam_roof"] = True
        design["minimal_landscape"] = True
        design["gravel_path"] = True
        design["backdrop_trees"] = True
        design["public_room_front"] = True
        design["golden_hour"] = any(token in text for token in ("golden hour", "sunset", "warm light"))
        design["warm_interior_glow"] = any(token in text for token in ("warm light inside", "warm interior", "emission"))
        design["roof_overhang"] = 0.0 if any(token in text for token in ("no overhang", "without overhang", "without eaves", "no eaves")) else 0.02
        if any(token in text for token in ("wood cladding", "timber cladding", "planken", "charred wood", "burnt wood", "dark timber", "burnt pine")):
            design["upper_wall_material"] = "wood_dark"
    if design["is_cubism"]:
        design["roof_glass_guard"] = True
        design["frameless_glazing"] = True
        design["slit_windows"] = "slit window" in text or "light line" in text or "щелев" in text
        design["corner_glass"] = "corner glazing" in text or "glass-to-glass" in text or "углов" in text
        design["glass_tint"] = "graphite" if any(token in text for token in ("graphite", "mirror", "tint", "графит", "зеркал")) else "clear"
        design["cantilever_carport"] = any(token in text for token in ("carport", "parking", "электрокар", "гараж", "парков"))
        design["panel_cladding"] = (
            "anthracite_panels"
            if any(token in text for token in ("aluminum", "aluminium", "anthracite", "composite", "panel", "панел"))
            else "dark_concrete"
        )
        design["roof_lounge"] = any(token in text for token in ("solar", "lounger", "roof terrace", "planter", "шезлонг", "кадк", "солнеч"))
        design["emissive_joints"] = any(token in text for token in ("led", "emissive", "illumination", "светящ", "диод"))

    foundation_match = re.search(
        r"(?:plinth|foundation|цоколь|фундамент)[^0-9]{0,35}(\d+(?:\.\d+)?)(?:\s*(?:-|–|to)\s*(\d+(?:\.\d+)?))?\s*m",
        text,
    )
    if foundation_match:
        design["foundation_height"] = _pair_average(foundation_match.group(1), foundation_match.group(2))

    overhang_match = re.search(
        r"(?:overhang|вынос)[^0-9]{0,35}(\d+(?:\.\d+)?)(?:\s*(?:-|–|to)\s*(\d+(?:\.\d+)?))?\s*m",
        text,
    )
    if not overhang_match:
        overhang_match = re.search(
            r"(\d+(?:\.\d+)?)(?:\s*(?:-|–|to)\s*(\d+(?:\.\d+)?))?\s*m[^.]{0,25}(?:overhang|overhangs|свес|вынос)",
            text,
        )
    if overhang_match:
        design["roof_overhang"] = _pair_average(overhang_match.group(1), overhang_match.group(2))

    panoramic_match = re.search(
        r"panoramic[^.]{0,90}?(\d+(?:\.\d+)?)\s*m[^.]{0,20}(?:w|wide|width)[^.]{0,25}(\d+(?:\.\d+)?)\s*m[^.]{0,20}(?:h|height)",
        text,
    )
    if panoramic_match:
        design["panoramic_width"] = float(panoramic_match.group(1))
        design["panoramic_height"] = float(panoramic_match.group(2))

    bedroom_window_match = re.search(
        r"(?:bedroom windows|спальн)[^.]{0,90}?(\d+(?:\.\d+)?)\s*m[^.]{0,20}(?:w|wide|width|шир)[^.]{0,25}(\d+(?:\.\d+)?)\s*m[^.]{0,20}(?:h|height|выс)",
        text,
    )
    if bedroom_window_match:
        design["bedroom_window_width"] = float(bedroom_window_match.group(1))
        design["bedroom_window_height"] = float(bedroom_window_match.group(2))

    balcony_depth_match = re.search(
        r"(?:balcony|балкон)[^.]{0,60}?(\d+(?:\.\d+)?)\s*m[^.]{0,20}(?:deep|depth|ширин)",
        text,
    )
    if not balcony_depth_match:
        balcony_depth_match = re.search(
            r"(\d+(?:\.\d+)?)\s*m[^.]{0,20}(?:deep|depth)[^.]{0,35}(?:balcony|балкон)",
            text,
        )
    if balcony_depth_match:
        design["balcony_depth"] = float(balcony_depth_match.group(1))

    shift_match = re.search(
        r"(?:shift|offset|cantilever)[^.]{0,60}?(\d+(?:\.\d+)?)(?:\s*(?:-|–|to)\s*(\d+(?:\.\d+)?))?\s*m",
        text,
    )
    if shift_match:
        design["upper_shift_x"] = _pair_average(shift_match.group(1), shift_match.group(2))
    elif design.get("is_cubism"):
        design["upper_shift_x"] = 2.75

    if design.get("slit_windows"):
        slit_match = re.search(
            r"(?:slit|light line|щелев)[^.]{0,60}?(\d+(?:\.\d+)?)\s*(?:m|метр|cm|см)",
            text,
        )
        if slit_match:
            slit_value = float(slit_match.group(1))
            if slit_value > 1.0:
                slit_value = slit_value / 100.0
            design["slit_window_height"] = slit_value
        else:
            design["slit_window_height"] = 0.35

    if design.get("corner_glass"):
        design["corner_glass_corner"] = "front_left"

    if ("dark timber" in text or "темн" in text or "wood cladding" in text or "дерев" in text) and design["is_chalet"]:
        design["upper_wall_material"] = "wood_dark"
    if design["is_log_cabin"]:
        design["arch_style_override"] = "rustic_log_cabin"
        design["wall_material_override"] = "log_wood"
        design["window_trim"] = True
        design["trim_boards"] = True
        design["backdrop_trees"] = True
        design["shrubs"] = True
        design["lawn"] = True
        design["gabled_window_wall"] = any(
            token in text
            for token in ("gabled window wall", "gable window wall", "open gabled dormer", "matches the roof pitch")
        )
        design["porch_balustrade"] = any(
            token in text for token in ("balustrade", "balusters", "spindle", "turned balusters", "перила", "балюстрад")
        )
        design["porch_lean_to"] = any(
            token in text for token in ("lean-to roof", "lean to roof", "shed-style", "shed roof", "porch roof")
        )
        design["door_lantern"] = any(token in text for token in ("lantern", "фонарь"))
        design["brick_plinth"] = any(
            token in text
            for token in ("brick plinth", "brick plinth course", "red-brick plinth", "brick course", "кирпичный цоколь", "цоколь")
        )
        if any(token in text for token in ("barrel tile", "barrel tiles", "clay barrel", "clay tiles", "черепиц", "roof tiles")):
            design["roof_finish"] = "barrel_tile"
        design["roof_overhang"] = max(float(design.get("roof_overhang", 0.62) or 0.62), 0.55)
    return design


def _planner_notes(graph: ConstraintGraph) -> str:
    return str(_value(graph, "special_notes", ""))
    payload = _special_design_payload(graph)
    notes = str(_value(graph, "special_notes", ""))
    payload_notes = " ".join(str(item) for item in payload.get("constraint_notes", []) if item)
    architectural_concept = str(payload.get("architectural_concept", ""))
    stylistic_uniqueness = str(payload.get("stylistic_uniqueness", ""))
    facade_strategy = str(payload.get("facade_strategy", ""))
    technical_instruction = str(payload.get("technical_instruction_markdown", ""))
    future_parser_notes = " ".join(
        str(item)
        for item in payload.get("space_program", {}).get("future_parser_notes", [])
        if item
    )
    return " ".join(
        value
        for value in [
            notes,
            payload_notes,
            architectural_concept,
            stylistic_uniqueness,
            facade_strategy,
            technical_instruction,
            future_parser_notes,
        ]
        if value
    )


def _merged_prompt_text(graph: ConstraintGraph) -> str:
    payload = _special_design_payload(graph)
    notes = str(_value(graph, "special_notes", "")).strip()
    fragments: list[str] = [notes]
    for key in ("architectural_concept", "stylistic_uniqueness", "facade_strategy", "technical_instruction_markdown"):
        value = str(payload.get(key, "")).strip()
        if value:
            fragments.append(value)
    fragments.extend(
        str(item).strip()
        for item in payload.get("constraint_notes", [])
        if item and "forced to" not in str(item).lower() and "has_" not in str(item).lower()
    )
    fragments.extend(
        str(item).strip()
        for item in payload.get("space_program", {}).get("future_parser_notes", [])
        if item
    )
    return " ".join(fragment for fragment in fragments if fragment)


def _planner_notes_v2(graph: ConstraintGraph) -> str:
    return _merged_prompt_text(graph)


def _strict_prompt_option(graph: ConstraintGraph, special: dict[str, Any], field_name: str, explicit_key: str) -> bool:
    value = bool(_value(graph, field_name, False))
    if not special.get("strict_prompt_only") or not special.get("notes_present"):
        return value
    return bool(special.get(explicit_key, False))


def _extract_special_design_v2(graph: ConstraintGraph) -> dict[str, Any]:
    design = dict(_extract_special_design(graph))
    text = _normalize_text(_merged_prompt_text(graph))

    design["notes_present"] = bool(text)
    design["strict_prompt_only"] = True
    design["requested_columns"] = any(token in text for token in (" column", " columns", "square columns", "supported by two simple square columns"))
    design["requested_pediment"] = any(token in text for token in ("pediment",))
    design["requested_portico"] = any(token in text for token in ("portico",))
    design["requested_garage"] = any(token in text for token in ("garage", "garage door", "two-car garage", "two car garage"))
    design["requested_terrace"] = any(token in text for token in ("terrace", "patio", "roof deck", "rear deck"))
    design["requested_balcony"] = any(token in text for token in ("balcony",))
    design["requested_fence"] = any(token in text for token in ("fence",))
    design["requested_porch"] = any(token in text for token in ("porch", "covered porch", "veranda", "крыльцо", "веранда"))
    design["door_six_lites"] = any(token in text for token in ("6-pane glass insert", "6 pane glass insert", "6-pane", "6 pane"))

    if any(token in text for token in ("traditional suburban", "suburban family home", "suburban", "family home", "detached residential")):
        design["is_suburban"] = True
        design["arch_style_override"] = "traditional_suburban"

    if any(token in text for token in ("log cabin", "log house", "rustic cabin", "timber house", "stacked round logs", "round logs", "log construction", "сруб", "бревенчат")):
        design["is_log_cabin"] = True
        design["arch_style_override"] = "rustic_log_cabin"
        design["wall_material_override"] = "log_wood"
        design["window_trim"] = True
        design["trim_boards"] = True
        design["requested_porch"] = True

    if any(token in text for token in ("horizontal siding", "lap siding", "vinyl siding", "wooden lap siding", "horizontal lap siding", "clapboard", "siding texture")):
        design["wall_material_override"] = "siding"

    if any(token in text for token in ("cross-gable", "cross gable", "complex cross-gable")):
        design["cross_gable"] = True

    if any(token in text for token in ("eaves", "soffits", "fascia boards")):
        design["gutters"] = True if "gutter" in text or "downspout" in text else bool(design.get("gutters", False))
        design["trim_boards"] = True

    if any(token in text for token in ("muntin", "muntins", "grid", "grids", "double-hung", "double hung", "pane glass insert", "white trim")):
        design["window_grids"] = True
        design["window_trim"] = True

    if any(token in text for token in ("off-white", "off white", "off-white trim", "matte \"off-white\"", "matte off-white")):
        design["offwhite_trim"] = True

    if any(token in text for token in ("two individual sectional garage doors", "sectional garage doors")):
        design["garage_dual_doors"] = True
        design["garage_panels"] = True
        design["garage_top_windows"] = True if "windows at the top" in text or "row of small windows" in text else bool(design.get("garage_top_windows", False))

    if any(token in text for token in ("mailbox",)):
        design["mailbox"] = True
    if any(token in text for token in ("garden lights", "solar garden lights", "path lights", "small solar garden lights")):
        design["garden_lights"] = True
    if any(token in text for token in ("shrubs", "low-lying shrubs", "foundation shrubs")):
        design["shrubs"] = True
    if any(token in text for token in ("lawn", "grass", "particle system")):
        design["lawn"] = True
    if any(token in text for token in ("welcome mat",)):
        design["welcome_mat"] = True
    if any(token in text for token in ("hanging flower pot", "flower pot")):
        design["hanging_pot"] = True
    if any(token in text for token in ("electric meter", "outdoor outlet")):
        design["utility_meter"] = True
    if any(token in text for token in ("warm light inside", "warm light", "black hole effect", "warm interior")):
        design["warm_interior_glow"] = True
    if not design.get("roof_finish") and any(token in text for token in ("asphalt shingles", "bitumen tiles", "shingles")):
        design["roof_finish"] = "shingle"
    if "chimney" in text:
        design["chimney"] = True

    return design


def _auto_front_window_count(width: float, floors: int) -> int:
    count = max(2, min(7, round(width / 2.9)))
    if floors == 1 and count % 2 == 1:
        count += 1
    return count


def _generic_axes(length: float, count: int, edge_margin: float) -> list[float]:
    if count <= 0:
        return []

    usable_half = max(0.6, (length / 2.0) - edge_margin)
    if count % 2 == 1:
        side_count = count // 2
        step = usable_half / (side_count + 1) if side_count else usable_half
        positive = [round(step * index, 4) for index in range(1, side_count + 1)]
        return [-value for value in reversed(positive)] + [0.0] + positive

    side_count = count // 2
    step = usable_half / (side_count + 0.5)
    positive = [round(step * (index - 0.5), 4) for index in range(1, side_count + 1)]
    return [-value for value in reversed(positive)] + positive


def _front_axes(length: float, total_count: int, edge_margin: float, center_gap: float) -> tuple[list[float], list[float]]:
    if total_count <= 0:
        return [], []

    upper_has_center = total_count % 2 == 1
    side_count = total_count // 2
    if side_count <= 0:
        return [], [0.0] if upper_has_center else []

    usable_half = (length / 2.0) - edge_margin - (center_gap / 2.0)
    interval = usable_half / side_count
    positive = [
        round((center_gap / 2.0) + interval * (index - 0.5), 4)
        for index in range(1, side_count + 1)
    ]
    side_axes = [-value for value in reversed(positive)] + positive
    upper_axes = list(side_axes)
    if upper_has_center:
        upper_axes.insert(len(side_axes) // 2, 0.0)
    return side_axes, upper_axes


def _window_dimensions(
    floor_height: float,
    span: float,
    arch_style: str,
    window_style: str,
) -> tuple[float, float, float]:
    style_rules = STYLE_RULES[arch_style]
    width_factor, height_factor = WINDOW_STYLE_FACTORS[window_style]
    base_height_factor = style_rules["window_height_factor"] * (height_factor / 0.60)
    window_height = _clamp(floor_height * base_height_factor, 1.35, floor_height - 0.82)
    sill_height = _clamp((floor_height - window_height) * 0.58, 0.72, 1.05)
    window_width = _clamp(span * style_rules["window_width_factor"] * width_factor, 1.0, 2.15)
    return round(window_width, 4), round(window_height, 4), round(sill_height, 4)


def _build_facade_windows(
    facade: str,
    axes: list[float],
    floors: int,
    floor_height: float,
    window_width: float,
    window_height: float,
    sill_height: float,
    *,
    skip_ground_center: bool = False,
) -> list[OpeningSpec]:
    windows: list[OpeningSpec] = []
    for floor_index in range(floors):
        for axis in axes:
            if floor_index == 0 and skip_ground_center and abs(axis) < 0.0001:
                continue
            windows.append(
                OpeningSpec(
                    opening_id=f"{facade}_window_f{floor_index}_{len(windows):02d}",
                    facade=facade,
                    kind="window",
                    center=round(axis, 4),
                    bottom=round((floor_index * floor_height) + sill_height, 4),
                    width=window_width,
                    height=window_height,
                    floor_index=floor_index,
                )
            )
    return windows


def _resolve_roof(
    graph: ConstraintGraph,
    width: float,
    depth: float,
    wall_height: float,
    arch_style: str,
    special: dict[str, Any],
) -> RoofSpec:
    roof_type = _value(graph, "roof_type", "hip")
    pitch = float(_value(graph, "roof_pitch", 28.0))
    has_explicit_overhang = "roof_overhang" in special
    overhang = float(special.get("roof_overhang", STYLE_RULES[arch_style]["roof_overhang"]))
    if arch_style == "scandinavian_barnhouse" and roof_type == "gable":
        overhang = max(0.0, overhang)
    if arch_style == "rustic_log_cabin" and roof_type == "gable":
        overhang = max(0.55, overhang)
        pitch = _clamp(pitch, 24.0, 38.0)
    elif roof_type in {"gable", "hip"} and not has_explicit_overhang:
        overhang = max(0.46, overhang)
    if arch_style == "traditional_suburban" and roof_type == "gable":
        overhang = max(0.52, overhang)
        pitch = _clamp(pitch, 28.0, 38.0)

    if roof_type == "flat":
        return RoofSpec(
            roof_type="flat",
            pitch_degrees=0.0,
            overhang=round(max(0.18, overhang - 0.12), 4),
            ridge_height=0.22,
            base_elevation=round(wall_height, 4),
            thickness=0.22,
        )

    if roof_type == "gable":
        rise_span = width / 2.0
        pitch = _clamp(pitch, 12.0, 50.0)
    else:
        rise_span = min(width, depth) / 2.0
        pitch = _clamp(pitch, 12.0, 42.0)

    return RoofSpec(
        roof_type=roof_type,
        pitch_degrees=round(pitch, 4),
        overhang=round(overhang, 4),
        ridge_height=round(rise_span * math.tan(math.radians(pitch)), 4),
        base_elevation=round(wall_height, 4),
        thickness=0.12 if arch_style == "scandinavian_barnhouse" else (0.18 if arch_style == "rustic_log_cabin" else 0.16),
    )


def _resolve_entrance(
    graph: ConstraintGraph,
    width: float,
    floor_height: float,
    foundation_height: float,
    arch_style: str,
    special: dict[str, Any],
) -> EntranceSpec:
    entrance_style = _value(graph, "entrance_style", "modern")
    has_columns = _strict_prompt_option(graph, special, "has_columns", "requested_columns")
    has_pediment = _strict_prompt_option(graph, special, "has_pediment", "requested_pediment")
    has_portico = _strict_prompt_option(graph, special, "has_portico", "requested_portico")

    entrance_scale = {
        "modern_villa": 1.0,
        "grand_estate": 1.08,
        "classic_luxury_mansion": 1.14,
        "scandinavian_barnhouse": 0.94,
        "traditional_suburban": 0.98,
        "rustic_log_cabin": 0.92,
    }[arch_style]
    if entrance_style == "classic":
        entrance_scale += 0.06

    door_width = _clamp(1.24 * entrance_scale, 1.22, 1.65)
    door_height = _clamp(floor_height * 0.77, 2.2, 2.55)
    if arch_style == "scandinavian_barnhouse":
        door_width = _clamp(1.10 * entrance_scale, 1.05, 1.22)
        door_height = _clamp(floor_height * 0.82, 2.35, 2.55)
    if arch_style == "rustic_log_cabin":
        door_width = _clamp(1.02 * entrance_scale, 0.98, 1.18)
        door_height = _clamp(floor_height * 0.79, 2.2, 2.45)
    edge_margin = max(1.0, width * STYLE_RULES[arch_style]["edge_margin_ratio"])
    if special.get("is_cubism"):
        door_width = _clamp(1.34 * entrance_scale, 1.28, 1.7)
        door_height = _clamp(floor_height * 0.62, 2.65, 3.15)
        max_center = (width / 2.0) - edge_margin - (door_width / 2.0) - 0.2
        door_center = round(min(max_center, width * 0.33), 4)
        has_portico = False
        has_columns = False if not bool(_value(graph, "has_columns", False)) else has_columns
        has_pediment = False if not bool(_value(graph, "has_pediment", False)) else has_pediment
    elif arch_style == "scandinavian_barnhouse" and special.get("panoramic_front") and not special.get("force_symmetry"):
        max_center = (width / 2.0) - edge_margin - (door_width / 2.0) - 0.25
        door_center = round(min(max_center, width * 0.34), 4)
    elif arch_style == "rustic_log_cabin":
        max_center = (width / 2.0) - edge_margin - (door_width / 2.0) - 0.4
        door_center = round(min(max_center, width * 0.24), 4)
    elif special.get("panoramic_front"):
        max_center = (width / 2.0) - edge_margin - (door_width / 2.0) - 0.2
        door_center = round(min(max_center, width * 0.33), 4)
    else:
        door_center = 0.0

    if special.get("force_symmetry"):
        door_center = 0.0

    stoop_width = max(door_width + 1.0, 3.0 + (0.5 if has_columns else 0.0))
    stoop_depth = 1.25 + (0.35 if has_portico else 0.0)
    if arch_style == "traditional_suburban":
        stoop_width = max(stoop_width, 3.6)
        stoop_depth = max(stoop_depth, 1.45 if not special.get("porch_gable") else 1.85)
    if arch_style == "scandinavian_barnhouse":
        stoop_width = max(2.4, door_width + 0.82)
        stoop_depth = 1.65
    if arch_style == "rustic_log_cabin":
        stoop_width = max(5.0, min(width * 0.44, door_width + 4.0))
        stoop_depth = 2.4 if special.get("requested_porch") else 1.45
    canopy_depth = 0.0 if not has_portico else (1.45 if entrance_style == "modern" else 1.8)
    canopy_thickness = 0.12 if has_portico else 0.0
    column_radius = 0.12 if entrance_style == "modern" else 0.15
    column_height = door_height + 0.25
    pediment_height = 0.0 if not has_pediment else (0.48 if entrance_style == "modern" else 0.62)

    return EntranceSpec(
        door=DoorSpec(
            center=door_center,
            width=round(door_width, 4),
            height=round(door_height, 4),
            bottom=round(max(0.02, foundation_height * 0.5), 4),
            reveal_depth=0.06,
            style=entrance_style,
        ),
        style=entrance_style,
        has_columns=has_columns,
        has_pediment=has_pediment,
        has_portico=has_portico,
        stoop_width=round(min(width * 0.46, stoop_width), 4),
        stoop_depth=round(stoop_depth, 4),
        canopy_depth=round(canopy_depth, 4),
        canopy_thickness=round(canopy_thickness, 4),
        column_radius=round(column_radius, 4),
        column_height=round(column_height, 4),
        column_count=2 if has_columns else 0,
        pediment_height=round(pediment_height, 4),
    )


def _resolve_barnhouse_front_facade(
    width: float,
    floor_height: float,
    entrance: EntranceSpec,
    special: dict[str, Any],
) -> FacadeLayoutSpec:
    edge_margin = round(max(0.95, width * 0.08), 4)
    glass_bottom = 0.06
    glass_height = _clamp(float(special.get("panoramic_height", floor_height - 0.22)), 2.35, floor_height - 0.12)
    windows: list[OpeningSpec] = []

    if special.get("force_symmetry"):
        center_gap = max(entrance.door.width + 0.92, width * 0.18)
        span = ((width - (edge_margin * 2.0)) - center_gap) / 2.0
        unit_width = _clamp(span - 0.18, 2.6, width * 0.34)
        offset = round((center_gap / 2.0) + (unit_width / 2.0) + 0.12, 4)
        for index, center in enumerate((-offset, offset)):
            windows.append(
                OpeningSpec(
                    opening_id=f"front_window_panorama_f0_{index:02d}",
                    facade="front",
                    kind="window",
                    center=round(center, 4),
                    bottom=round(glass_bottom, 4),
                    width=round(unit_width, 4),
                    height=round(glass_height, 4),
                    floor_index=0,
                    mullion_count=3,
                )
            )
        axes = [-offset, offset]
        facade_window_width = unit_width
    else:
        left_limit = (-width / 2.0) + edge_margin
        right_limit = entrance.door.center - (entrance.door.width / 2.0) - 0.72
        clear_width = max(4.8, right_limit - left_limit)
        panoramic_width = _clamp(float(special.get("panoramic_width", clear_width - 0.15)), 4.8, min(width * 0.68, clear_width))
        panorama_center = round(left_limit + (panoramic_width / 2.0), 4)
        windows.append(
            OpeningSpec(
                opening_id="front_window_panorama_f0_00",
                facade="front",
                kind="window",
                center=panorama_center,
                bottom=round(glass_bottom, 4),
                width=round(panoramic_width, 4),
                height=round(glass_height, 4),
                floor_index=0,
                mullion_count=4,
            )
        )
        axes = [panorama_center]
        facade_window_width = panoramic_width

    return FacadeLayoutSpec(
        facade="front",
        length=round(width, 4),
        edge_margin=edge_margin,
        center_gap=round(max(entrance.door.width + 0.92, width * 0.18), 4),
        axes=axes,
        window_width=round(facade_window_width, 4),
        window_height=round(glass_height, 4),
        sill_height=round(glass_bottom, 4),
        windows=windows,
    )


def _resolve_custom_front_facade(
    width: float,
    floors: int,
    floor_height: float,
    entrance: EntranceSpec,
    special: dict[str, Any],
    *,
    balcony_requested: bool,
) -> FacadeLayoutSpec:
    edge_margin = round(max(1.0, width * 0.10), 4)
    panoramic_width = _clamp(float(special.get("panoramic_width", 4.0)), 2.8, width * 0.45)
    panoramic_height = _clamp(float(special.get("panoramic_height", 2.8)), 2.2, floor_height - 0.08)
    ground_bottom = round(max(0.10, (floor_height - panoramic_height) * 0.25), 4)
    bedroom_window_width = _clamp(float(special.get("bedroom_window_width", 1.5)), 1.2, 1.9)
    bedroom_window_height = _clamp(float(special.get("bedroom_window_height", 2.2)), 1.8, floor_height - 0.18)
    upper_bottom = round(floor_height + max(0.28, (floor_height - bedroom_window_height) * 0.42), 4)

    windows = [
        OpeningSpec(
            opening_id="front_window_panorama_f0_00",
            facade="front",
            kind="window",
            center=0.0,
            bottom=ground_bottom,
            width=round(panoramic_width, 4),
            height=round(panoramic_height, 4),
            floor_index=0,
            mullion_count=4,
        )
    ]

    upper_centers: list[float] = []
    if floors >= 2:
        side_center = round(_clamp((width * 0.28), 2.2, (width / 2.0) - edge_margin - (bedroom_window_width / 2.0)), 4)
        if balcony_requested:
            windows.append(
                OpeningSpec(
                    opening_id="front_balcony_opening_f1_01",
                    facade="front",
                    kind="window",
                    center=0.0,
                    bottom=upper_bottom,
                    width=1.8,
                    height=round(bedroom_window_height, 4),
                    floor_index=1,
                    mullion_count=2,
                )
            )
            upper_centers.append(0.0)
        for index, center in enumerate((-side_center, side_center), start=2):
            windows.append(
                OpeningSpec(
                    opening_id=f"front_window_f1_{index:02d}",
                    facade="front",
                    kind="window",
                    center=center,
                    bottom=upper_bottom,
                    width=round(bedroom_window_width, 4),
                    height=round(bedroom_window_height, 4),
                    floor_index=1,
                    mullion_count=1,
                )
            )
            upper_centers.append(center)

    axes = sorted(upper_centers) if upper_centers else [0.0]
    return FacadeLayoutSpec(
        facade="front",
        length=round(width, 4),
        edge_margin=edge_margin,
        center_gap=round(max(entrance.door.width + 0.8, panoramic_width + 0.35), 4),
        axes=axes,
        window_width=round(bedroom_window_width, 4),
        window_height=round(bedroom_window_height, 4),
        sill_height=round(ground_bottom, 4),
        windows=windows,
    )


def _resolve_suburban_front_facade(
    width: float,
    floors: int,
    floor_height: float,
    entrance: EntranceSpec,
) -> FacadeLayoutSpec:
    edge_margin = round(max(1.05, width * 0.10), 4)
    lower_window_width = 1.02
    upper_window_width = 0.96
    window_height = _clamp(floor_height * 0.69, 1.72, 1.98)
    sill_height = 0.72
    center_gap = round(max(entrance.door.width + 1.18, width * 0.22), 4)
    lower_offset = round((center_gap / 2.0) + 0.82, 4)
    upper_offsets = [-3.0, -1.3, 1.3, 3.0] if width >= 11.2 else [-2.55, -0.95, 0.95, 2.55]

    windows: list[OpeningSpec] = [
        OpeningSpec(
            opening_id="front_suburban_f0_00",
            facade="front",
            kind="window",
            center=round(-lower_offset, 4),
            bottom=0.72,
            width=lower_window_width,
            height=round(window_height, 4),
            floor_index=0,
            mullion_count=3,
        ),
        OpeningSpec(
            opening_id="front_suburban_f0_01",
            facade="front",
            kind="window",
            center=round(lower_offset, 4),
            bottom=0.72,
            width=lower_window_width,
            height=round(window_height, 4),
            floor_index=0,
            mullion_count=3,
        ),
    ]
    if floors >= 2:
        for index, center in enumerate(upper_offsets, start=2):
            windows.append(
                OpeningSpec(
                    opening_id=f"front_suburban_f1_{index:02d}",
                    facade="front",
                    kind="window",
                    center=round(center, 4),
                    bottom=round(floor_height + sill_height, 4),
                    width=upper_window_width,
                    height=round(window_height, 4),
                    floor_index=1,
                    mullion_count=3,
                )
            )

    return FacadeLayoutSpec(
        facade="front",
        length=round(width, 4),
        edge_margin=edge_margin,
        center_gap=center_gap,
        axes=[round(value, 4) for value in upper_offsets] if floors >= 2 else [round(-lower_offset, 4), round(lower_offset, 4)],
        window_width=upper_window_width,
        window_height=round(window_height, 4),
        sill_height=sill_height,
        windows=windows,
    )


def _resolve_log_cabin_front_facade(
    width: float,
    floors: int,
    floor_height: float,
    entrance: EntranceSpec,
    special: dict[str, Any],
) -> FacadeLayoutSpec:
    edge_margin = round(max(1.0, width * 0.08), 4)
    left_cluster_center = round(-max(2.3, width * 0.28), 4)
    cluster_spacing = 1.16
    ground_bottom = 0.72
    ground_width = 0.92
    ground_height = _clamp(floor_height * 0.66, 1.7, 1.95)
    upper_bottom = round(floor_height + 0.54, 4)
    upper_height = _clamp((floor_height * 0.90), 2.0, 2.38)

    windows: list[OpeningSpec] = []
    for index, center in enumerate((left_cluster_center - cluster_spacing, left_cluster_center, left_cluster_center + cluster_spacing)):
        windows.append(
            OpeningSpec(
                opening_id=f"log_cabin_front_f0_{index:02d}",
                facade="front",
                kind="window",
                center=round(center, 4),
                bottom=ground_bottom,
                width=ground_width,
                height=round(ground_height, 4),
                floor_index=0,
                mullion_count=2,
            )
        )

    right_window_center = round(min((width / 2.0) - edge_margin - 0.7, entrance.door.center + 1.75), 4)
    windows.append(
        OpeningSpec(
            opening_id="log_cabin_front_right_f0",
            facade="front",
            kind="window",
            center=right_window_center,
            bottom=ground_bottom,
            width=0.96,
            height=round(ground_height, 4),
            floor_index=0,
            mullion_count=1,
        )
    )

    if floors >= 2:
        if special.get("gabled_window_wall"):
            upper_centers = [
                round(left_cluster_center - 0.98, 4),
                round(left_cluster_center - 0.30, 4),
                round(left_cluster_center + 0.30, 4),
                round(left_cluster_center + 0.98, 4),
            ]
            upper_widths = [0.60, 0.82, 0.82, 0.60]
            upper_heights = [1.82, upper_height, upper_height, 1.82]
            for index, (center, width_value, height_value) in enumerate(zip(upper_centers, upper_widths, upper_heights), start=4):
                windows.append(
                    OpeningSpec(
                        opening_id=f"log_cabin_gable_f1_{index:02d}",
                        facade="front",
                        kind="window",
                        center=center,
                        bottom=upper_bottom,
                        width=width_value,
                        height=round(height_value, 4),
                        floor_index=1,
                        mullion_count=1,
                    )
                )
        windows.append(
            OpeningSpec(
                opening_id="log_cabin_front_right_f1",
                facade="front",
                kind="window",
                center=round(right_window_center, 4),
                bottom=round(floor_height + 0.74, 4),
                width=0.88,
                height=1.58,
                floor_index=1,
                mullion_count=1,
            )
        )

    axes = sorted({round(window.center, 4) for window in windows if window.floor_index == min(1, floors - 1)})
    return FacadeLayoutSpec(
        facade="front",
        length=round(width, 4),
        edge_margin=edge_margin,
        center_gap=round(max(entrance.door.width + 1.2, width * 0.18), 4),
        axes=axes,
        window_width=ground_width,
        window_height=round(ground_height, 4),
        sill_height=ground_bottom,
        windows=windows,
    )


def _resolve_cubism_facades(
    width: float,
    depth: float,
    floors: int,
    floor_height: float,
    entrance: EntranceSpec,
    special: dict[str, Any],
) -> tuple[FacadeLayoutSpec, FacadeLayoutSpec, FacadeLayoutSpec, FacadeLayoutSpec]:
    shift_x = float(special.get("upper_shift_x", 2.75 if floors >= 2 else 0.0))
    slit_height = _clamp(float(special.get("slit_window_height", 0.35)), 0.28, 0.42)
    corner_width = _clamp(width * 0.34, 3.2, 4.2)
    corner_height = _clamp(floor_height - 0.22, 2.5, floor_height - 0.08)
    corner_front_center_ground = round((-(width / 2.0)) + 0.72 + (corner_width / 2.0), 4)
    corner_front_center_upper = round(corner_front_center_ground + (shift_x if floors >= 2 else 0.0), 4)
    corner_side_center = round((-(depth / 2.0)) + 0.72 + (corner_width / 2.0), 4)
    slit_width_front = _clamp(width * 0.34, 2.8, 3.8)
    slit_width_rear = _clamp(width * 0.42, 3.2, 4.4)
    glass_bottom = 0.08
    upper_bottom = round(floor_height + 0.08, 4)
    slit_bottom_ground = round(max(0.7, floor_height * 0.46), 4)
    slit_bottom_upper = round(floor_height + max(0.9, floor_height * 0.48), 4)
    vertical_slit_bottom_ground = round(max(0.42, floor_height * 0.12), 4)
    vertical_slit_bottom_upper = round((floor_height) + max(0.42, floor_height * 0.12), 4)
    vertical_slit_top_margin = 0.42
    vertical_slit_height = _clamp(floor_height - (vertical_slit_bottom_ground + vertical_slit_top_margin), 2.2, floor_height - 0.9)

    front_windows: list[OpeningSpec] = [
        OpeningSpec(
            opening_id="cubism_front_corner_f0",
            facade="front",
            kind="window",
            center=corner_front_center_ground,
            bottom=glass_bottom,
            width=round(corner_width, 4),
            height=round(corner_height, 4),
            floor_index=0,
            mullion_count=0,
            frame_style="frameless",
        ),
    ]
    if floors >= 2:
        front_windows.extend(
            [
                OpeningSpec(
                    opening_id="cubism_front_corner_f1",
                    facade="front",
                    kind="window",
                    center=corner_front_center_upper,
                    bottom=upper_bottom,
                    width=round(corner_width, 4),
                    height=round(corner_height, 4),
                    floor_index=1,
                    mullion_count=0,
                    frame_style="frameless",
                ),
                OpeningSpec(
                    opening_id="cubism_front_slit_f1",
                    facade="front",
                    kind="window",
                    center=round(shift_x + (width * 0.18), 4),
                    bottom=slit_bottom_upper,
                    width=round(slit_width_front, 4),
                    height=round(slit_height, 4),
                    floor_index=1,
                    mullion_count=0,
                    frame_style="slit",
                ),
            ]
        )

    rear_windows: list[OpeningSpec] = []
    left_windows: list[OpeningSpec] = [
        OpeningSpec(
            opening_id="cubism_left_corner_f0",
            facade="left",
            kind="window",
            center=corner_side_center,
            bottom=glass_bottom,
            width=round(corner_width, 4),
            height=round(corner_height, 4),
            floor_index=0,
            mullion_count=0,
            frame_style="frameless",
        ),
    ]
    right_windows: list[OpeningSpec] = [
        OpeningSpec(
            opening_id="cubism_right_slit_f0",
            facade="right",
            kind="window",
            center=0.0,
            bottom=vertical_slit_bottom_ground,
            width=0.36,
            height=round(vertical_slit_height, 4),
            floor_index=0,
            mullion_count=0,
            frame_style="slit",
        )
    ]
    for floor_index in range(floors):
        floor_shift = shift_x if floor_index >= 1 else 0.0
        rear_windows.append(
            OpeningSpec(
                opening_id=f"cubism_rear_slit_f{floor_index}",
                facade="rear",
                kind="window",
                center=round(floor_shift - (width * 0.02), 4),
                bottom=round((floor_index * floor_height) + max(0.95, floor_height * 0.48), 4),
                width=round(slit_width_rear, 4),
                height=round(slit_height, 4),
                floor_index=floor_index,
                mullion_count=0,
                frame_style="slit",
            )
        )
    if floors >= 2:
        left_windows.append(
            OpeningSpec(
                opening_id="cubism_left_corner_f1",
                facade="left",
                kind="window",
                center=corner_side_center,
                bottom=upper_bottom,
                width=round(corner_width, 4),
                height=round(corner_height, 4),
                floor_index=1,
                mullion_count=0,
                frame_style="frameless",
            )
        )
        right_windows.append(
            OpeningSpec(
                opening_id="cubism_right_slit_f1",
                facade="right",
                kind="window",
                center=round(depth * 0.10, 4),
                bottom=vertical_slit_bottom_upper,
                width=0.36,
                height=round(vertical_slit_height, 4),
                floor_index=1,
                mullion_count=0,
                frame_style="slit",
            )
        )

    front_facade = FacadeLayoutSpec(
        facade="front",
        length=round(width, 4),
        edge_margin=0.7,
        center_gap=round(abs(entrance.door.center) + 0.9, 4),
        axes=[opening.center for opening in front_windows if opening.floor_index >= min(1, floors - 1)],
        window_width=round(corner_width, 4),
        window_height=round(corner_height, 4),
        sill_height=glass_bottom,
        windows=front_windows,
    )
    rear_facade = FacadeLayoutSpec(
        facade="rear",
        length=round(width, 4),
        edge_margin=0.7,
        center_gap=0.0,
        axes=[opening.center for opening in rear_windows],
        window_width=round(slit_width_rear, 4),
        window_height=round(slit_height, 4),
        sill_height=slit_bottom_ground,
        windows=rear_windows,
    )
    left_facade = FacadeLayoutSpec(
        facade="left",
        length=round(depth, 4),
        edge_margin=0.7,
        center_gap=0.0,
        axes=[opening.center for opening in left_windows],
        window_width=round(corner_width, 4),
        window_height=round(corner_height, 4),
        sill_height=glass_bottom,
        windows=left_windows,
    )
    right_facade = FacadeLayoutSpec(
        facade="right",
        length=round(depth, 4),
        edge_margin=0.7,
        center_gap=0.0,
        axes=[opening.center for opening in right_windows],
        window_width=0.36,
        window_height=round(vertical_slit_height, 4),
        sill_height=slit_bottom_ground,
        windows=right_windows,
    )
    return front_facade, rear_facade, left_facade, right_facade


def _resolve_front_facade(
    graph: ConstraintGraph,
    width: float,
    floors: int,
    floor_height: float,
    arch_style: str,
    window_style: str,
    entrance: EntranceSpec,
    special: dict[str, Any],
    *,
    balcony_requested: bool,
) -> FacadeLayoutSpec:
    if arch_style == "rustic_log_cabin":
        return _resolve_log_cabin_front_facade(
            width,
            floors,
            floor_height,
            entrance,
            special,
        )
    if arch_style == "traditional_suburban":
        return _resolve_suburban_front_facade(
            width,
            floors,
            floor_height,
            entrance,
        )
    if special.get("is_barnhouse"):
        return _resolve_barnhouse_front_facade(
            width,
            floor_height,
            entrance,
            special,
        )
    if special.get("panoramic_front"):
        return _resolve_custom_front_facade(
            width,
            floors,
            floor_height,
            entrance,
            special,
            balcony_requested=balcony_requested,
        )

    style_rules = STYLE_RULES[arch_style]
    requested = int(_value(graph, "window_count_front", 0))
    total_count = requested if requested > 0 else _auto_front_window_count(width, floors)
    if special.get("force_symmetry") and requested <= 0 and floors >= 2 and total_count % 2 == 0:
        total_count += 1
    edge_margin = round(max(1.0, width * style_rules["edge_margin_ratio"]), 4)
    center_gap = round(max(entrance.door.width + 1.0, width * 0.22), 4)
    ground_axes, upper_axes = _front_axes(width, total_count, edge_margin, center_gap)

    if ground_axes:
        smallest_span = min(
            abs(ground_axes[0] - (-width / 2 + edge_margin)),
            abs((width / 2 - edge_margin) - ground_axes[-1]),
        )
    else:
        smallest_span = (width / 2) - edge_margin - (center_gap / 2)
    window_width, window_height, sill_height = _window_dimensions(
        floor_height,
        max(1.3, smallest_span * 1.55),
        arch_style,
        window_style,
    )
    windows = _build_facade_windows(
        "front",
        upper_axes,
        floors,
        floor_height,
        window_width,
        window_height,
        sill_height,
        skip_ground_center=True,
    )
    return FacadeLayoutSpec(
        facade="front",
        length=round(width, 4),
        edge_margin=edge_margin,
        center_gap=center_gap,
        axes=upper_axes,
        window_width=window_width,
        window_height=window_height,
        sill_height=sill_height,
        windows=windows,
    )


def _resolve_generic_facade(
    facade: str,
    length: float,
    floors: int,
    floor_height: float,
    arch_style: str,
    window_style: str,
    count: int,
) -> FacadeLayoutSpec:
    edge_margin = round(max(0.9, length * STYLE_RULES[arch_style]["edge_margin_ratio"]), 4)
    axes = _generic_axes(length, count, edge_margin)
    span = abs(axes[1] - axes[0]) if len(axes) >= 2 else max(1.5, length - (edge_margin * 2))
    window_width, window_height, sill_height = _window_dimensions(
        floor_height,
        span,
        arch_style,
        window_style,
    )
    windows = _build_facade_windows(
        facade,
        axes,
        floors,
        floor_height,
        window_width,
        window_height,
        sill_height,
    )
    return FacadeLayoutSpec(
        facade=facade,
        length=round(length, 4),
        edge_margin=edge_margin,
        center_gap=0.0,
        axes=axes,
        window_width=window_width,
        window_height=window_height,
        sill_height=sill_height,
        windows=windows,
    )


def _apply_suburban_window_details(*facades: FacadeLayoutSpec) -> None:
    for facade in facades:
        for opening in facade.windows:
            if opening.kind == "window" and opening.frame_style == "standard":
                opening.mullion_count = max(3, int(opening.mullion_count))


def _resolve_garage(graph: ConstraintGraph, width: float, depth: float, floor_height: float) -> GarageSpec:
    special = _extract_special_design_v2(graph)
    enabled = _strict_prompt_option(graph, special, "has_garage", "requested_garage")
    if not enabled:
        return GarageSpec(False, "right", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    dual_doors = bool(special.get("garage_dual_doors"))
    garage_width = _clamp(width * 0.38, 4.5, 7.4)
    if dual_doors:
        garage_width = max(5.8, garage_width)
    garage_depth = _clamp(depth * 0.58 if dual_doors else depth * 0.72, 5.2, depth)
    return GarageSpec(
        enabled=True,
        side="right",
        width=round(garage_width, 4),
        depth=round(garage_depth, 4),
        height=round(max(2.7, floor_height * 0.94), 4),
        front_setback=round(min(1.1, depth * 0.12), 4),
        door_width=round(2.5 if dual_doors else _clamp(garage_width * 0.48, 2.5, 3.2), 4),
        door_height=2.25,
    )


def _resolve_terrace(
    graph: ConstraintGraph,
    width: float,
    depth: float,
    entrance: EntranceSpec,
    special: dict[str, Any],
) -> TerraceSpec:
    enabled = _strict_prompt_option(graph, special, "has_terrace", "requested_terrace")
    if not enabled:
        return TerraceSpec(False, 0.0, 0.0, 0.0, 0.0, 0.0)
    if special.get("is_barnhouse"):
        return TerraceSpec(
            True,
            round(max(2.6, entrance.stoop_width + 0.4), 4),
            1.8,
            0.14,
            round(entrance.door.center, 4),
            0.0,
        )
    if special.get("is_cubism"):
        shift_x = abs(float(special.get("upper_shift_x", 2.75)))
        terrace_width = _clamp(shift_x - 0.22, 2.2, width * 0.38)
        terrace_depth = _clamp(depth * 0.34, 2.6, depth * 0.44)
        center_x = round((-(width / 2.0) + (terrace_width / 2.0)) if float(special.get("upper_shift_x", 0.0)) >= 0 else ((width / 2.0) - (terrace_width / 2.0)), 4)
        center_y = round((depth / 2.0) - (terrace_depth / 2.0) - 0.55, 4)
        return TerraceSpec(
            True,
            round(terrace_width, 4),
            round(terrace_depth, 4),
            round(float(_value(graph, "floor_height", 3.0)), 4),
            center_x,
            center_y,
        )
    terrace_width = max(entrance.stoop_width + 1.2, min(width * 0.58, 8.2))
    if special.get("panoramic_front"):
        terrace_width = max(terrace_width, float(special.get("panoramic_width", 4.0)) + 1.6)
    return TerraceSpec(True, round(terrace_width, 4), 2.8, 0.16, 0.0, 0.0)


def _resolve_balcony(
    graph: ConstraintGraph,
    width: float,
    floor_height: float,
    floors: int,
    special: dict[str, Any],
    metadata: dict[str, float],
) -> BalconySpec:
    enabled = _strict_prompt_option(graph, special, "has_balcony", "requested_balcony") and floors >= 2
    if not enabled:
        return BalconySpec(False, 0.0, 0.0, 0.0, 0, 0.0)

    room_width = float(metadata.get("master_width", width * 0.30))
    center_x = float(metadata.get("master_center_x", 0.0))
    balcony_width = _clamp(room_width - 0.35, 3.0, width * 0.78)
    balcony_depth = _clamp(float(special.get("balcony_depth", 1.45)), 1.2, 2.2)
    return BalconySpec(
        enabled=True,
        width=round(balcony_width, 4),
        depth=round(balcony_depth, 4),
        elevation=round(floor_height + 0.14, 4),
        floor_index=1,
        center_x=round(center_x, 4),
    )


def _shift_upper_rooms_and_features(
    room_specs: list[RoomSpec],
    feature_specs: list[FeatureSpec],
    shift_x: float,
) -> tuple[list[RoomSpec], list[FeatureSpec]]:
    if abs(shift_x) < 0.0001:
        return room_specs, feature_specs

    shifted_rooms = [
        RoomSpec(
            room_id=room.room_id,
            name=room.name,
            floor_index=room.floor_index,
            center_x=round(room.center_x + (shift_x if room.floor_index >= 1 else 0.0), 4),
            center_y=room.center_y,
            width=room.width,
            depth=room.depth,
            height=room.height,
            zone=room.zone,
            notes=room.notes,
            finish=room.finish,
        )
        for room in room_specs
    ]

    shifted_features: list[FeatureSpec] = []
    for feature in feature_specs:
        feature_shift = 0.0
        if feature.floor_index >= 1 or feature.kind in {"skylight"}:
            feature_shift = shift_x
        shifted_features.append(
            FeatureSpec(
                feature_id=feature.feature_id,
                kind=feature.kind,
                floor_index=feature.floor_index,
                center_x=round(feature.center_x + feature_shift, 4),
                center_y=feature.center_y,
                width=feature.width,
                depth=feature.depth,
                height=feature.height,
                rotation_degrees=feature.rotation_degrees,
                material_hint=feature.material_hint,
                notes=feature.notes,
            )
        )
    return shifted_rooms, shifted_features


def resolve(graph: ConstraintGraph) -> ResolvedSpec:
    width = float(_value(graph, "width", 12.0))
    depth = float(_value(graph, "depth", 10.0))
    floors = int(_value(graph, "floors", 2))
    floor_height = float(_value(graph, "floor_height", 3.1))
    arch_style = str(_value(graph, "arch_style", "modern_villa"))
    window_style = str(_value(graph, "window_style", "modern"))
    wall_material = str(_value(graph, "wall_material", "stucco"))

    special = _extract_special_design_v2(graph)
    if special.get("arch_style_override"):
        arch_style = str(special["arch_style_override"])
    if special.get("wall_material_override"):
        wall_material = str(special["wall_material_override"])
    if arch_style not in STYLE_RULES:
        arch_style = "modern_villa"
    if arch_style == "scandinavian_barnhouse" and wall_material == "concrete":
        wall_material = "stucco"

    style_rules = STYLE_RULES[arch_style]
    wall_height = round(floors * floor_height, 4)
    wall_thickness = round(style_rules["wall_thickness"], 4)
    floor_slab_thickness = 0.18
    foundation_height = round(float(special.get("foundation_height", style_rules["foundation_height"])), 4)

    entrance = _resolve_entrance(graph, width, floor_height, foundation_height, arch_style, special)
    roof = _resolve_roof(graph, width, depth, wall_height, arch_style, special)
    ai_payload = _special_design_payload(graph)
    design_profile = (
        "suburban"
        if arch_style == "traditional_suburban"
        else (
            "cabin"
            if arch_style == "rustic_log_cabin"
            else ("barnhouse" if special.get("is_barnhouse") else ("cubism" if special.get("is_cubism") else "default"))
        )
    )
    room_specs, feature_specs, metadata = plan_interior(
        width,
        depth,
        wall_thickness,
        floor_height,
        floors,
        roof.roof_type,
        ai_payload.get("space_program"),
        special_notes=_planner_notes_v2(graph),
        has_garage=_strict_prompt_option(graph, special, "has_garage", "requested_garage"),
        design_profile=design_profile,
    )
    if special.get("is_cubism") and floors >= 2:
        room_specs, feature_specs = _shift_upper_rooms_and_features(
            room_specs,
            feature_specs,
            float(special.get("upper_shift_x", 2.75)),
        )
    balcony_requested = _strict_prompt_option(graph, special, "has_balcony", "requested_balcony") and floors >= 2
    if special.get("is_cubism"):
        front_facade, rear_facade, left_facade, right_facade = _resolve_cubism_facades(
            width,
            depth,
            floors,
            floor_height,
            entrance,
            special,
        )
    else:
        front_facade = _resolve_front_facade(
            graph,
            width,
            floors,
            floor_height,
            arch_style,
            window_style,
            entrance,
            special,
            balcony_requested=balcony_requested,
        )
        if arch_style == "scandinavian_barnhouse":
            rear_count = 2
            side_count = 2
        elif arch_style == "rustic_log_cabin":
            rear_count = 2
            side_count = 1
        elif arch_style == "traditional_suburban":
            rear_count = 4
            side_count = 2
        else:
            rear_count = max(2, min(max(2, len(front_facade.axes) or 2), round(width / 3.1)))
            side_count = max(1, min(4, round(depth / 3.0)))
        rear_facade = _resolve_generic_facade(
            "rear",
            width,
            floors,
            floor_height,
            arch_style,
            window_style,
            rear_count,
        )
        left_facade = _resolve_generic_facade(
            "left",
            depth,
            floors,
            floor_height,
            arch_style,
            window_style,
            side_count,
        )
        right_facade = _resolve_generic_facade(
            "right",
            depth,
            floors,
            floor_height,
            arch_style,
            window_style,
            side_count,
        )
        if arch_style == "traditional_suburban":
            _apply_suburban_window_details(front_facade, rear_facade, left_facade, right_facade)

    garage = _resolve_garage(graph, width, depth, floor_height)
    terrace = _resolve_terrace(graph, width, depth, entrance, special)
    balcony = _resolve_balcony(graph, width, floor_height, floors, special, metadata)
    environment = EnvironmentSpec(
        lot_margin=12.0,
        path_width=round(max(1.6, entrance.door.width + (0.55 if arch_style == "scandinavian_barnhouse" else (0.65 if arch_style == "rustic_log_cabin" else 0.8))), 4),
        path_length=6.8 if arch_style == "rustic_log_cabin" else (7.0 if arch_style == "scandinavian_barnhouse" else 8.0),
        driveway_width=round(max(3.0, garage.door_width + 0.55), 4) if garage.enabled else 0.0,
        fence_enabled=_strict_prompt_option(graph, special, "has_fence", "requested_fence"),
    )

    return ResolvedSpec(
        width=round(width, 4),
        depth=round(depth, 4),
        floors=floors,
        floor_height=round(floor_height, 4),
        wall_height=wall_height,
        wall_thickness=wall_thickness,
        floor_slab_thickness=floor_slab_thickness,
        foundation_height=foundation_height,
        arch_style=arch_style,
        window_style=window_style,
        wall_material=wall_material,
        roof=roof,
        front_facade=front_facade,
        rear_facade=rear_facade,
        left_facade=left_facade,
        right_facade=right_facade,
        entrance=entrance,
        garage=garage,
        terrace=terrace,
        balcony=balcony,
        environment=environment,
        room_specs=room_specs,
        feature_specs=feature_specs,
        design_profile=design_profile,
        design_options={
            "force_symmetry": bool(special.get("force_symmetry", False)),
            "strict_prompt_only": bool(special.get("strict_prompt_only", False)),
            "notes_present": bool(special.get("notes_present", False)),
            "upper_shift_x": round(float(special.get("upper_shift_x", 0.0)), 4),
            "corner_glass": bool(special.get("corner_glass", False)),
            "corner_glass_corner": str(special.get("corner_glass_corner", "")),
            "slit_window_height": round(float(special.get("slit_window_height", 0.0)), 4),
            "frameless_glazing": bool(special.get("frameless_glazing", False)),
            "glass_tint": str(special.get("glass_tint", "clear")),
            "cantilever_carport": bool(special.get("cantilever_carport", False)),
            "panel_cladding": str(special.get("panel_cladding", "")),
            "roof_glass_guard": bool(special.get("roof_glass_guard", False)),
            "roof_lounge": bool(special.get("roof_lounge", False)),
            "emissive_joints": bool(special.get("emissive_joints", False)),
            "wood_cladding_mix": bool(special.get("wood_cladding_mix", False)),
            "standing_seam_roof": bool(special.get("standing_seam_roof", False)),
            "minimal_landscape": bool(special.get("minimal_landscape", False)),
            "gravel_path": bool(special.get("gravel_path", False)),
            "backdrop_trees": bool(special.get("backdrop_trees", False)),
            "golden_hour": bool(special.get("golden_hour", False)),
            "warm_interior_glow": bool(special.get("warm_interior_glow", False)),
            "public_room_front": bool(special.get("public_room_front", False)),
            "cross_gable": bool(special.get("cross_gable", False)),
            "porch_gable": bool(special.get("porch_gable", False)),
            "chimney": bool(special.get("chimney", False)),
            "gutters": bool(special.get("gutters", False)),
            "trim_boards": bool(special.get("trim_boards", False)),
            "window_trim": bool(special.get("window_trim", False)),
            "window_grids": bool(special.get("window_grids", False)),
            "garage_dual_doors": bool(special.get("garage_dual_doors", False)),
            "garage_top_windows": bool(special.get("garage_top_windows", False)),
            "garage_panels": bool(special.get("garage_panels", False)),
            "mailbox": bool(special.get("mailbox", False)),
            "garden_lights": bool(special.get("garden_lights", False)),
            "shrubs": bool(special.get("shrubs", False)),
            "lawn": bool(special.get("lawn", False)),
            "welcome_mat": bool(special.get("welcome_mat", False)),
            "hanging_pot": bool(special.get("hanging_pot", False)),
            "utility_meter": bool(special.get("utility_meter", False)),
            "door_six_lites": bool(special.get("door_six_lites", False)),
            "roof_finish": str(special.get("roof_finish", "")),
            "offwhite_trim": bool(special.get("offwhite_trim", False)),
            "porch_lean_to": bool(special.get("porch_lean_to", False)),
            "porch_balustrade": bool(special.get("porch_balustrade", False)),
            "door_lantern": bool(special.get("door_lantern", False)),
            "brick_plinth": bool(special.get("brick_plinth", False)),
            "gabled_window_wall": bool(special.get("gabled_window_wall", False)),
            "requested_porch": bool(special.get("requested_porch", False)),
        },
        upper_wall_material=str(special.get("upper_wall_material", "")),
        special_notes=str(_value(graph, "special_notes", "")),
        note_overrides=list(graph.notes),
    )
