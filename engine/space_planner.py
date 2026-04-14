from __future__ import annotations

import math
import re
from typing import Any

from engine.specs import FeatureSpec, RoomSpec


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _parse_dimensions(text: str) -> tuple[float, float] | None:
    numbers = [float(match) for match in re.findall(r"\d+(?:[.,]\d+)?", text.replace(",", "."))]
    if len(numbers) < 2:
        return None
    return numbers[0], numbers[1]


def _preferred_pair(room: dict[str, Any] | None, default: tuple[float, float]) -> tuple[float, float]:
    if not room:
        return default
    parsed = _parse_dimensions(str(room.get("dimensions_m", "")))
    if parsed:
        return parsed
    area = float(room.get("target_area_sqm", default[0] * default[1]))
    side = math.sqrt(max(1.0, area))
    return side, side


def _make_stub(name: str, area: float, dimensions: str, notes: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "target_area_sqm": area,
        "dimensions_m": dimensions,
        "doors": "",
        "windows": "",
        "notes": notes,
    }


def _count_mentions(text: str, needles: tuple[str, ...]) -> int:
    normalized = _normalize(text)
    return sum(normalized.count(needle) for needle in needles)


def _room_spec(
    room: dict[str, Any] | None,
    room_id: str,
    floor_index: int,
    center_x: float,
    center_y: float,
    width: float,
    depth: float,
    height: float,
    zone: str,
    *,
    default_name: str,
    finish: str = "",
) -> RoomSpec:
    name = str(room.get("name", default_name)) if room else default_name
    notes = str(room.get("notes", "")) if room else ""
    return RoomSpec(
        room_id=room_id,
        name=name,
        floor_index=floor_index,
        center_x=round(center_x, 4),
        center_y=round(center_y, 4),
        width=round(max(0.8, width), 4),
        depth=round(max(0.8, depth), 4),
        height=round(height, 4),
        zone=zone,
        notes=notes,
        finish=finish,
    )


def _feature(
    feature_id: str,
    kind: str,
    floor_index: int,
    center_x: float,
    center_y: float,
    width: float,
    depth: float,
    height: float,
    *,
    rotation_degrees: float = 0.0,
    material_hint: str = "",
    notes: str = "",
) -> FeatureSpec:
    return FeatureSpec(
        feature_id=feature_id,
        kind=kind,
        floor_index=floor_index,
        center_x=round(center_x, 4),
        center_y=round(center_y, 4),
        width=round(width, 4),
        depth=round(depth, 4),
        height=round(height, 4),
        rotation_degrees=round(rotation_degrees, 4),
        material_hint=material_hint,
        notes=notes,
    )


