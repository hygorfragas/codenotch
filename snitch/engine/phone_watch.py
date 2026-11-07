"""Celular perto da mão ou do rosto, e o relógio de uso confirmado."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _center(box: np.ndarray) -> tuple[float, float]:
    return (float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2


def _contains(box: np.ndarray, point: tuple[float, float], scale: float) -> bool:
    cx, cy = _center(box)
    width = max(float(box[2]) - float(box[0]), 1.0) * scale
    height = max(float(box[3]) - float(box[1]), 1.0) * scale
    return abs(point[0] - cx) <= width / 2 and abs(point[1] - cy) <= height / 2


def phone_near_body(
    phone_box: np.ndarray,
    hands: list[np.ndarray],
    faces: list[np.ndarray],
    heads: list[np.ndarray],
) -> str | None:
    """'hand' ou 'face' quando o centro do celular está junto do corpo. Longe, None."""
    point = _center(phone_box)
    for hand in hands:
        if _contains(hand, point, 1.8):
            return "hand"
    for face in faces:
        if _contains(face, point, 1.6):
            return "face"
    for head in heads:
        if not _contains(head, point, 1.25):
            continue
        top = float(head[1])
        height = max(float(head[3]) - top, 1.0)
        if point[1] <= top + 0.7 * height:
            return "face"
    return None


@dataclass
class PhoneSighting:
    tracker_id: int
    center: tuple[float, float]
    visible: bool
    confirmed: bool


class PhoneClock:
    """Soma o tempo de uso confirmado e sobrevive a uma troca curta de ID."""

    def __init__(self, grace_seconds: float = 4.5, reid_pixels: float = 220.0, max_gap: float = 1.0) -> None:
        self.grace_seconds = grace_seconds
        self.reid_pixels = reid_pixels
        self.max_gap = max_gap
        self._tracks: dict[int, dict[str, float | bool | tuple[float, float]]] = {}

    def update(
        self,
        sightings: list[PhoneSighting],
        now: float,
        limit: int | None,
    ) -> list[dict[str, int | bool]]:
        live = {item.tracker_id for item in sightings}
        for item in sightings:
            if item.tracker_id in self._tracks:
                continue
            donor = self._nearest_stale(item.center, now, live)
            if donor is not None:
                self._tracks[item.tracker_id] = self._tracks.pop(donor)
        statuses: list[dict[str, int | bool]] = []
        for item in sightings:
            record = self._tracks.get(item.tracker_id)
            if record is None:
                record = {"elapsed": 0.0, "last": now, "reported": False, "center": item.center}
                self._tracks[item.tracker_id] = record
                gap = 0.0
            else:
                gap = min(self.max_gap, max(0.0, now - float(record["last"])))
            record["last"] = now
            record["center"] = item.center
            if item.visible and item.confirmed and gap > 0:
                record["elapsed"] = float(record["elapsed"]) + gap
            elapsed = int(float(record["elapsed"]))
            crossed = bool(limit and elapsed >= int(limit) and not record["reported"])
            if crossed:
                record["reported"] = True
            statuses.append({
                "tracker_id": item.tracker_id,
                "elapsed_s": elapsed,
                "limit_s": int(limit or 0),
                "visible": item.visible,
                "confirmed": item.confirmed,
                "limit_exceeded": crossed,
            })
        for tracker_id, record in list(self._tracks.items()):
            if tracker_id not in live and now - float(record["last"]) > self.grace_seconds:
                self._tracks.pop(tracker_id, None)
        return statuses

    def _nearest_stale(
        self,
        center: tuple[float, float],
        now: float,
        live: set[int],
    ) -> int | None:
        best_id: int | None = None
        best_distance = self.reid_pixels
        for tracker_id, record in self._tracks.items():
            if tracker_id in live or now - float(record["last"]) > self.grace_seconds:
                continue
            previous = record.get("center")
            if not isinstance(previous, tuple):
                continue
            distance = ((center[0] - previous[0]) ** 2 + (center[1] - previous[1]) ** 2) ** 0.5
            if distance <= best_distance:
                best_distance = distance
                best_id = tracker_id
        return best_id
