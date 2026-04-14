from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GUIParameterPlan(BaseModel):
    width: float = Field(description="Building width in meters.")
    depth: float = Field(description="Building depth in meters.")
    floors: int = Field(description="Number of floors.")
    floor_height: float = Field(description="Floor height in meters.")
    roof_type: Literal["gable", "hip", "flat"]
    roof_pitch: float = Field(description="Roof pitch in degrees. Use 0 for flat roof.")
    window_count_front: int = Field(description="Front facade manual window count. Use 0 for auto.")
    window_style: Literal["modern", "classic", "square"]
    wall_material: Literal["stucco", "brick", "stone", "concrete", "siding", "log_wood"]
    entrance_style: Literal["modern", "classic"]
    has_columns: bool
    has_pediment: bool
    has_portico: bool
    has_garage: bool
    has_terrace: bool
    has_balcony: bool
    has_fence: bool
    arch_style: Literal["modern_villa", "grand_estate", "classic_luxury_mansion", "scandinavian_barnhouse", "traditional_suburban", "rustic_log_cabin"]
    special_notes: str = ""


class RoomPlan(BaseModel):
    name: str
    target_area_sqm: float
    dimensions_m: str
    doors: str
    windows: str
    notes: str


class SpaceProgramPlan(BaseModel):
    target_total_area_sqm: float
    zoning_strategy: str
    circulation_strategy: str
    room_program: list[RoomPlan]
    adjacency_rules: list[str]
    future_parser_notes: list[str]


class HousePlanResponse(BaseModel):
    project_title: str
    architectural_concept: str
    stylistic_uniqueness: str
    facade_strategy: str
    constraint_notes: list[str]
    gui_parameters: GUIParameterPlan
    space_program: SpaceProgramPlan
    technical_instruction_markdown: str