def infer_space_program_from_notes(
    special_notes: str,
    floors: int,
    *,
    has_garage: bool,
) -> dict[str, Any]:
    text = _normalize(special_notes)
    room_program: list[dict[str, Any]] = [
        _make_stub("Entry", 8.0, "2.4 x 3.2", "First floor entry zone."),
        _make_stub("Hall 1 / Stair Core", 14.0, "3.5 x 4.0", "First floor circulation."),
        _make_stub("Open Space / Studio", 36.0, "6.0 x 6.0", "First floor living and dining."),
        _make_stub("Bath 1", 5.0, "2.0 x 2.5", "First floor guest bathroom."),
    ]

    if any(token in text for token in ("utility", "laundry", "technical", "mechanical", "tech room", "прач", "технич")):
        room_program.append(_make_stub("Utility", 7.5, "2.5 x 3.0", "First floor service room."))
    if any(token in text for token in ("sauna", "сауна")):
        room_program.append(_make_stub("Sauna", 9.0, "3.0 x 3.0", "First floor sauna near bath."))
    if any(token in text for token in ("office", "study", "cabinet", "кабинет")):
        office_floor_note = "Second floor office." if floors >= 2 else "First floor office."
        room_program.append(_make_stub("Office", 12.0, "3.0 x 4.0", office_floor_note))

    bedroom_mentions = _count_mentions(text, ("bedroom", "спальн"))
    if floors >= 2:
        room_program.extend(
            [
                _make_stub("Hall 2 / Landing", 12.0, "3.0 x 4.0", "Second floor circulation."),
                _make_stub("Master Bedroom", 22.0, "4.4 x 5.0", "Second floor private suite."),
                _make_stub("Bath 2", 7.0, "2.5 x 2.8", "Second floor bathroom."),
            ]
        )
        extra_bedrooms = max(0, bedroom_mentions - 1)
        if extra_bedrooms == 0 and any(token in text for token in ("guest room", "children", "kids", "детск", "гостев")):
            extra_bedrooms = 1
        for index in range(extra_bedrooms):
            room_program.append(_make_stub(f"Bedroom {index + 2}", 15.0, "3.6 x 4.2", "Second floor bedroom."))
        if any(token in text for token in ("closet", "wardrobe", "гардероб")):
            room_program.append(_make_stub("Closet", 6.0, "2.0 x 3.0", "Second floor closet."))

    if floors >= 3 and any(token in text for token in ("roof terrace", "rooftop", "terrace", "крыш", "эксплуатируем")):
        room_program.append(_make_stub("Roof Terrace", 35.0, "6.0 x 6.0", "Top floor rooftop lounge."))
    if floors >= 3 and any(token in text for token in ("technical room", "plant room", "hvac", "mechanical", "технич")):
        room_program.append(_make_stub("Technical Room", 12.0, "3.0 x 4.0", "Top floor service room."))

    if has_garage or any(token in text for token in ("garage", "carport", "parking", "гараж", "парков")):
        room_program.append(_make_stub("Garage / Carport", 24.0, "4.0 x 6.0", "First floor attached garage or carport."))

    return {
        "target_total_area_sqm": sum(float(room["target_area_sqm"]) for room in room_program),
        "zoning_strategy": "Heuristic fallback zoning from the brief.",
        "circulation_strategy": "Entry and circulation cores connect all rooms on each floor.",
        "room_program": room_program,
        "adjacency_rules": [],
        "future_parser_notes": [],
    }


def _explicit_floor(room: dict[str, Any], floors: int) -> int | None:
    haystack = _normalize(" ".join([str(room.get("name", "")), str(room.get("notes", ""))]))
    first_floor_tokens = (
        "ground floor",
        "first floor",
        "lower floor",
        "1st floor",
        "1f",
        "первый этаж",
        "1-й этаж",
    )
    second_floor_tokens = (
        "second floor",
        "upper floor",
        "2nd floor",
        "2f",
        "второй этаж",
        "2-й этаж",
    )
    top_floor_tokens = (
        "roof",
        "rooftop",
        "roof terrace",
        "top floor",
        "third floor",
        "3rd floor",
        "3f",
        "третий этаж",
        "крыш",
        "эксплуатируем",
    )
    if any(token in haystack for token in first_floor_tokens):
        return 0
    if any(token in haystack for token in second_floor_tokens):
        return min(1, floors - 1)
    if any(token in haystack for token in top_floor_tokens):
        return floors - 1
    return None


