from __future__ import annotations


ALLOWED_ROOF_TYPES = {"gable", "hip", "flat"}
ALLOWED_WINDOW_STYLES = {"modern", "classic", "square"}
ALLOWED_WALL_MATERIALS = {"stucco", "brick", "stone", "concrete", "siding", "log_wood"}
ALLOWED_ENTRANCE_STYLES = {"modern", "classic"}
ALLOWED_ARCH_STYLES = {"modern_villa", "grand_estate", "classic_luxury_mansion", "scandinavian_barnhouse", "traditional_suburban", "rustic_log_cabin"}


def validate_generation_inputs(params: dict) -> list[str]:
    errors: list[str] = []

    width = float(params.get("width", 0.0))
    depth = float(params.get("depth", 0.0))
    floors = int(params.get("floors", 0))
    floor_height = float(params.get("floor_height", 0.0))
    roof_type = str(params.get("roof_type", ""))
    roof_pitch = float(params.get("roof_pitch", 0.0))
    front_windows = int(params.get("window_count_front", 0))

    if width < 6.0 or width > 60.0:
        errors.append("Width must stay between 6 and 60 meters.")
    if depth < 6.0 or depth > 45.0:
        errors.append("Depth must stay between 6 and 45 meters.")
    if floors < 1 or floors > 5:
        errors.append("Floors must stay between 1 and 5.")
    if floor_height < 2.6 or floor_height > 4.8:
        errors.append("Floor height must stay between 2.6 and 4.8 meters.")
    if roof_type not in ALLOWED_ROOF_TYPES:
        errors.append("Roof type must be gable, hip or flat.")
    if roof_type != "flat" and not (10.0 <= roof_pitch <= 55.0):
        errors.append("Roof pitch for gable/hip roofs must stay between 10 and 55 degrees.")
    if params.get("window_style") not in ALLOWED_WINDOW_STYLES:
        errors.append("Window style is invalid.")
    if params.get("wall_material") not in ALLOWED_WALL_MATERIALS:
        errors.append("Wall material is invalid.")
    if params.get("entrance_style") not in ALLOWED_ENTRANCE_STYLES:
        errors.append("Entrance style is invalid.")
    if params.get("arch_style") not in ALLOWED_ARCH_STYLES:
        errors.append("Architectural style is invalid.")
    if params.get("has_balcony") and floors < 2:
        errors.append("Balcony requires at least 2 floors.")
    if front_windows < 0 or front_windows > 9:
        errors.append("Front window count must stay between 0 and 9.")
    if floors == 1 and front_windows > 0 and front_windows % 2 == 1:
        errors.append(
            "A single-floor facade with a centered entrance requires an even manual front window count."
        )

    return errors
