from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class OpeningSpec:
    opening_id: str
    facade: str
    kind: str
    center: float
    bottom: float
    width: float
    height: float
    floor_index: int
    mullion_count: int = 1
    frame_style: str = "standard"


@dataclass(slots=True)
class FacadeLayoutSpec:
    facade: str
    length: float
    edge_margin: float
    center_gap: float
    axes: list[float] = field(default_factory=list)
    window_width: float = 1.4
    window_height: float = 1.6
    sill_height: float = 0.9
    windows: list[OpeningSpec] = field(default_factory=list)


@dataclass(slots=True)
class DoorSpec:
    center: float
    width: float
    height: float
    bottom: float
    reveal_depth: float
    style: str


@dataclass(slots=True)
class EntranceSpec:
    door: DoorSpec
    style: str
    has_columns: bool
    has_pediment: bool
    has_portico: bool
    stoop_width: float
    stoop_depth: float
    canopy_depth: float
    canopy_thickness: float
    column_radius: float
    column_height: float
    column_count: int
    pediment_height: float


@dataclass(slots=True)
class RoofSpec:
    roof_type: str
    pitch_degrees: float
    overhang: float
    ridge_height: float
    base_elevation: float
    thickness: float
    ridge_axis: str = "y"


@dataclass(slots=True)
class GarageSpec:
    enabled: bool
    side: str
    width: float
    depth: float
    height: float
    front_setback: float
    door_width: float
    door_height: float


@dataclass(slots=True)
class TerraceSpec:
    enabled: bool
    width: float
    depth: float
    elevation: float
    center_x: float = 0.0
    center_y: float = 0.0


@dataclass(slots=True)
class BalconySpec:
    enabled: bool
    width: float
    depth: float
    elevation: float
    floor_index: int
    center_x: float = 0.0


@dataclass(slots=True)
class RoomSpec:
    room_id: str
    name: str
    floor_index: int
    center_x: float
    center_y: float
    width: float
    depth: float
    height: float
    zone: str
    notes: str = ""
    finish: str = ""


@dataclass(slots=True)
class FeatureSpec:
    feature_id: str
    kind: str
    floor_index: int
    center_x: float
    center_y: float
    width: float
    depth: float
    height: float
    rotation_degrees: float = 0.0
    material_hint: str = ""
    notes: str = ""


@dataclass(slots=True)
class EnvironmentSpec:
    lot_margin: float
    path_width: float
    path_length: float
    driveway_width: float
    fence_enabled: bool


@dataclass(slots=True)
class ResolvedSpec:
    width: float
    depth: float
    floors: int
    floor_height: float
    wall_height: float
    wall_thickness: float
    floor_slab_thickness: float
    foundation_height: float
    arch_style: str
    window_style: str
    wall_material: str
    roof: RoofSpec
    front_facade: FacadeLayoutSpec
    rear_facade: FacadeLayoutSpec
    left_facade: FacadeLayoutSpec
    right_facade: FacadeLayoutSpec
    entrance: EntranceSpec
    garage: GarageSpec
    terrace: TerraceSpec
    balcony: BalconySpec
    environment: EnvironmentSpec
    room_specs: list[RoomSpec] = field(default_factory=list)
    feature_specs: list[FeatureSpec] = field(default_factory=list)
    design_profile: str = "default"
    design_options: dict[str, Any] = field(default_factory=dict)
    upper_wall_material: str = ""
    special_notes: str = ""
    note_overrides: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def from_dict(cls, payload: dict) -> ResolvedSpec:
        def opening_list(items: list[dict]) -> list[OpeningSpec]:
            return [OpeningSpec(**item) for item in items]

        def room_list(items: list[dict]) -> list[RoomSpec]:
            return [RoomSpec(**item) for item in items]

        def feature_list(items: list[dict]) -> list[FeatureSpec]:
            return [FeatureSpec(**item) for item in items]

        def facade(data: dict) -> FacadeLayoutSpec:
            return FacadeLayoutSpec(
                facade=data["facade"],
                length=data["length"],
                edge_margin=data["edge_margin"],
                center_gap=data["center_gap"],
                axes=list(data.get("axes", [])),
                window_width=data["window_width"],
                window_height=data["window_height"],
                sill_height=data["sill_height"],
                windows=opening_list(data.get("windows", [])),
            )

        return cls(
            width=payload["width"],
            depth=payload["depth"],
            floors=payload["floors"],
            floor_height=payload["floor_height"],
            wall_height=payload["wall_height"],
            wall_thickness=payload["wall_thickness"],
            floor_slab_thickness=payload["floor_slab_thickness"],
            foundation_height=payload["foundation_height"],
            arch_style=payload["arch_style"],
            window_style=payload["window_style"],
            wall_material=payload["wall_material"],
            roof=RoofSpec(**payload["roof"]),
            front_facade=facade(payload["front_facade"]),
            rear_facade=facade(payload["rear_facade"]),
            left_facade=facade(payload["left_facade"]),
            right_facade=facade(payload["right_facade"]),
            entrance=EntranceSpec(
                door=DoorSpec(**payload["entrance"]["door"]),
                style=payload["entrance"]["style"],
                has_columns=payload["entrance"]["has_columns"],
                has_pediment=payload["entrance"]["has_pediment"],
                has_portico=payload["entrance"]["has_portico"],
                stoop_width=payload["entrance"]["stoop_width"],
                stoop_depth=payload["entrance"]["stoop_depth"],
                canopy_depth=payload["entrance"]["canopy_depth"],
                canopy_thickness=payload["entrance"]["canopy_thickness"],
                column_radius=payload["entrance"]["column_radius"],
                column_height=payload["entrance"]["column_height"],
                column_count=payload["entrance"]["column_count"],
                pediment_height=payload["entrance"]["pediment_height"],
            ),
            garage=GarageSpec(**payload["garage"]),
            terrace=TerraceSpec(
                enabled=payload["terrace"]["enabled"],
                width=payload["terrace"]["width"],
                depth=payload["terrace"]["depth"],
                elevation=payload["terrace"]["elevation"],
                center_x=payload["terrace"].get("center_x", 0.0),
                center_y=payload["terrace"].get("center_y", 0.0),
            ),
            balcony=BalconySpec(
                enabled=payload["balcony"]["enabled"],
                width=payload["balcony"]["width"],
                depth=payload["balcony"]["depth"],
                elevation=payload["balcony"]["elevation"],
                floor_index=payload["balcony"]["floor_index"],
                center_x=payload["balcony"].get("center_x", 0.0),
            ),
            environment=EnvironmentSpec(**payload["environment"]),
            room_specs=room_list(payload.get("room_specs", [])),
            feature_specs=feature_list(payload.get("feature_specs", [])),
            design_profile=payload.get("design_profile", "default"),
            design_options=dict(payload.get("design_options", {})),
            upper_wall_material=payload.get("upper_wall_material", ""),
            special_notes=payload.get("special_notes", ""),
            note_overrides=list(payload.get("note_overrides", [])),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> ResolvedSpec:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