def _room_role(room: dict[str, Any]) -> str:
    name_text = _normalize(str(room.get("name", "")))
    notes_text = _normalize(str(room.get("notes", "")))
    combined = _normalize(f"{name_text} {notes_text}")

    core_name_roles = [
        ("bath", ("bath", "wc", "powder", "ensuite", "shower", "toilet", "ванн", "сануз", "душ")),
        ("master", ("master", "primary suite", "owner suite", "мастер", "родитель")),
        ("bedroom", ("bedroom", "guest room", "children", "kid", "nursery", "спальн", "детск", "гостев")),
        ("office", ("office", "study", "cabinet", "workspace", "кабинет")),
        ("closet", ("closet", "wardrobe", "walk-in", "гардероб")),
        ("utility", ("utility", "laundry", "mechanical", "technical", "plant room", "hvac", "прач", "технич")),
        ("sauna", ("sauna", "сауна")),
        ("garage", ("garage", "carport", "parking", "гараж", "парков")),
        ("balcony", ("balcony", "loggia", "лодж", "балкон")),
        ("exterior", ("roof terrace", "rooftop", "terrace", "patio", "deck", "эксплуатируем", "террас", "крыш")),
        (
            "public",
            (
                "open space",
                "studio",
                "living",
                "lounge",
                "family room",
                "dining",
                "kitchen",
                "гостин",
                "кухн",
                "столов",
            ),
        ),
        ("circulation", ("hall", "landing", "stair", "atrium", "bridge", "gallery", "холл", "лестн", "атриум")),
        ("entry", ("entry", "foyer", "vestibule", "mudroom", "прихож", "вестиб")),
    ]
    for role, needles in core_name_roles:
        if any(needle in name_text for needle in needles):
            return role

    fallback_roles = [
        ("bath", ("bath", "wc", "powder", "ensuite", "shower", "toilet", "ванн", "сануз", "душ")),
        ("master", ("master", "primary suite", "owner suite", "мастер", "родитель")),
        ("bedroom", ("bedroom", "guest room", "children", "kid", "nursery", "спальн", "детск")),
        ("office", ("office", "study", "cabinet", "workspace", "кабинет")),
        ("closet", ("closet", "wardrobe", "walk-in", "гардероб")),
        ("utility", ("utility", "laundry", "mechanical", "technical", "plant room", "hvac", "прач", "технич")),
        ("sauna", ("sauna", "сауна")),
        ("garage", ("garage", "carport", "parking", "гараж", "парков")),
        (
            "public",
            (
                "open space",
                "studio",
                "living",
                "lounge",
                "family room",
                "dining",
                "kitchen",
                "гостин",
                "кухн",
                "столов",
            ),
        ),
        ("circulation", ("hall", "landing", "stair", "atrium", "bridge", "gallery", "холл", "лестн", "атриум")),
        ("entry", ("entry", "foyer", "vestibule", "mudroom", "прихож", "вестиб")),
        ("exterior", ("roof terrace", "rooftop", "terrace", "patio", "deck", "эксплуатируем", "крыш")),
    ]
    for role, needles in fallback_roles:
        if any(needle in combined for needle in needles):
            return role
    return "other"


def _infer_floor(room: dict[str, Any], role: str, floors: int) -> int:
    explicit = _explicit_floor(room, floors)
    if explicit is not None:
        return explicit
    if floors <= 1:
        return 0

    haystack = _normalize(" ".join([str(room.get("name", "")), str(room.get("notes", ""))]))
    if any(token in haystack for token in ("roof", "rooftop", "roof terrace", "top floor", "third floor", "3rd floor", "крыш", "третий")):
        return floors - 1
    if role in {"entry", "public", "garage"}:
        return 0
    if role in {"master", "bedroom", "closet"}:
        return min(1, floors - 1)
    if role in {"utility", "sauna"}:
        if floors >= 3 and any(token in haystack for token in ("roof", "rooftop", "top", "plant", "hvac", "технич")):
            return floors - 1
        return 0
    if role == "office":
        return min(1, floors - 1)
    if role == "bath":
        if any(token in haystack for token in ("master", "ensuite", "upper", "second", "второй", "мастер")):
            return min(1, floors - 1)
        return 0
    if role == "circulation":
        return min(1, floors - 1)
    return 0


def _classify_room_program(room_program: list[dict[str, Any]], floors: int) -> list[dict[str, Any]]:
    classified: list[dict[str, Any]] = []
    for index, room in enumerate(room_program):
        role = _room_role(room)
        if role in {"balcony", "exterior"}:
            continue
        floor_index = _infer_floor(room, role, floors)
        classified.append(
            {
                "source": room,
                "role": role,
                "floor_index": floor_index,
                "order": index,
            }
        )
    return classified


def _take(entries: list[dict[str, Any]], role: str) -> list[dict[str, Any]]:
    taken = [entry for entry in entries if entry["role"] == role]
    for entry in taken:
        entries.remove(entry)
    return taken


def _first_or_stub(entries: list[dict[str, Any]], role: str, name: str, area: float, dimensions: str, notes: str) -> dict[str, Any]:
    matches = _take(entries, role)
    if matches:
        return matches[0]["source"]
    return _make_stub(name, area, dimensions, notes)


def _append_room(
    planned_rooms: list[RoomSpec],
    room: dict[str, Any] | None,
    room_id: str,
    floor_index: int,
    center_x: float,
    center_y: float,
    width: float,
    depth: float,
    floor_height: float,
    zone: str,
    default_name: str,
    *,
    finish: str = "",
) -> RoomSpec:
    spec = _room_spec(
        room,
        room_id,
        floor_index,
        center_x,
        center_y,
        width,
        depth,
        floor_height,
        zone,
        default_name=default_name,
        finish=finish,
    )
    planned_rooms.append(spec)
    return spec


