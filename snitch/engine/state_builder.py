"""Monta o JSON de estado enviado ao Jev a partir de detecções e zonas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TrackedPerson:
    tracker_id: int
    bbox_xyxy: tuple[float, float, float, float]
    in_zones: list[str] = field(default_factory=list)
    ppe_detected: list[str] = field(default_factory=list)
    ppe_missing: list[str] = field(default_factory=list)


def build_jev_state(
    *,
    camera_id: int,
    frame_index: int,
    persons: list[TrackedPerson],
    zones: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Estado atômico por frame — sem imagem (FR: Jev recebe JSON, não pixels)."""
    return {
        "camera_id": camera_id,
        "frame_index": frame_index,
        "zones": zones or [],
        "persons": [
            {
                "tracker_id": p.tracker_id,
                "bbox": list(p.bbox_xyxy),
                "in_zones": p.in_zones,
                "ppe_detected": p.ppe_detected,
                "ppe_missing": p.ppe_missing,
            }
            for p in persons
        ],
    }
