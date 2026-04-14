from __future__ import annotations

from engine.specs import FacadeLayoutSpec, ResolvedSpec


def iter_facades(spec: ResolvedSpec) -> list[FacadeLayoutSpec]:
    return [
        spec.front_facade,
        spec.rear_facade,
        spec.left_facade,
        spec.right_facade,
    ]


def plane_location(spec: ResolvedSpec, facade: str, inset: float = 0.0) -> tuple[float, float, float]:
    if facade == "front":
        return (0.0, -(spec.depth / 2.0) + inset, 0.0)
    if facade == "rear":
        return (0.0, (spec.depth / 2.0) - inset, 0.0)
    if facade == "left":
        return (-(spec.width / 2.0) + inset, 0.0, 0.0)
    return ((spec.width / 2.0) - inset, 0.0, 0.0)


def opening_location(
    spec: ResolvedSpec,
    facade: str,
    center: float,
    bottom: float,
    width: float,
    height: float,
    inset: float = 0.0,
) -> tuple[float, float, float]:
    z = bottom + (height / 2.0)
    if facade == "front":
        return (center, -(spec.depth / 2.0) + inset, z)
    if facade == "rear":
        return (center, (spec.depth / 2.0) - inset, z)
    if facade == "left":
        return (-(spec.width / 2.0) + inset, center, z)
    return ((spec.width / 2.0) - inset, center, z)


def opening_size(spec: ResolvedSpec, facade: str, width: float, height: float, depth: float) -> tuple[float, float, float]:
    if facade in {"front", "rear"}:
        return (width, depth, height)
    return (depth, width, height)