def _split_span(total: float, count: int, minimum: float) -> list[float]:
    if count <= 0:
        return []
    values = [max(minimum, total / count) for _ in range(count)]
    scale = total / sum(values)
    return [value * scale for value in values]


def _zone_for_role(role: str) -> str:
    if role in {"master", "bedroom"}:
        return "private"
    if role == "public":
        return "public"
    if role == "sauna":
        return "sauna"
    if role in {"circulation"}:
        return "circulation"
    if role == "entry":
        return "entry"
    return "service"


def _room_wants_frontage(room: dict[str, Any] | None) -> bool:
    if not room:
        return False
    combined = _normalize(
        " ".join(
            [
                str(room.get("name", "")),
                str(room.get("notes", "")),
                str(room.get("windows", "")),
                str(room.get("doors", "")),
            ]
        )
    )
    return any(
        token in combined
        for token in (
            "panoramic",
            "terrace",
            "front facade",
            "floor-to-ceiling",
            "view",
            "light",
        )
    )


def _plan_first_floor(
    width: float,
    depth: float,
    floor_height: float,
    floor_entries: list[dict[str, Any]],
    *,
    floors: int,
    special_notes: str,
    design_profile: str,
) -> tuple[list[RoomSpec], list[FeatureSpec], dict[str, float]]:
    planned_rooms: list[RoomSpec] = []
    features: list[FeatureSpec] = []
    metadata: dict[str, float] = {}

    working = list(sorted(floor_entries, key=lambda item: item["order"]))
    entry_room = _first_or_stub(working, "entry", "Entry", 8.0, "2.6 x 3.2", "First floor entry.")
    hall_room = _first_or_stub(working, "circulation", "Hall 1 / Stair Core", 14.0, "3.5 x 4.2", "First floor circulation.")
    public_rooms = _take(working, "public")
    public_main = public_rooms[0]["source"] if public_rooms else _make_stub("Open Space / Studio", 36.0, "6.0 x 6.2", "First floor public room.")
    public_aux = public_rooms[1]["source"] if len(public_rooms) > 1 else None
    front_aux_candidates = _take(working, "bedroom") + _take(working, "office") + _take(working, "other")
    service_rooms = _take(working, "bath") + _take(working, "utility") + _take(working, "sauna")
    garage_rooms = _take(working, "garage")
    leftovers = working
    normalized_notes = _normalize(special_notes)
    public_prefers_front = design_profile == "barnhouse" or _room_wants_frontage(public_main) or any(
        token in normalized_notes for token in ("panoramic", "barnhouse", "terrace", "golden hour")
    )

    half_w = width / 2.0
    half_d = depth / 2.0
    side_width = _clamp(max(_preferred_pair(entry_room, (2.6, 3.2))[0], _preferred_pair(hall_room, (3.5, 4.2))[0], 3.2), 3.2, min(4.2, width * 0.40))
    left_width = max(4.0, width - side_width)
    if public_prefers_front:
        front_depth = _clamp(max(_preferred_pair(entry_room, (2.6, 3.2))[1], 2.8), 2.6, min(3.2, depth * 0.32))
        public_depth = _clamp(max(_preferred_pair(public_main, (6.0, 5.2))[1], 4.8), 4.8, min(5.4, depth * 0.58))
        rear_depth = max(3.2, depth - public_depth)
        hall_depth = max(3.6, depth - front_depth)
        if hall_depth + front_depth > depth:
            hall_depth = depth - front_depth
    else:
        front_depth = _clamp(_preferred_pair(entry_room, (2.6, 3.2))[1], 2.8, min(3.8, depth * 0.36))
        middle_depth = _clamp(max(_preferred_pair(hall_room, (3.5, 4.2))[1], 4.0), 3.8, min(4.8, depth * 0.42))
        rear_depth = max(2.4, depth - front_depth - middle_depth)
        if front_depth + middle_depth + rear_depth > depth:
            rear_depth = max(2.2, depth - front_depth - middle_depth)
        public_depth = middle_depth if front_aux_candidates else front_depth + middle_depth
        hall_depth = middle_depth + rear_depth

    left_x = -half_w + (left_width / 2.0)
    right_x = half_w - (side_width / 2.0)
    front_y = -half_d + (front_depth / 2.0)
    hall_y = -half_d + front_depth + (hall_depth / 2.0)
    rear_y = half_d - (rear_depth / 2.0)

    front_aux_room = front_aux_candidates.pop(0)["source"] if front_aux_candidates else public_aux
    if public_prefers_front:
        public_y = -half_d + (public_depth / 2.0)
        if front_aux_room:
            service_rooms.insert(0, front_aux_room)
            front_aux_room = None
    else:
        public_y = -half_d + front_depth + ((public_depth if not front_aux_room else public_depth) / 2.0)
        if front_aux_room:
            public_y = -half_d + front_depth + ((public_depth) / 2.0)

    if front_aux_room:
        front_aux_role = _room_role(front_aux_room)
        _append_room(
            planned_rooms,
            front_aux_room,
            "front_aux_f0",
            0,
            left_x,
            front_y,
            left_width,
            front_depth,
            floor_height,
            _zone_for_role(front_aux_role),
            "Ground Room",
            finish="cedar" if front_aux_role == "sauna" else "",
        )

    public_spec = _append_room(
        planned_rooms,
        public_main,
        "public_main_f0",
        0,
        left_x,
        public_y,
        left_width,
        public_depth,
        floor_height,
        "public",
        "Open Space",
    )
    _append_room(
        planned_rooms,
        entry_room,
        "entry_f0",
        0,
        right_x,
        front_y,
        side_width,
        front_depth,
        floor_height,
        "entry",
        "Entry",
    )
    hall_spec = _append_room(
        planned_rooms,
        hall_room,
        "hall_f0",
        0,
        right_x,
        hall_y,
        side_width,
        hall_depth,
        floor_height,
        "circulation",
        "Hall 1",
    )

    rear_queue = service_rooms + front_aux_candidates + [entry["source"] for entry in leftovers if entry["role"] != "garage"]
    if garage_rooms:
        metadata["garage_requested"] = 1.0

    if rear_queue:
        widths = _split_span(left_width, len(rear_queue), 2.0)
        cursor_x = -half_w
        for index, room in enumerate(rear_queue):
            room_width = widths[index]
            role = _room_role(room)
            _append_room(
                planned_rooms,
                room,
                f"rear_room_f0_{index}",
                0,
                cursor_x + (room_width / 2.0),
                rear_y,
                room_width,
                rear_depth,
                floor_height,
                _zone_for_role(role),
                "Service Room",
                finish="cedar" if role == "sauna" else "",
            )
            cursor_x += room_width

    if floors > 1:
        features.append(
            _feature(
                "stair_main",
                "stair",
                0,
                hall_spec.center_x,
                hall_spec.center_y,
                1.2,
                min(4.6, max(3.6, hall_spec.depth - 0.4)),
                floor_height,
                material_hint="oak",
                notes="Primary circulation stair.",
            )
        )
    if _wants_feature(normalized_notes, ("fireplace", "камин")):
        features.append(
            _feature(
                "fireplace_main",
                "fireplace",
                0,
                public_spec.center_x + (public_spec.width / 2.0) - 0.65,
                public_spec.center_y + (public_spec.depth / 2.0) - 1.15,
                1.15,
                0.45,
                floor_height - 0.18,
                material_hint="stone",
            )
        )
    return planned_rooms, features, metadata


