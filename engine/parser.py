from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from engine.constraints import ConstraintGraph


FIELD_CASTERS: dict[str, Any] = {
    "width": float,
    "depth": float,
    "floors": int,
    "floor_height": float,
    "roof_type": str,
    "roof_pitch": float,
    "window_count_front": int,
    "window_style": str,
    "wall_material": str,
    "has_columns": bool,
    "has_pediment": bool,
    "has_portico": bool,
    "entrance_style": str,
    "has_garage": bool,
    "has_terrace": bool,
    "has_balcony": bool,
    "has_fence": bool,
    "arch_style": str,
}


def _normalize_notes(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def interpret_special_notes(text: str) -> tuple[dict[str, Any], list[str]]:
    normalized = _normalize_notes(text)
    overrides: dict[str, Any] = {}
    messages: list[str] = []

    def contains_any(*needles: str) -> bool:
        return any(needle in normalized for needle in needles)

    if contains_any("hip roof", "вальм", "четырехскат"):
        overrides["roof_type"] = "hip"
        messages.append("Special notes set roof_type='hip'.")
    elif contains_any("cross-gable", "cross gable", "gable roof", "двускат", "щипц"):
        overrides["roof_type"] = "gable"
        messages.append("Special notes set roof_type='gable'.")
    elif contains_any("flat roof", "плоская крыша", "плоскую крыш", "эксплуатируем"):
        overrides["roof_type"] = "flat"
        overrides["roof_pitch"] = 0.0
        messages.append("Special notes set roof_type='flat'.")

    if contains_any(
        "horizontal siding",
        "lap siding",
        "vinyl siding",
        "wood siding",
        "clapboard",
        "siding texture",
        "lap siding texture",
        "горизонтальный сайдинг",
        "сайдинг",
    ):
        overrides["wall_material"] = "siding"
        messages.append("Special notes set wall_material='siding'.")
    elif contains_any("log cabin", "log house", "timber house", "round logs", "stacked logs", "сруб", "бревенчат", "бревно"):
        overrides["wall_material"] = "log_wood"
        messages.append("Special notes set wall_material='log_wood'.")
    elif contains_any("brick facade", "brick wall", "brick house", "brickwork", "brick exterior", "из кирпич", "фасад из кирпича", "кирпичный дом"):
        overrides["wall_material"] = "brick"
        messages.append("Special notes set wall_material='brick'.")
    elif contains_any("stone facade", "stone wall", "stone house", "slate", "камен", "сланц"):
        overrides["wall_material"] = "stone"
        messages.append("Special notes set wall_material='stone'.")
    elif contains_any("stucco", "plaster facade", "plaster wall", "штукатур"):
        overrides["wall_material"] = "stucco"
        messages.append("Special notes set wall_material='stucco'.")
    elif contains_any("concrete facade", "concrete wall", "concrete house", "бетон"):
        overrides["wall_material"] = "concrete"
        messages.append("Special notes set wall_material='concrete'.")

    if contains_any("barnhouse", "modern barnhouse", "scandinavian", "scandi"):
        overrides["arch_style"] = "scandinavian_barnhouse"
        messages.append("Special notes set arch_style='scandinavian_barnhouse'.")
    elif contains_any("traditional suburban", "suburban family home", "suburban", "family home", "detached residential"):
        overrides["arch_style"] = "traditional_suburban"
        messages.append("Special notes set arch_style='traditional_suburban'.")
    elif contains_any("log cabin", "log house", "rustic cabin", "timber house", "сруб", "бревенчат"):
        overrides["arch_style"] = "rustic_log_cabin"
        messages.append("Special notes set arch_style='rustic_log_cabin'.")

    switch_terms = {
        "has_columns": ("column", "колон"),
        "has_pediment": ("pediment", "фронтон"),
        "has_portico": ("portico", "портик"),
        "has_garage": ("garage", "гараж"),
        "has_terrace": ("terrace", "террас"),
        "has_balcony": ("balcony", "балкон"),
        "has_fence": ("fence", "забор"),
    }

    for key, (en_term, ru_term) in switch_terms.items():
        disable_en = contains_any(f"no {en_term}", f"without {en_term}", f"remove {en_term}")
        enable_en = contains_any(f"with {en_term}", f"add {en_term}", f"include {en_term}")
        disable_ru = contains_any(f"без {ru_term}", f"убрать {ru_term}", f"нет {ru_term}")
        enable_ru = contains_any(f"с {ru_term}", f"добавь {ru_term}", f"добавить {ru_term}", f"нужен {ru_term}")
        if disable_en or disable_ru:
            overrides[key] = False
            messages.append(f"Special notes set {key}=False.")
        elif enable_en or enable_ru:
            overrides[key] = True
            messages.append(f"Special notes set {key}=True.")

    return overrides, messages


def parse_raw_input(raw: dict[str, Any]) -> ConstraintGraph:
    graph = ConstraintGraph()

    for key, caster in FIELD_CASTERS.items():
        if key not in raw:
            continue
        value = raw[key]
        if caster is bool:
            value = bool(value)
        else:
            value = caster(value)
        graph.set(key, value, source="gui")

    special_notes = str(raw.get("special_notes", "")).strip()
    if special_notes:
        graph.set("special_notes", special_notes, source="gui", required=False)
        overrides, messages = interpret_special_notes(special_notes)
        graph.notes.extend(messages)
        for name, value in overrides.items():
            graph.set(name, value, source="notes")

    ai_design_payload = raw.get("ai_design_payload")
    if isinstance(ai_design_payload, dict):
        graph.set("ai_design_payload", ai_design_payload, source="ai", required=False)

    return graph


def save_raw_input(raw: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(raw, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
