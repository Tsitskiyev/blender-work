from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AssetDefinition:
    asset_type: str
    builder_name: str
    placement_zones: list[str] = field(default_factory=list)
    allowed_contexts: list[str] = field(default_factory=lambda: ["any"])


REGISTRY: dict[str, AssetDefinition] = {
    "lamp": AssetDefinition(
        asset_type="lamp",
        builder_name="build_path_lamps",
        placement_zones=["path_side"],
    ),
}


def get_asset(name: str) -> AssetDefinition | None:
    return REGISTRY.get(name)