def _plan_upper_floor(
    width: float,
    depth: float,
    floor_height: float,
    floor_entries: list[dict[str, Any]],
    roof_type: str,
    floor_index: int,
) -> tuple[list[RoomSpec], list[FeatureSpec], dict[str, float]]:
    planned_rooms: list[RoomSpec] = []
    features: list[FeatureSpec] = []
    metadata: dict[str, float] = {}

    working = list(sorted(floor_entries, key=lambda item: item["order"]))
    floor_label = floor_index + 1
    floor_note = f"Floor {floor_label}."
    hall_room = _first_or_stub(working, "circulation", f"Hall {floor_label} / Landing", 12.0, "3.0 x 4.0", floor_note)
    public_candidates = _take(working, "public")
    master_candidates = _take(working, "master")
    bedroom_candidates = _take(working, "bedroom")
    office_candidates = _take(working, "office") + _take(working, "other")
    service_rooms = _take(working, "bath") + _take(working, "closet") + _take(working, "utility") + _take(working, "sauna")

    primary_room = master_candidates[0]["source"] if master_candidates else (
        public_candidates.pop(0)["source"] if public_candidates else (
            bedroom_candidates.pop(0)["source"] if bedroom_candidates else (
                office_candidates.pop(0)["source"] if office_candidates else _make_stub(f"Upper Room {floor_label}A", 22.0, "4.4 x 5.0", floor_note)
            )
        )
    )
    front_right_room = bedroom_candidates.pop(0)["source"] if bedroom_candidates else (
        public_candidates.pop(0)["source"] if public_candidates else (
            office_candidates.pop(0)["source"] if office_candidates else _make_stub(f"Upper Room {floor_label}B", 16.0, "3.8 x 4.2", floor_note)
        )
    )

    half_w = width / 2.0
    half_d = depth / 2.0
    ceiling_finish = "sloped" if roof_type == "gable" else ""

    hall_width = _clamp(_preferred_pair(hall_room, (3.0, 4.0))[0], 2.6, min(3.3, width * 0.28))
    left_total_width = _clamp(max(_preferred_pair(primary_room, (4.4, 5.0))[0], width * 0.46), 4.4, width - hall_width - 2.8)
    right_width = max(2.8, width - left_total_width)
    service_left_width = _clamp(min(left_total_width * 0.48, 3.4), 2.4, 3.4)
    front_depth = _clamp(max(_preferred_pair(primary_room, (4.4, 5.0))[1], _preferred_pair(front_right_room, (3.8, 4.2))[1]), 4.2, min(6.0, depth - 2.6))
    rear_depth = max(2.6, depth - front_depth)

    left_x = -half_w + (left_total_width / 2.0)
    front_right_x = half_w - (right_width / 2.0)
    service_left_x = -half_w + (service_left_width / 2.0)
    hall_x = -half_w + service_left_width + (hall_width / 2.0)
    rear_right_width = max(2.4, width - service_left_width - hall_width)
    rear_right_x = -half_w + service_left_width + hall_width + (rear_right_width / 2.0)
    front_y = -half_d + (front_depth / 2.0)
    rear_y = half_d - (rear_depth / 2.0)

    primary_role = _room_role(primary_room)
    primary_spec = _append_room(
        planned_rooms,
        primary_room,
        f"primary_f{floor_index}",
        floor_index,
        left_x,
        front_y,
        left_total_width,
        front_depth,
        floor_height,
        _zone_for_role(primary_role),
        f"Upper Room {floor_label}A",
        finish=ceiling_finish if _zone_for_role(primary_role) == "private" else "",
    )
    if floor_index == 1 and primary_role in {"master", "bedroom"}:
        metadata["master_center_x"] = primary_spec.center_x
        metadata["master_width"] = primary_spec.width

    front_right_role = _room_role(front_right_room)
    _append_room(
        planned_rooms,
        front_right_room,
        f"front_right_f{floor_index}",
        floor_index,
        front_right_x,
        front_y,
        right_width,
        front_depth,
        floor_height,
        _zone_for_role(front_right_role),
        f"Upper Room {floor_label}B",
        finish=ceiling_finish if _zone_for_role(front_right_role) == "private" else "",
    )
    hall_spec = _append_room(
        planned_rooms,
        hall_room,
        f"hall_f{floor_index}",
        floor_index,
        hall_x,
        rear_y,
        hall_width,
        rear_depth,
        floor_height,
        "circulation",
        f"Hall {floor_label}",
        finish=ceiling_finish,
    )

    left_service_queue = service_rooms[:2]
    right_rear_queue = service_rooms[2:] + bedroom_candidates + public_candidates + office_candidates

    if left_service_queue:
        depths = _split_span(rear_depth, len(left_service_queue), 1.6)
        cursor_y = -half_d + front_depth
        for index, room in enumerate(left_service_queue):
            room_depth = depths[index]
            role = _room_role(room)
            _append_room(
                planned_rooms,
                room,
                f"left_service_f{floor_index}_{index}",
                floor_index,
                service_left_x,
                cursor_y + (room_depth / 2.0),
                service_left_width,
                room_depth,
                floor_height,
                _zone_for_role(role),
                "Service Room",
                finish="cedar" if role == "sauna" else "",
            )
            cursor_y += room_depth

    if right_rear_queue:
        depths = _split_span(rear_depth, len(right_rear_queue), 1.8)
        cursor_y = -half_d + front_depth
        for index, room in enumerate(right_rear_queue):
            room_depth = depths[index]
            role = _room_role(room)
            _append_room(
                planned_rooms,
                room,
                f"rear_right_f{floor_index}_{index}",
                floor_index,
                rear_right_x,
                cursor_y + (room_depth / 2.0),
                rear_right_width,
                room_depth,
                floor_height,
                _zone_for_role(role),
                "Upper Rear Room",
                finish=ceiling_finish if _zone_for_role(role) == "private" else "",
            )
            cursor_y += room_depth

    features.append(
        _feature(
            f"stair_landing_f{floor_index}",
            "stair_landing",
            floor_index,
            hall_spec.center_x,
            hall_spec.center_y - 0.25,
            min(1.8, hall_spec.width - 0.1),
            min(2.2, hall_spec.depth - 0.2),
            0.12,
            material_hint="oak",
        )
    )
    return planned_rooms, features, metadata


