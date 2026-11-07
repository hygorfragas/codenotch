"""Lê keypoints do YOLOv8-pose. Índices são os 17 do COCO."""

from __future__ import annotations

import math
from typing import Any

NOSE, LEFT_EYE, RIGHT_EYE, LEFT_EAR, RIGHT_EAR = 0, 1, 2, 3, 4
LEFT_WRIST, RIGHT_WRIST = 9, 10


def _point(xy: Any, conf: Any, index: int, minimum: float = 0.25) -> tuple[float, float] | None:
    if xy is None or index >= len(xy):
        return None
    score = float(conf[index]) if conf is not None and index < len(conf) and conf[index] is not None else 1.0
    if score < minimum:
        return None
    x, y = float(xy[index][0]), float(xy[index][1])
    if x <= 0 and y <= 0:
        return None
    return (x, y)


def describe_pose(xy: Any, conf: Any) -> dict[str, Any]:
    nose = _point(xy, conf, NOSE)
    left_eye = _point(xy, conf, LEFT_EYE)
    right_eye = _point(xy, conf, RIGHT_EYE)
    ears = [point for point in (_point(xy, conf, LEFT_EAR), _point(xy, conf, RIGHT_EAR)) if point]
    wrists = [point for point in (_point(xy, conf, LEFT_WRIST), _point(xy, conf, RIGHT_WRIST)) if point]
    eyes = [point for point in (left_eye, right_eye) if point]
    occluded = nose is None and not eyes
    if len(eyes) == 2 and nose is not None:
        yaw = "frontal"
    elif len(eyes) == 1 or (len(ears) == 1 and nose is not None):
        yaw = "profile"
    else:
        yaw = "unknown"
    return {
        "nose": nose,
        "eyes": eyes,
        "ears": ears,
        "wrists": wrists,
        "occluded": occluded,
        "yaw": yaw,
        "face_visible": nose is not None or bool(eyes),
        "ear_visible": bool(ears),
        "hand_visible": bool(wrists),
    }


def _hypot(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def nearest(origin: tuple[float, float] | None, points: list[tuple[float, float]]) -> float | None:
    if origin is None or not points:
        return None
    return min(_hypot(origin, point) for point in points)


def head_lowered(pose: dict[str, Any], head_height: float) -> bool:
    """Nariz bem abaixo dos olhos: a pessoa olha para baixo, onde um celular costuma estar."""
    nose = pose.get("nose")
    eyes = pose.get("eyes") or []
    if nose is None or not eyes:
        return False
    eye_y = sum(point[1] for point in eyes) / len(eyes)
    return nose[1] > eye_y + 0.12 * max(head_height, 1.0)


def hand_near_face(pose: dict[str, Any], head_height: float) -> bool:
    """Pulso perto da orelha ou do nariz, na mesma escala da cabeça."""
    wrists = pose.get("wrists") or []
    targets = list(pose.get("ears") or [])
    if pose.get("nose") is not None:
        targets.append(pose["nose"])
    if not wrists or not targets:
        return False
    limit = 0.75 * max(head_height, 1.0)
    for wrist in wrists:
        distance = nearest(wrist, targets)
        if distance is not None and distance <= limit:
            return True
    return False


def phone_pose_trigger(pose: dict[str, Any], head_height: float) -> bool:
    return head_lowered(pose, head_height) or hand_near_face(pose, head_height)


def face_toward_phone(pose: dict[str, Any], phone: tuple[float, float] | None, head_height: float) -> bool:
    nose = pose.get("nose")
    if nose is None or phone is None:
        return False
    if _hypot(nose, phone) > 1.05 * max(head_height, 1.0):
        return False
    eyes = pose.get("eyes") or []
    if len(eyes) >= 1:
        eye = eyes[0]
        same_side = (phone[0] - nose[0]) * (eye[0] - nose[0]) >= -5
        return same_side or pose.get("yaw") == "frontal"
    return pose.get("yaw") == "frontal"