def _wants_feature(text: str, needles: tuple[str, ...]) -> bool:
    normalized = _normalize(text)
    return any(needle in normalized for needle in needles)


def _append_optional_features(
    features: list[FeatureSpec],
    room_specs: list[RoomSpec],
    special_notes: str,
    floors: int,
    floor_height: float,
) -> None:
    normalized = _normalize(special_notes)
    hall_f0 = next((room for room in room_specs if room.room_id == "hall_f0"), None)
    upper_halls = sorted(
        [room for room in room_specs if room.zone == "circulation" and room.floor_index > 0],
        key=lambda room: room.floor_index,
    )
    top_hall = upper_halls[-1] if upper_halls else None

    if hall_f0 and _wants_feature(normalized, ("lift", "elevator", "pneumatic lift", "пневмолифт", "лифт")):
        features.append(
            _feature(
                "lift_core",
                "lift",
                0,
                hall_f0.center_x,
                hall_f0.center_y + max(0.0, hall_f0.depth * 0.18),
                1.2,
                1.2,
                max(floor_height * floors, 3.0),
                material_hint="glass",
                notes="Cylindrical lift shaft.",
            )
        )

    if top_hall and _wants_feature(normalized, ("zenith", "skylight", "second light", "roof light", "зенит", "второй свет")):
        features.append(
            _feature(
                "skylight_void",
                "skylight",
                top_hall.floor_index,
                top_hall.center_x,
                top_hall.center_y,
                1.6,
                1.6,
                0.25,
                material_hint="glass",
            )
        )


def plan_interior(
    width: float,
    depth: float,
    wall_thickness: float,
    floor_height: float,
    floors: int,
    roof_type: str,
    space_program: dict[str, Any] | None,
    *,
    special_notes: str = "",
    has_garage: bool = False,
    design_profile: str = "default",
) -> tuple[list[RoomSpec], list[FeatureSpec], dict[str, float]]:
    effective_program = space_program
    if not effective_program or not effective_program.get("room_program"):
        effective_program = infer_space_program_from_notes(
            special_notes,
            floors,
            has_garage=has_garage,
        )

    room_program = list(effective_program.get("room_program", []))
    if not room_program:
        return [], [], {}

    interior_width = max(3.0, width - (wall_thickness * 2.0))
    interior_depth = max(3.0, depth - (wall_thickness * 2.0))
    classified = _classify_room_program(room_program, floors)
    floor_map = {
        floor_index: [entry for entry in classified if entry["floor_index"] == floor_index]
        for floor_index in range(floors)
    }

    planned_rooms, features, metadata = _plan_first_floor(
        interior_width,
        interior_depth,
        floor_height,
        floor_map.get(0, []),
        floors=floors,
        special_notes=special_notes,
        design_profile=design_profile,
    )

    for floor_index in range(1, floors):
        floor_entries = floor_map.get(floor_index, [])
        if not floor_entries:
            continue
        upper_rooms, upper_features, upper_meta = _plan_upper_floor(
            interior_width,
            interior_depth,
            floor_height,
            floor_entries,
            roof_type,
            floor_index,
        )
        planned_rooms.extend(upper_rooms)
        features.extend(upper_features)
        metadata.update(upper_meta)

    _append_optional_features(features, planned_rooms, special_notes, floors, floor_height)
    return planned_rooms, features, metadata
