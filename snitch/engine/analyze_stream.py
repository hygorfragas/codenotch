#!/usr/bin/env python3
"""
SNITCH — analisa fluxo RTSP/arquivo, YOLO (SH17), ByteTrack, PolygonZone,
desenha caixas e publica frames via SSE. Estado JSON vai ao Jev.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from jev_client import ask_jev_sync
from state_builder import TrackedPerson, build_jev_state

# Classes SH17 (17 EPIs / partes corporais) — ordem alinhada ao dataset público.
SH17_CLASS_NAMES: tuple[str, ...] = (
    "person",
    "head",
    "face",
    "hand",
    "foot",
    "helmet",
    "goggles",
    "ear_protection",
    "mask",
    "vest",
    "gloves",
    "boots",
    "harness",
    "tool",
    "vehicle",
    "fire_extinguisher",
    "sign",
)

PPE_BODY_MAP: dict[str, str] = {
    "helmet": "head",
    "goggles": "face",
    "ear_protection": "head",
    "mask": "face",
    "vest": "person",
    "gloves": "hand",
    "boots": "foot",
}

# Nomes do yolo8n.pt oficial (sh17.yaml) -> vocabulário do motor.
CLASS_ALIASES: dict[str, str] = {
    "safety-vest": "vest",
    "shoes": "boots",
    "glasses": "goggles",
    "ear-mufs": "ear_protection",
    "face-mask": "mask",
    "hands": "hand",
}

DISPLAY_LABELS: dict[str, str] = {
    "person": "Pessoa",
    "helmet": "Capacete",
    "gloves": "Luvas",
    "glasses": "Óculos de proteção",
    "goggles": "Óculos de proteção",
    "shoes": "Calçado de segurança",
    "boots": "Botina",
    "safety-vest": "Colete refletivo",
    "vest": "Colete refletivo",
    "ear-mufs": "Protetor auricular",
    "ear_protection": "Protetor auricular",
    "ear-protector": "Protetor auricular",
    "face-mask": "Máscara facial",
    "mask": "Máscara facial",
    "face-guard": "Protetor facial",
    "medical-suit": "Traje médico",
    "safety-suit": "Traje de segurança",
    "head": "Cabeça",
    "face": "Rosto",
    "hands": "Mãos",
    "hand": "Mãos",
    "ear": "Orelha",
    "foot": "Pé",
    "tool": "Ferramenta",
    "harness": "Cinto de segurança",
    "smartphone": "Celular",
    "cell phone": "Celular",
}


def canonical_class_name(name: str) -> str:
    return CLASS_ALIASES.get(name, name)


def display_class_name(name: str) -> str:
    return DISPLAY_LABELS.get(name, name)


def map_boxes_to_frame(
    xyxy,
    source_hw: tuple[int, int],
    origin_xy: tuple[float, float],
    crop_hw: tuple[int, int],
    frame_hw: tuple[int, int],
) -> list[list[float]]:
    """Leva caixas do recorte para o quadro cheio e corta no limite da imagem.

    source_hw é o tamanho da imagem que o modelo recebeu. Se ela é o recorte
    cru, a escala é 1 e só entra a origem. Se foi redimensionada, a escala
    desfaz esse resize antes de somar a origem. Não usa o imgsz do letterbox:
    o Ultralytics já devolve xyxy no tamanho da imagem recebida.
    """
    source_h, source_w = source_hw
    crop_h, crop_w = crop_hw
    origin_x, origin_y = origin_xy
    frame_h, frame_w = frame_hw
    scale_x = crop_w / max(float(source_w), 1.0)
    scale_y = crop_h / max(float(source_h), 1.0)
    mapped: list[list[float]] = []
    for raw in xyxy:
        x1 = origin_x + float(raw[0]) * scale_x
        y1 = origin_y + float(raw[1]) * scale_y
        x2 = origin_x + float(raw[2]) * scale_x
        y2 = origin_y + float(raw[3]) * scale_y
        x1 = min(max(x1, 0.0), float(frame_w))
        y1 = min(max(y1, 0.0), float(frame_h))
        x2 = min(max(x2, 0.0), float(frame_w))
        y2 = min(max(y2, 0.0), float(frame_h))
        if x2 - x1 < 2 or y2 - y1 < 2:
            continue
        mapped.append([x1, y1, x2, y2])
    return mapped


def smartphone_record_decision(
    *,
    enabled: bool,
    seconds: int,
    limit: int | None,
    laya_confirmed: bool | None,
    laya_available: bool,
) -> tuple[bool, str]:
    """A Laya confirma o uso. Sem ela, só um fallback mais longo registra o episódio."""
    if not enabled or limit is None or seconds < limit:
        return False, "abaixo_do_limite"
    if laya_available and laya_confirmed is True:
        return True, "laya"
    if laya_available and laya_confirmed is not True:
        return False, "laya_nao_confirmou"
    if seconds >= limit + 5:
        return True, "fallback_local"
    return False, "laya_indisponivel"


def compact_laya_payload(state: dict[str, Any]) -> dict[str, Any]:
    """Estado curto para a Laya: sem imagem e sem caixas de EPI repetidas."""
    policy = state.get("smartphone") if isinstance(state.get("smartphone"), dict) else {}
    phones = {
        int(item["tracker_id"]): item
        for item in (state.get("smartphones") or [])
        if isinstance(item, dict) and item.get("tracker_id") is not None
    }
    persons = []
    for person in state.get("persons") or []:
        if not isinstance(person, dict):
            continue
        tracker_id = int(person.get("tracker_id") or 0)
        phone = phones.get(tracker_id) or {}
        persons.append({
            "tracker_id": tracker_id,
            "in_zones": list(person.get("in_zones") or []),
            "ppe_missing": list(person.get("ppe_missing") or []),
            "employee_id": phone.get("employee_id"),
            "smartphone": {
                "smartphone_detected": bool(phone.get("active")),
                "confidence": phone.get("confidence"),
                "continuous_seconds": int(phone.get("seconds") or 0),
                "bbox": phone.get("bbox"),
                "hands_overlap": bool(phone.get("hands_overlap")),
                "near_face": bool(phone.get("near_face")),
                "near_ear": bool(phone.get("near_ear")),
                "in_front_of_face": bool(phone.get("in_front_of_face")),
                "recent_hits": int(phone.get("recent_hits") or 0),
            },
        })
    zones = []
    for zone in state.get("zone_dwell") or state.get("zones") or []:
        if not isinstance(zone, dict):
            continue
        zones.append({
            "name": zone.get("name"),
            "type": zone.get("type"),
            "elapsed_s": zone.get("elapsed_s"),
            "exceeded": zone.get("exceeded"),
        })
    return {
        "camera_id": state.get("camera_id"),
        "frame_index": state.get("frame_index"),
        "required_ppe": list(state.get("required_ppe") or []),
        "zones": zones,
        "persons": persons,
        "smartphone_policy": {
            "enabled": bool(policy.get("enabled")),
            "max_continuous_seconds": policy.get("max_continuous_seconds", policy.get("hand_limit_seconds")),
        },
    }


def render_scene(frame: np.ndarray, overlay: dict[str, Any]) -> np.ndarray:
    """Desenha o último resultado em qualquer quadro novo, sem rodar o modelo de novo."""
    image = frame.copy()
    labels: list[tuple[str, int, int, tuple[int, int, int], tuple[float, float, float, float]]] = []
    for item in overlay.get("boxes") or []:
        x1, y1, x2, y2 = (float(value) for value in item["xyxy"])
        color = tuple(int(channel) for channel in item["color"])
        cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
        labels.append((str(item.get("label") or ""), int(x1), max(0, int(y1) - 22), color, (x1, y1, x2, y2)))
    if labels:
        image = draw_unicode_labels(image, layout_detection_labels(labels))
    zone_labels: list[tuple[str, int, int, tuple[int, int, int]]] = []
    for zone in overlay.get("zones") or []:
        polygon = np.array(zone["polygon"], dtype=np.int32)
        color = tuple(int(channel) for channel in zone["color"])
        cv2.polylines(image, [polygon], isClosed=True, color=color, thickness=2)
        if zone.get("label"):
            zone_labels.append((str(zone["label"]), int(polygon[0][0]), max(0, int(polygon[0][1]) - 22), color))
    if zone_labels:
        image = draw_unicode_labels(image, zone_labels)
    return image


DWELL_GRACE_SECONDS = 4.5
DWELL_REID_PIXELS = 220.0
ZONE_MIN_OVERLAP = 0.15
YOLO_BASE_CONF = 0.10
STRONG_CLASS_CONF = 0.25
SMALL_PPE_CONF = 0.10
EAR_PROTECTION_CONF = 0.35
PHONE_CONF = 0.20
PHONE_HOLD_SECONDS = 2.0
PHONE_INFER_INTERVAL = 0.25
PHONE_FULL_INTERVAL = 1.0
GLASSES_ZOOM_INTERVAL = 0.4
COCO_PHONE_CLASS = 67
PPE_MEMORY_SECONDS = 2.2
SMALL_PPE_LABELS = frozenset({"goggles", "mask", "gloves", "face-guard"})
CROP_PPE_LABELS = frozenset({"goggles", "helmet", "mask", "ear_protection", "face-guard"})
_BUNDLED_FONT = Path(__file__).resolve().parent / "fonts" / "DejaVuSans-Bold.ttf"
FONT_CANDIDATES: tuple[Path, ...] = (
    _BUNDLED_FONT,
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/Library/Fonts/Arial.ttf"),
    Path("/System/Library/Fonts/Helvetica.ttc"),
    Path("/System/Library/Fonts/Supplemental/Helvetica.ttc"),
)
_FONT_PATH: str | None = None
_FONT_CACHE: dict[int, ImageFont.ImageFont | ImageFont.FreeTypeFont] = {}


def resolve_unicode_font_path() -> str | None:
    """Primeira fonte TrueType que desenha acentos. Hershey, do OpenCV, não desenha."""
    global _FONT_PATH
    if _FONT_PATH is not None:
        return _FONT_PATH or None
    for candidate in FONT_CANDIDATES:
        if candidate.is_file():
            _FONT_PATH = str(candidate)
            return _FONT_PATH
    _FONT_PATH = ""
    return None


def _unicode_font(size: int = 18) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    cached = _FONT_CACHE.get(size)
    if cached is not None:
        return cached
    path = resolve_unicode_font_path()
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont
    if path is None:
        font = ImageFont.load_default()
    else:
        font = ImageFont.truetype(path, size=size)
    _FONT_CACHE[size] = font
    return font


def draw_unicode_labels(
    frame: np.ndarray,
    labels: list[tuple[str, int, int, tuple[int, int, int]]],
) -> np.ndarray:
    """Desenha texto UTF-8 no quadro BGR. A cor vem em BGR, como no OpenCV."""
    if not labels:
        return frame
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image)
    font = _unicode_font(18)
    for text, x, y, color_bgr in labels:
        if not text:
            continue
        fill = (int(color_bgr[2]), int(color_bgr[1]), int(color_bgr[0]))
        left, top, right, bottom = draw.textbbox((x, y), text, font=font)
        draw.rectangle((left - 3, top - 2, right + 3, bottom + 2), fill=(15, 23, 42))
        draw.text((x, y), text, font=font, fill=fill)
    return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def person_intersects_zone(
    box: np.ndarray,
    polygon: np.ndarray,
    min_overlap: float = ZONE_MIN_OVERLAP,
) -> bool:
    """Cabeça, centro ou pés dentro do polígono, ou pelo menos 15% da caixa sobre ele.

    PolygonZone só olha o pé (BOTTOM_CENTER). Na webcam o pé fica fora do quadro
    ou fora do polígono mesmo com a pessoa no meio da zona.
    """
    points = np.asarray(polygon, dtype=np.float32)
    if points.shape[0] < 3:
        return False
    contour = np.ascontiguousarray(points.reshape(-1, 1, 2), dtype=np.float32)
    x1, y1, x2, y2 = (float(value) for value in box)
    anchors = (
        ((x1 + x2) / 2.0, (y1 + y2) / 2.0),
        ((x1 + x2) / 2.0, y2),
        ((x1 + x2) / 2.0, y1),
    )
    for point in anchors:
        if cv2.pointPolygonTest(contour, point, False) >= 0:
            return True
    width = max(x2 - x1, 1.0)
    height = max(y2 - y1, 1.0)
    pixels = width * height
    scale = 1.0 if pixels <= 200_000 else math.sqrt(200_000 / pixels)
    mask_w = max(2, int(round(width * scale)))
    mask_h = max(2, int(round(height * scale)))
    mask = np.zeros((mask_h, mask_w), dtype=np.uint8)
    local = points.copy()
    local[:, 0] = (local[:, 0] - x1) * (mask_w / width)
    local[:, 1] = (local[:, 1] - y1) * (mask_h / height)
    cv2.fillPoly(mask, [np.round(local).astype(np.int32)], 255)
    covered = float(cv2.countNonZero(mask)) / float(mask_w * mask_h)
    return covered >= min_overlap


def lookup_class_name(class_id: int, names: Any | None = None) -> str:
    """Rótulo canônico. Com o modelo carregado usa model.names; no mock, SH17_CLASS_NAMES."""
    raw: str
    if isinstance(names, dict):
        raw = str(names.get(class_id, class_id))
    elif isinstance(names, (list, tuple)) and 0 <= class_id < len(names):
        raw = str(names[class_id])
    elif 0 <= class_id < len(SH17_CLASS_NAMES):
        raw = SH17_CLASS_NAMES[class_id]
    else:
        raw = str(class_id)
    return canonical_class_name(raw)


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").lower() in {"1", "true", "yes", "on"}


def _resolve_device() -> str:
    chosen = os.environ.get("SNITCH_YOLO_DEVICE", "").strip()
    if chosen:
        return chosen
    try:
        import torch
    except Exception:  # noqa: BLE001
        return "cpu"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _box_area(box: np.ndarray) -> float:
    return max(0.0, float(box[2]) - float(box[0])) * max(0.0, float(box[3]) - float(box[1]))


def _rects_overlap(left: tuple[int, int, int, int], right: tuple[int, int, int, int], pad: int = 2) -> bool:
    return not (
        left[2] + pad < right[0]
        or right[2] + pad < left[0]
        or left[3] + pad < right[1]
        or right[3] + pad < left[1]
    )


def layout_detection_labels(
    entries: list[tuple[str, int, int, tuple[int, int, int], tuple[float, float, float, float]]],
) -> list[tuple[str, int, int, tuple[int, int, int]]]:
    """Empilha rótulos que nasceriam no mesmo topo, para Pessoa não cobrir Cabeça."""
    ranked = sorted(range(len(entries)), key=lambda index: _box_area(np.array(entries[index][4])), reverse=True)
    placed: list[tuple[int, int, int, int]] = []
    output: list[tuple[str, int, int, tuple[int, int, int]] | None] = [None] * len(entries)
    for index in ranked:
        text, x, y, color, box = entries[index]
        width = max(16, int(len(text) * 8))
        height = 22
        x1, y1, x2, y2 = (int(box[0]), int(box[1]), int(box[2]), int(box[3]))
        candidates = (
            (int(x), int(y)),
            (x2 + 4, y1),
            (x1, y2 + 2),
            (int(x), int(y) + height + 2),
        )
        chosen = candidates[0]
        for origin in candidates:
            rect = (origin[0], origin[1], origin[0] + width, origin[1] + height)
            if not any(_rects_overlap(rect, other) for other in placed):
                chosen = origin
                break
        placed.append((chosen[0], chosen[1], chosen[0] + width, chosen[1] + height))
        output[index] = (text, chosen[0], max(0, chosen[1]), color)
    return [item for item in output if item is not None]


def _import_supervision():
    import supervision as sv

    return sv


def _import_yolo():
    from ultralytics import YOLO

    return YOLO


@dataclass
class ZoneConfig:
    name: str
    polygon: np.ndarray  # Nx2 float, pixels ou normalizado 0–1
    zone_type: str = "passagem"
    max_dwell_seconds: int | None = None
    zone_id: int | None = None


@dataclass
class AnalyzeStreamConfig:
    camera_id: int = 1
    weights_path: Path = Path("storage/engine/sh17.pt")
    stream_source: str = "0"
    jev_url: str = "http://127.0.0.1:8787"
    required_ppe: tuple[str, ...] = ("helmet", "vest", "boots", "gloves")
    zones: list[ZoneConfig] = field(default_factory=list)
    mock: bool = False
    jev_questions: tuple[str, ...] = (
        "any_missing_required_ppe",
        "any_person_in_restricted_zone",
        "any_smartphone_idle",
        "any_person_using_smartphone",
    )


class StreamAnalyzer:
    """Pipeline quadro a quadro: detectar, rastrear, zonas, anotar, estado Jev."""

    def __init__(self, config: AnalyzeStreamConfig) -> None:
        self.config = config
        self._frame_index = 0
        self._tracker = None
        self._polygon_zones: list[Any] = []
        self._model = None
        self._jev_lock = threading.Lock()
        self._jev_inflight = False
        self._last_jev: dict[str, Any] | None = None
        self._last_jev_error: str | None = None
        self._last_jev_ts = 0.0
        self._last_jev_latency_ms: float | None = None
        self._laya_engine: str | None = None
        self._episode_lock = threading.Lock()
        self._episode_at: dict[str, float] = {}
        self._tracker_links: dict[str, dict[str, Any]] = {}
        self._smartphone: dict[str, Any] = {
            "enabled": False,
            "hand_limit_seconds": None,
            "max_continuous_seconds": None,
        }
        self._coco = None
        self._cached_phones: list[list[float]] = []
        self._cached_phones_at = 0.0
        self._phone_since: dict[int, float] = {}
        self._phone_hold: dict[int, float] = {}
        self._phone_boxes: dict[int, list[float]] = {}
        self._phone_confidence: dict[int, float | None] = {}
        self._phone_history: dict[int, list[float]] = {}
        self._last_phone_infer = 0.0
        self._last_full_phone = 0.0
        self._imgsz = int(os.environ.get("SNITCH_YOLO_IMGSZ", "640") or "640")
        self._half = False
        self._overlay: dict[str, Any] = {"boxes": [], "zones": []}
        self._overlay_lock = threading.Lock()
        self._laya_signature_value = ""
        self._laya_latency_samples: list[float] = []
        self._health_at = 0.0
        self._config_lock = threading.Lock()
        self._config_inflight = False
        self._config_ts = 0.0
        self._occupancy: dict[tuple[str, int, str], dict[str, Any]] = {}
        self._device = "cpu"
        self._ppe_memory: dict[tuple[int, str], dict[str, Any]] = {}
        self._roi_at: dict[int, float] = {}
        self._inference_fps = 0.0

        sv = _import_supervision()
        if not config.mock:
            YOLO = _import_yolo()
            self._tracker = sv.ByteTrack()
            weights = str(config.weights_path)
            if not Path(weights).is_file():
                raise FileNotFoundError(
                    f"Pesos SH17 não encontrados em {weights}. "
                    "Defina SH17_WEIGHTS ou SNITCH_VISION_MOCK=1."
                )
            self._model = YOLO(weights)
            self._device = _resolve_device()
            try:
                self._model.to(self._device)
            except Exception:  # noqa: BLE001
                self._device = "cpu"
                self._model.to(self._device)
            self._half = self._device == "mps" and os.environ.get("SNITCH_YOLO_HALF", "1").lower() not in {"0", "false", "off"}
            print(
                f"SH17 {weights} device={self._device} imgsz={self._imgsz} half={self._half}",
                file=sys.stderr,
                flush=True,
            )
            coco_path = self._coco_weights_path(Path(weights))
            if coco_path is not None:
                self._coco = YOLO(str(coco_path))
                try:
                    self._coco.to(self._device)
                except Exception:  # noqa: BLE001
                    self._coco.to("cpu")
                print(f"COCO celular {coco_path} device={self._device}", file=sys.stderr, flush=True)
            else:
                print("COCO ausente: celular não será detectado.", file=sys.stderr, flush=True)
            import logging
            logging.getLogger("ultralytics").setLevel(logging.ERROR)
            for zone in config.zones:
                self._polygon_zones.append(
                    (zone.name, sv.PolygonZone(polygon=zone.polygon))
                )
        elif config.zones:
            for zone in config.zones:
                self._polygon_zones.append(
                    (zone.name, sv.PolygonZone(polygon=zone.polygon))
                )
            self._tracker = sv.ByteTrack()

    def _mock_detections(self, frame: np.ndarray):
        import supervision as sv

        h, w = frame.shape[:2]
        xyxy = np.array([[w * 0.3, h * 0.2, w * 0.55, h * 0.85]])
        class_id = np.array([0])
        confidence = np.array([0.9])
        return sv.Detections(xyxy=xyxy, class_id=class_id, confidence=confidence)

    def _run_yolo(self, frame: np.ndarray):
        if self.config.mock:
            return self._mock_detections(frame)

        assert self._model is not None
        results = self._predict(self._model, frame, conf=YOLO_BASE_CONF, imgsz=self._imgsz)
        import supervision as sv

        return self._filter_by_class_confidence(sv.Detections.from_ultralytics(results))

    def _predict(self, model: Any, image: np.ndarray, **kwargs: Any):
        import torch

        import warnings

        kwargs.setdefault("verbose", False)
        kwargs.setdefault("device", self._device)
        if self._half:
            kwargs["half"] = True
        try:
            with warnings.catch_warnings(), torch.inference_mode():
                warnings.filterwarnings("ignore", message=".*half.*")
                return model(image, **kwargs)[0]
        except Exception:
            if not kwargs.get("half"):
                raise
            self._half = False
            kwargs.pop("half", None)
            with torch.inference_mode():
                return model(image, **kwargs)[0]

    def _keep_detection(self, label: str, confidence: float, box: np.ndarray, anchors: list[np.ndarray]) -> bool:
        if label in {"person", "head", "face"}:
            return confidence >= STRONG_CLASS_CONF
        if label == "ear_protection":
            return confidence >= EAR_PROTECTION_CONF
        if label in SMALL_PPE_LABELS:
            if confidence < SMALL_PPE_CONF:
                return False
            if confidence >= STRONG_CLASS_CONF:
                return True
            return any(self._center_inside(box, anchor) for anchor in anchors)
        return confidence >= STRONG_CLASS_CONF

    def _center_inside(self, box: np.ndarray, outer: np.ndarray) -> bool:
        cx = (float(box[0]) + float(box[2])) / 2
        cy = (float(box[1]) + float(box[3])) / 2
        return float(outer[0]) <= cx <= float(outer[2]) and float(outer[1]) <= cy <= float(outer[3])

    def _filter_by_class_confidence(self, detections):
        if detections.class_id is None or len(detections) == 0:
            return detections
        anchors = [
            detections.xyxy[index]
            for index, class_id in enumerate(detections.class_id)
            if self._class_label(int(class_id)) in {"person", "head", "face"}
            and float(detections.confidence[index]) >= STRONG_CLASS_CONF
        ]
        keep = [
            index
            for index, class_id in enumerate(detections.class_id)
            if self._keep_detection(
                self._class_label(int(class_id)),
                float(detections.confidence[index]),
                detections.xyxy[index],
                anchors,
            )
        ]
        if not keep:
            return self._empty_detections()
        return detections[keep]

    def _class_id_for(self, label: str) -> int | None:
        names = getattr(self._model, "names", None) if self._model is not None else None
        if isinstance(names, dict):
            for class_id, name in names.items():
                if canonical_class_name(str(name)) == label or str(name) == label:
                    return int(class_id)
        if label in SH17_CLASS_NAMES:
            return SH17_CLASS_NAMES.index(label)
        return None

    def _remember_ppe(
        self,
        tracker_id: int,
        label: str,
        box: np.ndarray,
        anchor: np.ndarray,
        class_id: int,
        now: float,
    ) -> None:
        ax1, ay1, ax2, ay2 = (float(value) for value in anchor)
        width = max(ax2 - ax1, 1.0)
        height = max(ay2 - ay1, 1.0)
        self._ppe_memory[(tracker_id, label)] = {
            "until": now + PPE_MEMORY_SECONDS,
            "class_id": int(class_id),
            "rel": (
                (float(box[0]) - ax1) / width,
                (float(box[1]) - ay1) / height,
                (float(box[2]) - ax1) / width,
                (float(box[3]) - ay1) / height,
            ),
        }

    def _recall_ppe(
        self,
        tracker_id: int,
        label: str,
        anchor: np.ndarray,
        now: float,
    ) -> tuple[list[float], int] | None:
        record = self._ppe_memory.get((tracker_id, label))
        if record is None or now > float(record["until"]):
            self._ppe_memory.pop((tracker_id, label), None)
            return None
        ax1, ay1, ax2, ay2 = (float(value) for value in anchor)
        width = max(ax2 - ax1, 1.0)
        height = max(ay2 - ay1, 1.0)
        rx1, ry1, rx2, ry2 = record["rel"]
        return (
            [ax1 + rx1 * width, ay1 + ry1 * height, ax1 + rx2 * width, ay1 + ry2 * height],
            int(record["class_id"]),
        )

    def _facial_anchor(self, person_box: np.ndarray, parts) -> np.ndarray:
        face = None
        head = None
        if parts is not None and parts.class_id is not None:
            for index, class_id in enumerate(parts.class_id):
                label = self._class_label(int(class_id))
                box = parts.xyxy[index]
                if not self._center_inside(box, person_box):
                    continue
                if label == "face":
                    face = box
                elif label == "head":
                    head = box
        if face is not None:
            return np.array(face, dtype=np.float32)
        if head is not None:
            return np.array(head, dtype=np.float32)
        x1, y1, x2, y2 = (float(value) for value in person_box)
        return np.array([x1, y1, x2, y1 + 0.35 * (y2 - y1)], dtype=np.float32)

    def _labels_inside(self, outer: np.ndarray, parts) -> set[str]:
        found: set[str] = set()
        if parts is None or parts.class_id is None:
            return found
        for index, class_id in enumerate(parts.class_id):
            if self._center_inside(parts.xyxy[index], outer):
                found.add(self._class_label(int(class_id)))
        return found

    def _infer_crop(self, frame: np.ndarray, anchor: np.ndarray) -> list[tuple[list[float], int, float, str]]:
        height, width = frame.shape[:2]
        x1, y1, x2, y2 = (float(value) for value in anchor)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        box_w = max((x2 - x1) * 1.4, 24)
        box_h = max((y2 - y1) * 1.4, 24)
        left = max(0, int(cx - box_w / 2))
        top = max(0, int(cy - box_h / 2))
        right = min(width, int(cx + box_w / 2))
        bottom = min(height, int(cy + box_h / 2))
        if right - left < 12 or bottom - top < 12:
            return []
        crop = frame[top:bottom, left:right]
        assert self._model is not None
        results = self._predict(self._model, crop, conf=SMALL_PPE_CONF, imgsz=320)
        import supervision as sv

        detections = sv.Detections.from_ultralytics(results)
        if detections.class_id is None or len(detections) == 0:
            return []
        crop_h, crop_w = crop.shape[:2]
        mapped = map_boxes_to_frame(
            detections.xyxy,
            (crop_h, crop_w),
            (left, top),
            (crop_h, crop_w),
            (height, width),
        )
        found: list[tuple[list[float], int, float, str]] = []
        crop_area = max(crop_w * crop_h, 1)
        for index, class_id in enumerate(detections.class_id):
            if index >= len(mapped):
                break
            label = self._class_label(int(class_id))
            confidence = float(detections.confidence[index])
            if label not in CROP_PPE_LABELS:
                continue
            minimum = EAR_PROTECTION_CONF if label == "ear_protection" else SMALL_PPE_CONF
            if confidence < minimum:
                continue
            box = mapped[index]
            box_area = max(box[2] - box[0], 0) * max(box[3] - box[1], 0)
            if box_area > crop_area * 0.65:
                continue
            found.append((box, int(class_id), confidence, label))
        return found

    def _append_detections(self, base, rows: list[tuple[list[float], int, float]]):
        if not rows:
            return base
        import supervision as sv

        extra_xyxy = np.array([row[0] for row in rows], dtype=np.float32)
        extra_class = np.array([row[1] for row in rows], dtype=int)
        extra_conf = np.array([row[2] for row in rows], dtype=np.float32)
        if base.class_id is None or len(base) == 0:
            return sv.Detections(xyxy=extra_xyxy, class_id=extra_class, confidence=extra_conf)
        return sv.Detections(
            xyxy=np.vstack([base.xyxy, extra_xyxy]),
            class_id=np.concatenate([base.class_id, extra_class]),
            confidence=np.concatenate([
                base.confidence if base.confidence is not None else np.ones(len(base), dtype=np.float32),
                extra_conf,
            ]),
        )

    def _refine_facial_ppe(self, frame: np.ndarray, people, parts):
        if people.tracker_id is None or len(people) == 0:
            return parts
        now = time.time()
        added: list[tuple[list[float], int, float]] = []
        crops = 0
        for index, tracker_id in enumerate(people.tracker_id):
            if tracker_id is None:
                continue
            tid = int(tracker_id)
            person_box = people.xyxy[index]
            anchor = self._facial_anchor(person_box, parts)
            present = self._labels_inside(person_box, parts)
            if self._should_zoom_for_glasses(present) and crops < 1:
                self._roi_at[tid] = now
                self._roi_at[-1] = now
                crops += 1
                for box, class_id, confidence, label in self._infer_crop(frame, anchor):
                    added.append((box, class_id, confidence))
                    present.add(label)
                    self._remember_ppe(tid, label, np.array(box), anchor, class_id, now)
            for label in CROP_PPE_LABELS:
                if label in present:
                    continue
                recalled = self._recall_ppe(tid, label, anchor, now)
                if recalled is None:
                    continue
                box, class_id = recalled
                added.append((box, class_id, 0.2))
                present.add(label)
            for label in list(present):
                if label not in CROP_PPE_LABELS:
                    continue
                # A fresh box inside the person updates the relative offset.
                if parts.class_id is None:
                    continue
                for part_index, class_id in enumerate(parts.class_id):
                    if self._class_label(int(class_id)) != label:
                        continue
                    if self._center_inside(parts.xyxy[part_index], person_box):
                        self._remember_ppe(tid, label, parts.xyxy[part_index], anchor, int(class_id), now)
                        break
        expired = [key for key, record in self._ppe_memory.items() if now > float(record["until"])]
        for key in expired:
            self._ppe_memory.pop(key, None)
        return self._append_detections(parts, added)

    def _should_zoom_for_glasses(self, present: set[str]) -> bool:
        required = set(self.config.required_ppe)
        if "goggles" not in required and "glasses" not in required:
            return False
        if "goggles" in present:
            return False
        last = self._roi_at.get(-1, 0.0)
        return (time.time() - last) >= GLASSES_ZOOM_INTERVAL

    def _coco_weights_path(self, sh17: Path) -> Path | None:
        configured = os.environ.get("SNITCH_COCO_WEIGHTS", "").strip()
        candidates = []
        if configured:
            candidates.append(Path(configured))
        candidates.extend((
            sh17.parent / "yolov8n-coco.pt",
            sh17.parent / "yolov8n.pt",
            Path("/weights/yolov8n-coco.pt"),
            Path("storage/engine/yolov8n-coco.pt"),
        ))
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return None

    def _phone_limit(self) -> int | None:
        raw = self._smartphone.get("max_continuous_seconds")
        if raw is None:
            raw = self._smartphone.get("hand_limit_seconds")
        if raw is None or not str(raw).strip():
            return None
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    def _read_phone_result(self, result: Any, offset_x: float = 0.0, offset_y: float = 0.0, scale_x: float = 1.0, scale_y: float = 1.0) -> list[dict[str, Any]]:
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []
        xyxy = boxes.xyxy
        confidences = boxes.conf
        if hasattr(xyxy, "cpu"):
            xyxy = xyxy.cpu().numpy()
            confidences = confidences.cpu().numpy()
        found = []
        for box, confidence in zip(xyxy, confidences):
            found.append({
                "bbox": [
                    offset_x + float(box[0]) * scale_x,
                    offset_y + float(box[1]) * scale_y,
                    offset_x + float(box[2]) * scale_x,
                    offset_y + float(box[3]) * scale_y,
                ],
                "confidence": round(float(confidence), 3),
            })
        return found

    def _detect_phones(self, frame: np.ndarray, people, parts) -> list[dict[str, Any]]:
        """Celular no quadro inteiro. O recorte esticado devolvia caixa do tamanho da pessoa."""
        del people, parts
        if self._coco is None:
            return []
        result = self._predict(self._coco, frame, conf=PHONE_CONF, imgsz=320, classes=[COCO_PHONE_CLASS])
        height, width = frame.shape[:2]
        boxes = self._read_phone_result(result)
        frame_area = max(width * height, 1)
        kept = []
        for item in boxes:
            box = item["bbox"]
            area = max(box[2] - box[0], 0) * max(box[3] - box[1], 0)
            if area > frame_area * 0.12:
                continue
            kept.append(item)
        self._last_full_phone = time.time()
        return kept

    def _phone_boxes_for_frame(self, frame: np.ndarray, people, parts, now: float) -> list[dict[str, Any]]:
        if self._coco is None:
            return []
        due = (now - self._last_phone_infer) >= PHONE_INFER_INTERVAL
        if due:
            self._cached_phones = self._detect_phones(frame, people, parts)
            self._cached_phones_at = now
            self._last_phone_infer = now
        elif now - self._cached_phones_at > PHONE_HOLD_SECONDS:
            self._cached_phones = []
        return list(self._cached_phones)

    def _box_area(self, box) -> float:
        return max(float(box[2]) - float(box[0]), 0.0) * max(float(box[3]) - float(box[1]), 0.0)

    def _intersection_ratio(self, inner, outer) -> float:
        area = self._box_area(inner)
        if area <= 0:
            return 0.0
        x1 = max(float(inner[0]), float(outer[0]))
        y1 = max(float(inner[1]), float(outer[1]))
        x2 = min(float(inner[2]), float(outer[2]))
        y2 = min(float(inner[3]), float(outer[3]))
        overlap = max(x2 - x1, 0.0) * max(y2 - y1, 0.0)
        return overlap / area

    def _phone_near_person(self, phone: list[float], person_box: np.ndarray, parts) -> bool:
        if self._box_area(phone) > self._box_area(person_box):
            return False
        if self._intersection_ratio(phone, person_box) >= 0.3:
            return True
        if parts is None or parts.class_id is None:
            return False
        for index, class_id in enumerate(parts.class_id):
            if self._class_label(int(class_id)) != "hand":
                continue
            hand = parts.xyxy[index]
            if self._intersection_ratio(hand, person_box) < 0.3:
                continue
            if self._intersection_ratio(phone, hand) >= 0.3:
                return True
        return False

    def _match_phone(self, phone_boxes: list[Any], person_box: np.ndarray, parts) -> tuple[list[float] | None, float | None]:
        for item in phone_boxes:
            if isinstance(item, dict):
                box = [float(value) for value in item["bbox"]]
                confidence = item.get("confidence")
            else:
                box = [float(value) for value in item]
                confidence = None
            if self._phone_near_person(box, person_box, parts):
                return box, None if confidence is None else float(confidence)
        return None, None

    def _phone_geometry(self, phone: list[float], person_box: np.ndarray, parts) -> dict[str, bool]:
        hands_overlap = False
        near_face = False
        near_ear = False
        in_front = False
        phone_array = np.array(phone, dtype=np.float32)
        if parts is not None and parts.class_id is not None:
            for index, class_id in enumerate(parts.class_id):
                label = self._class_label(int(class_id))
                box = parts.xyxy[index]
                if label == "hand" and (
                    self._center_inside(phone_array, box) or self._center_inside(box, phone_array)
                ):
                    hands_overlap = True
                if label == "face":
                    if self._center_inside(phone_array, box):
                        in_front = True
                        near_face = True
                    elif self._center_distance(phone_array, box) <= max(48.0, float(box[3] - box[1]) * 1.3):
                        near_face = True
                if label == "head":
                    hx1, hy1, hx2, hy2 = (float(value) for value in box)
                    pcx = (phone[0] + phone[2]) / 2
                    pcy = (phone[1] + phone[3]) / 2
                    width = max(hx2 - hx1, 1.0)
                    side = pcx <= hx1 + width * 0.22 or pcx >= hx2 - width * 0.22
                    if side and hy1 <= pcy <= hy1 + (hy2 - hy1) * 0.6:
                        near_ear = True
        if not near_face and self._center_inside(phone_array, person_box):
            x1, y1, x2, y2 = (float(value) for value in person_box)
            pcy = (phone[1] + phone[3]) / 2
            if pcy <= y1 + (y2 - y1) * 0.45:
                near_face = True
        return {
            "hands_overlap": hands_overlap,
            "near_face": near_face,
            "near_ear": near_ear,
            "in_front_of_face": in_front,
        }

    def _center_distance(self, left: np.ndarray, right: np.ndarray) -> float:
        lx = (float(left[0]) + float(left[2])) / 2
        ly = (float(left[1]) + float(left[3])) / 2
        rx = (float(right[0]) + float(right[2])) / 2
        ry = (float(right[1]) + float(right[3])) / 2
        return math.hypot(lx - rx, ly - ry)

    def _observe_smartphones(self, people, phone_boxes: list[Any], parts, now: float) -> list[dict[str, Any]]:
        if people.tracker_id is None or len(people) == 0:
            return []
        limit = self._phone_limit()
        seen: set[int] = set()
        statuses: list[dict[str, Any]] = []
        for index, tracker_id in enumerate(people.tracker_id):
            if tracker_id is None:
                continue
            tid = int(tracker_id)
            person_box = people.xyxy[index]
            matched, confidence = self._match_phone(phone_boxes, person_box, parts)
            if matched is not None:
                self._phone_hold[tid] = now
                self._phone_boxes[tid] = matched
                self._phone_confidence[tid] = confidence
                self._phone_since.setdefault(tid, now)
                self._phone_history.setdefault(tid, []).append(now)
            elif tid in self._phone_hold and now - self._phone_hold[tid] <= PHONE_HOLD_SECONDS:
                matched = self._phone_boxes.get(tid)
                confidence = self._phone_confidence.get(tid)
            else:
                self._phone_since.pop(tid, None)
                self._phone_hold.pop(tid, None)
                self._phone_boxes.pop(tid, None)
                self._phone_confidence.pop(tid, None)
                self._phone_history.pop(tid, None)
                continue
            if matched is None or tid not in self._phone_since:
                continue
            seen.add(tid)
            history = [stamp for stamp in self._phone_history.get(tid, []) if now - stamp <= PHONE_HOLD_SECONDS]
            self._phone_history[tid] = history
            seconds = max(0, int(now - self._phone_since[tid]))
            geometry = self._phone_geometry(matched, person_box, parts)
            statuses.append({
                "tracker_id": tid,
                "active": True,
                "seconds": seconds,
                "limit": limit,
                "exceeded": bool(limit is not None and seconds >= limit),
                "bbox": [round(float(value), 1) for value in matched],
                "confidence": confidence,
                "employee_id": self._employee_id_for_tracker(tid),
                "recent_hits": len(history),
                **geometry,
            })
        stale = [tracker for tracker in self._phone_since if tracker not in seen]
        for tracker in stale:
            if now - self._phone_hold.get(tracker, 0.0) > PHONE_HOLD_SECONDS:
                self._phone_since.pop(tracker, None)
                self._phone_hold.pop(tracker, None)
                self._phone_boxes.pop(tracker, None)
                self._phone_confidence.pop(tracker, None)
                self._phone_history.pop(tracker, None)
        return statuses

    def _draw_phones(self, frame: np.ndarray, phones: list[dict[str, Any]]) -> np.ndarray:
        labels: list[tuple[str, int, int, tuple[int, int, int], tuple[float, float, float, float]]] = []
        color = (255, 0, 255)
        for phone in phones:
            if not phone.get("active"):
                continue
            x1, y1, x2, y2 = (int(value) for value in phone["bbox"])
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            limit = phone.get("limit")
            text = f"Celular · {int(phone['seconds'])}s"
            if limit:
                text = f"{text} / {int(limit)}s"
            labels.append((text, x1, max(0, y1 - 22), color, tuple(float(value) for value in phone["bbox"])))
        if not labels:
            return frame
        return draw_unicode_labels(frame, layout_detection_labels(labels))

    def _class_label(self, class_id: int) -> str:
        names = getattr(self._model, "names", None) if self._model is not None else None
        return lookup_class_name(class_id, names)

    def _box_label(self, class_id: int, tracker_id: int | None) -> str:
        label = display_class_name(self._class_label(class_id))
        if tracker_id is None:
            return label
        link = self._tracker_links.get(str(tracker_id))
        who = ""
        if isinstance(link, dict) and link.get("name"):
            who = f" {link['name']}"
        return f"[#{tracker_id}{who}] {label}"

    def _annotate(
        self,
        frame: np.ndarray,
        detections,
        missing_labels: dict[int, list[str]] | None = None,
    ) -> np.ndarray:
        import supervision as sv

        box_annotator = sv.BoxAnnotator(thickness=2)
        annotated = box_annotator.annotate(scene=frame.copy(), detections=detections)
        if detections.xyxy is None or len(detections) == 0:
            return annotated
        class_ids = list(detections.class_id) if detections.class_id is not None else []
        tracker_ids = list(detections.tracker_id) if detections.tracker_id is not None else []
        labels: list[tuple[str, int, int, tuple[int, int, int]]] = []
        for index, class_id in enumerate(class_ids):
            raw_tracker = tracker_ids[index] if index < len(tracker_ids) else None
            tracker_id = None if raw_tracker is None else int(raw_tracker)
            text = self._box_label(int(class_id), tracker_id)
            if tracker_id is not None and missing_labels and missing_labels.get(tracker_id):
                text = f"{text} · falta {', '.join(missing_labels[tracker_id])}"
            x1, y1, x2, y2 = (float(value) for value in detections.xyxy[index])
            labels.append((text, int(x1), max(0, int(y1) - 22), (255, 255, 255), (x1, y1, x2, y2)))
        return draw_unicode_labels(annotated, layout_detection_labels(labels))

    def _zone_hits(self, detections) -> dict[int, list[str]]:
        hits: dict[int, list[str]] = {}
        if self.config.mock or not self._polygon_zones:
            return hits

        for name, zone in self._polygon_zones:
            mask = zone.trigger(detections=detections)
            for idx, inside in enumerate(mask):
                if not inside:
                    continue
                tracker_id = int(detections.tracker_id[idx]) if detections.tracker_id is not None else idx
                hits.setdefault(tracker_id, []).append(name)
        return hits

    def _persons_from_tracks(
        self,
        detections,
        zone_hits: dict[int, list[str]],
        parts=None,
    ) -> list[TrackedPerson]:
        persons: list[TrackedPerson] = []
        if detections.tracker_id is None:
            return persons

        by_tracker: dict[int, dict[str, Any]] = {}
        for i, tracker_id in enumerate(detections.tracker_id):
            if tracker_id is None:
                continue
            class_id = int(detections.class_id[i]) if detections.class_id is not None else 0
            if self._class_label(class_id) != "person":
                continue
            tid = int(tracker_id)
            source = parts if parts is not None else detections
            by_tracker[tid] = {"bbox": detections.xyxy[i], "ppe": self._ppe_for_person(detections.xyxy[i], source)}

        for tid, data in by_tracker.items():
            detected = sorted(set(data["ppe"]))
            missing = [p for p in self.config.required_ppe if p not in detected]
            bbox = tuple(float(x) for x in data["bbox"])
            persons.append(
                TrackedPerson(
                    tracker_id=tid,
                    bbox_xyxy=bbox,  # type: ignore[arg-type]
                    in_zones=zone_hits.get(tid, []),
                    ppe_detected=detected,
                    ppe_missing=missing,
                )
            )
        return persons

    def _polygon_pixels(self, polygon: np.ndarray, width: int, height: int) -> np.ndarray:
        points = np.array(polygon, dtype=np.float32)
        if points.size and float(np.nanmax(points)) <= 1.0:
            points = points.copy()
            points[:, 0] *= width
            points[:, 1] *= height
        return points

    def _employee_id_for_tracker(self, tracker_id: int) -> int | None:
        link = self._tracker_links.get(str(tracker_id))
        if isinstance(link, dict) and link.get("employee_id"):
            return int(link["employee_id"])
        return None

    def _zone_caption(self, zone: ZoneConfig, elapsed_s: int, occupied: bool) -> str:
        kind = "Restrita" if zone.zone_type in {"restrita", "risk"} else "Passagem"
        if zone.max_dwell_seconds:
            shown = elapsed_s if occupied else 0
            return f"{zone.name} · {kind} · {shown}s / {zone.max_dwell_seconds}s"
        if occupied:
            return f"{zone.name} · {kind} · {elapsed_s}s"
        return f"{zone.name} · {kind}"

    def _touch_occupancy(self, key: tuple[str, int, str], item: dict[str, Any], now: float) -> None:
        record = self._occupancy.get(key)
        if record is None:
            record = {"started": now}
            self._occupancy[key] = record
        record["last_seen"] = now
        record["present"] = True
        record["tracker_id"] = item["tracker_id"]
        record["employee_id"] = item["employee_id"]
        record["center"] = item["center"]
        record["zone"] = item["zone"]

    def _grace_donor(
        self,
        item: dict[str, Any],
        now: float,
        present_ids: set[int],
    ) -> tuple[str, int, str] | None:
        best_key: tuple[str, int, str] | None = None
        best_distance = DWELL_REID_PIXELS
        cx, cy = item["center"]
        for key, record in self._occupancy.items():
            kind, ident, zone_name = key
            if kind != "tracker" or zone_name != item["zone"].name or ident in present_ids:
                continue
            if now - float(record["last_seen"]) > DWELL_GRACE_SECONDS:
                continue
            ox, oy = record["center"]
            distance = math.hypot(cx - ox, cy - oy)
            if distance <= best_distance:
                best_distance = distance
                best_key = key
        return best_key

    def _absorb_presence(self, present: list[dict[str, Any]], now: float) -> None:
        for record in self._occupancy.values():
            record["present"] = False
        claimed: set[int] = set()
        for index, item in enumerate(present):
            employee_id = item["employee_id"]
            if employee_id is None:
                continue
            zone_name = item["zone"].name
            key = ("employee", int(employee_id), zone_name)
            tracker_key = ("tracker", int(item["tracker_id"]), zone_name)
            if key not in self._occupancy and tracker_key in self._occupancy:
                self._occupancy[key] = self._occupancy.pop(tracker_key)
            self._touch_occupancy(key, item, now)
            claimed.add(index)
        for index, item in enumerate(present):
            if index in claimed or item["employee_id"] is not None:
                continue
            key = ("tracker", int(item["tracker_id"]), item["zone"].name)
            if key in self._occupancy:
                self._touch_occupancy(key, item, now)
                claimed.add(index)
        present_ids: dict[str, set[int]] = {}
        for item in present:
            present_ids.setdefault(item["zone"].name, set()).add(int(item["tracker_id"]))
        for index, item in enumerate(present):
            if index in claimed or item["employee_id"] is not None:
                continue
            donor = self._grace_donor(item, now, present_ids.get(item["zone"].name, set()))
            key = ("tracker", int(item["tracker_id"]), item["zone"].name)
            if donor is not None and donor != key:
                self._occupancy[key] = self._occupancy.pop(donor)
            self._touch_occupancy(key, item, now)
        self._occupancy = {
            key: record
            for key, record in self._occupancy.items()
            if record.get("present") or now - float(record["last_seen"]) <= DWELL_GRACE_SECONDS
        }

    def _zone_dwell_payload(self, now: float) -> tuple[dict[int, list[str]], list[str], list[dict[str, Any]]]:
        hits: dict[int, list[str]] = {}
        exceeded: list[str] = []
        grouped: dict[str, dict[str, Any]] = {}
        for zone in self.config.zones:
            grouped[zone.name] = {
                "name": zone.name,
                "zone_id": zone.zone_id,
                "type": zone.zone_type,
                "max_dwell_seconds": zone.max_dwell_seconds,
                "elapsed_s": 0,
                "occupied": False,
                "present": False,
                "exceeded": False,
                "tracker_id": None,
                "employee_id": None,
                "label": self._zone_caption(zone, 0, False),
            }
        for record in self._occupancy.values():
            zone: ZoneConfig = record["zone"]
            elapsed = max(0, int(now - float(record["started"])))
            slot = grouped.get(zone.name)
            if slot is None:
                continue
            passage = zone.zone_type in {"passagem", "passage"}
            restricted = zone.zone_type in {"restrita", "risk"}
            over = bool(passage and zone.max_dwell_seconds and elapsed >= int(zone.max_dwell_seconds))
            present = bool(record.get("present"))
            slot["occupied"] = True
            slot["present"] = bool(slot["present"] or present)
            slot["exceeded"] = bool(slot["exceeded"] or over)
            if elapsed >= int(slot["elapsed_s"]):
                slot["elapsed_s"] = elapsed
                slot["tracker_id"] = int(record["tracker_id"])
                slot["employee_id"] = record.get("employee_id")
                slot["label"] = self._zone_caption(zone, elapsed, True)
            if present and restricted:
                hits.setdefault(int(record["tracker_id"]), []).append(zone.name)
            elif present and over:
                hits.setdefault(int(record["tracker_id"]), []).append(zone.name)
                if zone.name not in exceeded:
                    exceeded.append(zone.name)
        return hits, exceeded, list(grouped.values())

    def _zone_status(
        self,
        detections,
        width: int,
        height: int,
        now: float | None = None,
    ) -> tuple[dict[int, list[str]], list[str], list[dict[str, Any]]]:
        clock = time.time() if now is None else now
        if not self.config.zones:
            return {}, [], []
        present: list[dict[str, Any]] = []
        if detections.tracker_id is not None and detections.class_id is not None:
            person_rows = [
                index
                for index, tracker_id in enumerate(detections.tracker_id)
                if tracker_id is not None and self._class_label(int(detections.class_id[index])) == "person"
            ]
            if person_rows:
                people = detections[person_rows]
                for zone in self.config.zones:
                    polygon = self._polygon_pixels(zone.polygon, width, height)
                    for index in range(len(people)):
                        if people.tracker_id[index] is None:
                            continue
                        box = people.xyxy[index]
                        if not person_intersects_zone(box, polygon):
                            continue
                        tracker_id = int(people.tracker_id[index])
                        present.append({
                            "tracker_id": tracker_id,
                            "employee_id": self._employee_id_for_tracker(tracker_id),
                            "center": (
                                (float(box[0]) + float(box[2])) / 2.0,
                                (float(box[1]) + float(box[3])) / 2.0,
                            ),
                            "zone": zone,
                        })
        self._absorb_presence(present, clock)
        return self._zone_dwell_payload(clock)

    def _draw_zones(self, frame: np.ndarray, zone_dwell: list[dict[str, Any]]) -> np.ndarray:
        if not self.config.zones:
            return frame
        by_name = {str(item["name"]): item for item in zone_dwell}
        labels: list[tuple[str, int, int, tuple[int, int, int]]] = []
        height, width = frame.shape[:2]
        for zone in self.config.zones:
            info = by_name.get(zone.name, {})
            polygon = self._polygon_pixels(zone.polygon, width, height).astype(np.int32)
            if info.get("exceeded") or (zone.zone_type in {"restrita", "risk"} and info.get("occupied")):
                color = (40, 40, 220)
            elif info.get("occupied"):
                color = (0, 180, 255)
            else:
                color = (80, 180, 80)
            cv2.polylines(frame, [polygon], isClosed=True, color=color, thickness=2)
            title = str(info.get("label") or self._zone_caption(zone, 0, False))
            anchor_x = int(polygon[0][0])
            anchor_y = max(0, int(polygon[0][1]) - 22)
            labels.append((title, anchor_x, anchor_y, color))
        return draw_unicode_labels(frame, labels)

    def _person_indices(self, detections) -> list[int]:
        if detections.class_id is None:
            return []
        return [
            index
            for index, class_id in enumerate(detections.class_id)
            if self._class_label(int(class_id)) == "person"
        ]

    def _empty_detections(self):
        import supervision as sv

        return sv.Detections(
            xyxy=np.empty((0, 4), dtype=np.float32),
            class_id=np.empty((0,), dtype=int),
            confidence=np.empty((0,), dtype=np.float32),
        )

    def _track_people_only(self, detections):
        import supervision as sv

        person_idx = self._person_indices(detections)
        other_idx = [index for index in range(len(detections)) if index not in set(person_idx)]
        parts = detections[other_idx] if other_idx else self._empty_detections()
        if not person_idx:
            return self._empty_detections(), parts
        people = detections[person_idx]
        if self.config.mock:
            people.tracker_id = np.array([1] * len(people))
            return people, parts
        if self._tracker is not None:
            people = self._tracker.update_with_detections(people)
        return people, parts

    def _ppe_for_person(self, person_box: np.ndarray, detections) -> list[str]:
        found: list[str] = []
        if detections.class_id is None:
            return found
        x1, y1, x2, y2 = (float(v) for v in person_box)
        for index, class_id in enumerate(detections.class_id):
            label = self._class_label(int(class_id))
            if label == "person" or label not in self.config.required_ppe and label not in PPE_BODY_MAP:
                continue
            box = detections.xyxy[index]
            cx = float(box[0] + box[2]) / 2
            cy = float(box[1] + box[3]) / 2
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                found.append(label)
        return found

    def process_frame(self, frame: np.ndarray, *, render: bool = True) -> tuple[np.ndarray, dict[str, Any]]:
        detect_started = time.perf_counter()
        people, parts = self._track_people_only(self._run_yolo(frame))
        phones: list[dict[str, Any]] = []
        if not self.config.mock:
            parts = self._refine_facial_ppe(frame, people, parts)
            phones = self._observe_smartphones(
                people,
                self._phone_boxes_for_frame(frame, people, parts, time.time()),
                parts,
                time.time(),
            )
        detect_elapsed = time.perf_counter() - detect_started
        self._inference_fps = round(1.0 / detect_elapsed, 1) if detect_elapsed > 0 else 0.0
        zone_hits, dwell_exceeded, zone_dwell = self._zone_status(people, frame.shape[1], frame.shape[0])
        persons = self._persons_from_tracks(people, zone_hits, parts)
        state = build_jev_state(
            camera_id=self.config.camera_id,
            frame_index=self._frame_index,
            persons=persons,
            zones=[{"name": z.name} for z in self.config.zones],
        )

        if not self.config.mock:
            self._schedule_config()
        state["smartphone"] = dict(self._smartphone)
        state["smartphones"] = phones
        for person in state["persons"]:
            match = next((item for item in phones if item["tracker_id"] == person["tracker_id"]), None)
            person["smartphone_active"] = bool(match)
            person["smartphone_seconds"] = int(match["seconds"]) if match else 0
        state["dwell_exceeded"] = dwell_exceeded
        state["zone_dwell"] = zone_dwell
        self._attach_missing_ppe(state)
        self._attach_laya_phone(state)
        self._attach_jev(state, persons)
        missing_labels = {
            int(person["tracker_id"]): list(person.get("missing_ppe_labels_pt") or [])
            for person in state["persons"]
            if person.get("missing_ppe_labels_pt")
        }
        overlay = self._collect_overlay(people, parts, phones, zone_dwell, frame.shape[1], frame.shape[0], missing_labels)
        self._store_overlay(overlay)
        annotated = render_scene(frame, overlay) if render else frame
        telemetry = dict(state.get("telemetry") or {})
        telemetry["inference_fps"] = self._inference_fps
        telemetry["imgsz"] = self._imgsz
        telemetry["device"] = self._device
        state["telemetry"] = telemetry
        if persons and not self.config.mock:
            self._maybe_record_episode(frame, state)
        self._frame_index += 1
        return annotated, state

    def _store_overlay(self, overlay: dict[str, Any]) -> None:
        with self._overlay_lock:
            self._overlay = overlay

    def overlay_snapshot(self) -> dict[str, Any]:
        with self._overlay_lock:
            return self._overlay

    def _collect_overlay(self, people, parts, phones, zone_dwell, width, height, missing_labels) -> dict[str, Any]:
        boxes = self._detection_overlay(people, missing_labels, (80, 220, 80))
        boxes.extend(self._detection_overlay(parts, None, (80, 180, 255)))
        for phone in phones:
            if not phone.get("active"):
                continue
            limit = phone.get("limit")
            text = f"Celular · {int(phone['seconds'])}s"
            if limit:
                text = f"{text} / {int(limit)}s"
            boxes.append({"xyxy": phone["bbox"], "label": text, "color": (255, 0, 255)})
        zones = []
        by_name = {str(item["name"]): item for item in zone_dwell}
        for zone in self.config.zones:
            info = by_name.get(zone.name, {})
            polygon = self._polygon_pixels(zone.polygon, width, height).astype(int).tolist()
            if info.get("exceeded") or (zone.zone_type in {"restrita", "risk"} and info.get("occupied")):
                color = (40, 40, 220)
            elif info.get("occupied"):
                color = (0, 180, 255)
            else:
                color = (80, 180, 80)
            zones.append({
                "polygon": polygon,
                "color": color,
                "label": str(info.get("label") or self._zone_caption(zone, 0, False)),
            })
        return {"boxes": boxes, "zones": zones}

    def _detection_overlay(self, detections, missing_labels, color: tuple[int, int, int]) -> list[dict[str, Any]]:
        if detections is None or detections.class_id is None or len(detections) == 0:
            return []
        tracker_ids = list(detections.tracker_id) if detections.tracker_id is not None else []
        rows = []
        for index, class_id in enumerate(detections.class_id):
            raw_tracker = tracker_ids[index] if index < len(tracker_ids) else None
            tracker_id = None if raw_tracker is None else int(raw_tracker)
            text = self._box_label(int(class_id), tracker_id)
            if tracker_id is not None and missing_labels and missing_labels.get(tracker_id):
                text = f"{text} · falta {', '.join(missing_labels[tracker_id])}"
            rows.append({
                "xyxy": [float(value) for value in detections.xyxy[index]],
                "label": text,
                "color": color,
            })
        return rows

    def _attach_jev(self, state: dict[str, Any], persons: list[TrackedPerson]) -> None:
        if _env_flag("SNITCH_JEV_SYNC"):
            if self.config.jev_url and persons:
                self._ask_jev_now(state)
        else:
            self._schedule_jev(state, persons)
            with self._jev_lock:
                if self._last_jev is not None:
                    state["jev"] = self._last_jev
                elif self._last_jev_error:
                    state["jev_error"] = self._last_jev_error

        with self._jev_lock:
            state["telemetry"] = {
                "frame_index": self._frame_index,
                "jev_updated_at": self._last_jev_ts,
                "jev_latency_ms": self._last_jev_latency_ms,
                "laya_engine": self._laya_engine,
                "inference_fps": self._inference_fps,
                "laya_latency_avg_ms": (
                    round(sum(self._laya_latency_samples) / len(self._laya_latency_samples), 1)
                    if self._laya_latency_samples else None
                ),
            }

    def _laya_signature(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))

    def _schedule_jev(self, state: dict[str, Any], persons: list[TrackedPerson]) -> None:
        if not self.config.jev_url or not persons:
            return
        interval = float(os.environ.get("SNITCH_JEV_INTERVAL", "1.5"))
        payload = compact_laya_payload(state)
        signature = self._laya_signature(payload)
        now = time.time()
        with self._jev_lock:
            if self._jev_inflight:
                return
            unchanged = signature == self._laya_signature_value and self._last_jev is not None
            if unchanged and (now - self._last_jev_ts) < max(interval, 2.0):
                return
            self._jev_inflight = True
        threading.Thread(
            target=self._ask_jev_background,
            args=(payload, signature),
            name="snitch-jev",
            daemon=True,
        ).start()

    def _ask_jev_background(self, snapshot: dict[str, Any], signature: str) -> None:
        try:
            if self._ask_jev_now(snapshot):
                self._laya_signature_value = signature
        finally:
            with self._jev_lock:
                self._jev_inflight = False

    def _ask_jev_now(self, state: dict[str, Any]) -> bool:
        started = time.perf_counter()
        try:
            answers = ask_jev_sync(
                self.config.jev_url,
                state,
                list(self.config.jev_questions),
            )
            latency_ms = (time.perf_counter() - started) * 1000
            with self._jev_lock:
                previous = list(self._laya_latency_samples)
                previous.append(latency_ms)
                self._laya_latency_samples = previous[-8:]
                self._last_jev = answers
                self._last_jev_error = None
                self._last_jev_ts = time.time()
                self._last_jev_latency_ms = latency_ms
            self._remember_laya_engine()
            state["jev"] = answers
            return True
        except Exception as exc:  # noqa: BLE001 — motor continua se Jev estiver offline
            with self._jev_lock:
                self._last_jev_error = str(exc)
            state["jev_error"] = str(exc)
            return False

    def _attach_laya_phone(self, state: dict[str, Any]) -> None:
        jev = state.get("jev") if isinstance(state.get("jev"), dict) else self._last_jev or {}
        if not isinstance(jev, dict):
            jev = {}
        idle = jev.get("any_smartphone_idle")
        using = jev.get("any_person_using_smartphone")
        if idle is True or using is True:
            reason = "laya"
            confirmed: bool | None = True
            available = True
        elif idle is False or using is False:
            reason = "laya_nao_confirmou"
            confirmed = False
            available = True
        else:
            reason = "laya_indisponivel"
            confirmed = None
            available = False
        labels = {
            "laya": "Laya confirmou o uso",
            "laya_nao_confirmou": "Laya não confirmou o uso",
            "laya_indisponivel": "Laya indisponível",
        }
        samples = list(self._laya_latency_samples)
        average = round(sum(samples) / len(samples), 1) if samples else None
        state["laya_phone"] = {
            "available": available,
            "confirmed": confirmed,
            "reason": reason,
            "label": labels[reason],
            "latency_ms": self._last_jev_latency_ms,
            "latency_avg_ms": average,
        }

    def _remember_laya_engine(self) -> None:
        now = time.time()
        if now - self._health_at < 15 and self._laya_engine:
            return
        self._health_at = now
        engine = self._read_laya_engine()
        if engine:
            with self._jev_lock:
                self._laya_engine = engine

    def _read_laya_engine(self) -> str | None:
        if not self.config.jev_url:
            return None
        url = self.config.jev_url.rstrip("/") + "/health"
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                body = json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            return None
        engine = body.get("engine") if isinstance(body, dict) else None
        return str(engine) if engine else None

    def _maybe_record_episode(self, annotated: np.ndarray, state: dict[str, Any]) -> None:
        web = os.environ.get("SNITCH_WEB_URL", "").rstrip("/")
        if not web:
            return
        jev = state.get("jev") if isinstance(state.get("jev"), dict) else {}
        location_id = int(os.environ.get("SNITCH_LOCATION_ID", "2"))
        jobs: list[tuple[str, str, dict[str, Any]]] = []
        missing_items, missing_labels, detected_items = self._missing_ppe_report(state)
        if missing_items:
            jobs.append((
                "missing_ppe",
                f"{web}/snitch/episodes/ppe",
                {
                    "employee_id": self._linked_employee_id(state),
                    "location_id": location_id,
                    "camera_id": self.config.camera_id,
                    "required_ppe": list(self.config.required_ppe),
                    "detected_ppe": detected_items,
                    "missing_ppe": missing_items,
                    "missing_items": missing_items,
                    "missing_ppe_labels_pt": missing_labels,
                },
            ))
        posted_restricted = False
        for zone in state.get("zone_dwell") or []:
            if not isinstance(zone, dict) or not zone.get("present"):
                continue
            kind = str(zone.get("type") or "")
            restricted = kind in {"restrita", "risk"}
            passage = kind in {"passagem", "passage"} and bool(zone.get("exceeded"))
            if not restricted and not passage:
                continue
            zone_key = zone.get("zone_id") or zone.get("name")
            jobs.append((
                f"idle_zone:{zone_key}",
                f"{web}/snitch/episodes/idle-zone",
                {
                    "employee_id": zone.get("employee_id"),
                    "location_id": location_id,
                    "camera_id": self.config.camera_id,
                    "zone_id": zone.get("zone_id"),
                    "zone": zone.get("name"),
                    "zone_type": "restrita" if restricted else "passagem",
                    "max_time_seconds": zone.get("max_dwell_seconds") if zone.get("max_dwell_seconds") is not None else 0,
                    "time_exceeded": True,
                    "dwell_seconds": int(zone.get("elapsed_s") or 0),
                    "tracker_id": zone.get("tracker_id"),
                },
            ))
            if restricted:
                posted_restricted = True
        phone_view = state.get("laya_phone") if isinstance(state.get("laya_phone"), dict) else {}
        phone_limit = self._phone_limit()
        for chosen in state.get("smartphones") or []:
            if not isinstance(chosen, dict) or not chosen.get("active"):
                continue
            record, source = smartphone_record_decision(
                enabled=bool(self._smartphone.get("enabled")),
                seconds=int(chosen.get("seconds") or 0),
                limit=phone_limit,
                laya_confirmed=phone_view.get("confirmed"),
                laya_available=bool(phone_view.get("available")),
            )
            if not record:
                continue
            jobs.append((
                f"smartphone:{chosen.get('tracker_id')}",
                f"{web}/snitch/episodes/smartphone",
                {
                    "enabled": True,
                    "limit_exceeded": True,
                    "employee_id": chosen.get("employee_id"),
                    "location_id": location_id,
                    "camera_id": self.config.camera_id,
                    "tracker_id": chosen.get("tracker_id"),
                    "smartphone_seconds": int(chosen.get("seconds") or 0),
                    "max_continuous_seconds": phone_limit,
                    "decision_source": source,
                    "laya_confirmed": phone_view.get("confirmed") is True,
                },
            ))
        if jev.get("any_person_in_restricted_zone") is True and not posted_restricted:
            jobs.append((
                "idle_zone:laya",
                f"{web}/snitch/episodes/idle-zone",
                {
                    "employee_id": self._linked_employee_id(state),
                    "location_id": location_id,
                    "camera_id": self.config.camera_id,
                    "zone": "restrita",
                    "zone_type": "restrita",
                    "max_time_seconds": 0,
                    "time_exceeded": True,
                    "dwell_seconds": 0,
                },
            ))
        if not jobs:
            return
        photo = "data:image/jpeg;base64," + encode_frame_jpeg(render_scene(annotated, self.overlay_snapshot()), quality=60)
        cooldown = float(os.environ.get("SNITCH_EPISODE_COOLDOWN", "30"))
        now = time.time()
        for key, url, payload in jobs:
            payload["photo"] = photo
            with self._episode_lock:
                if now - self._episode_at.get(key, 0.0) < cooldown:
                    continue
                self._episode_at[key] = now
            worker = threading.Thread(
                target=_post_json,
                args=(url, payload),
                name=f"snitch-episode-{key}",
                daemon=True,
            )
            worker.start()
            if _env_flag("SNITCH_EPISODE_SYNC"):
                worker.join(timeout=2)

    def _attach_missing_ppe(self, state: dict[str, Any]) -> None:
        items: list[str] = []
        labels: list[str] = []
        for person in state.get("persons") or []:
            if not isinstance(person, dict):
                continue
            missing = [str(item) for item in (person.get("ppe_missing") or []) if str(item).strip()]
            person_labels = [display_class_name(item) for item in missing]
            person["missing_ppe_items"] = missing
            person["missing_ppe_labels_pt"] = person_labels
            for item, label in zip(missing, person_labels):
                if item not in items:
                    items.append(item)
                    labels.append(label)
        state["missing_ppe_items"] = items
        state["missing_ppe_labels_pt"] = labels
        state["required_ppe"] = list(self.config.required_ppe)

    def _missing_ppe_report(self, state: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
        items: list[str] = []
        labels: list[str] = []
        detected: list[str] = []
        for person in state.get("persons") or []:
            if not isinstance(person, dict):
                continue
            person_items = [str(item) for item in (person.get("missing_ppe_items") or person.get("ppe_missing") or [])]
            person_labels = person.get("missing_ppe_labels_pt") or [display_class_name(item) for item in person_items]
            for item, label in zip(person_items, person_labels):
                if item not in items:
                    items.append(item)
                    labels.append(str(label))
            for item in person.get("ppe_detected") or []:
                name = str(item)
                if name not in detected:
                    detected.append(name)
        if not items:
            items = [str(item) for item in (state.get("missing_ppe_items") or [])]
            labels = [str(label) for label in (state.get("missing_ppe_labels_pt") or [])]
            if len(labels) != len(items):
                labels = [display_class_name(item) for item in items]
        return items, labels, detected

    def _linked_employee_id(self, state: dict[str, Any]) -> int | None:
        for person in state.get("persons") or []:
            link = self._tracker_links.get(str(person.get("tracker_id")))
            if isinstance(link, dict) and link.get("employee_id"):
                return int(link["employee_id"])
        return None

    def _schedule_config(self) -> None:
        web = os.environ.get("SNITCH_WEB_URL", "").rstrip("/")
        if not web:
            return
        now = time.time()
        with self._config_lock:
            if self._config_inflight or (now - self._config_ts) < 5:
                return
            self._config_inflight = True
        threading.Thread(target=self._fetch_config, args=(web,), name="snitch-config", daemon=True).start()

    def _fetch_config(self, web: str) -> None:
        url = f"{web}/snitch/cameras/{self.config.camera_id}/engine-config"
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                data = json.loads(response.read().decode())
            if isinstance(data, dict):
                self._apply_remote_config(data)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            return
        finally:
            with self._config_lock:
                self._config_inflight = False
                self._config_ts = time.time()

    def _apply_remote_config(self, data: dict[str, Any]) -> None:
        required = [str(item) for item in (data.get("required_ppe") or []) if str(item).strip()]
        if required:
            self.config.required_ppe = tuple(required)
        links = data.get("tracker_links") or {}
        if isinstance(links, dict):
            self._tracker_links = {str(key): value for key, value in links.items() if isinstance(value, dict)}
        phone = data.get("smartphone") or {}
        if isinstance(phone, dict):
            limit = phone.get("max_continuous_seconds")
            if limit is None:
                limit = phone.get("hand_limit_seconds")
            self._smartphone = {
                "enabled": bool(phone.get("enabled")),
                "hand_limit_seconds": limit,
                "max_continuous_seconds": limit,
            }
        zones: list[ZoneConfig] = []
        for item in data.get("zones") or []:
            if not isinstance(item, dict):
                continue
            polygon = item.get("polygon") or []
            if not isinstance(polygon, list) or len(polygon) < 3:
                continue
            zone_id = item.get("id")
            zones.append(
                ZoneConfig(
                    name=str(item.get("name") or "zona"),
                    polygon=np.array(polygon, dtype=np.float32),
                    zone_type=str(item.get("type") or "passagem"),
                    max_dwell_seconds=int(item["max_dwell_seconds"]) if item.get("max_dwell_seconds") else None,
                    zone_id=int(zone_id) if zone_id else None,
                )
            )
        self.config.zones = zones
        names = {zone.name for zone in zones}
        self._occupancy = {key: record for key, record in self._occupancy.items() if key[2] in names}
        if self.config.mock:
            return
        import supervision as sv

        rebuilt: list[Any] = []
        for zone in zones:
            try:
                rebuilt.append((zone.name, sv.PolygonZone(polygon=zone.polygon)))
            except Exception:  # noqa: BLE001
                continue
        self._polygon_zones = rebuilt

    def frames(
        self,
        source: str | int,
        max_frames: int | None = None,
    ) -> Iterator[tuple[np.ndarray, dict[str, Any]]]:
        capture = cv2.VideoCapture(source)
        if not capture.isOpened():
            raise RuntimeError(f"Não foi possível abrir o fluxo: {source}")

        produced = 0
        try:
            while max_frames is None or produced < max_frames:
                ok, frame = capture.read()
                if not ok:
                    if not _is_video_file(source):
                        break
                    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ok, frame = capture.read()
                    if not ok:
                        break
                yield self.process_frame(frame)
                produced += 1
        finally:
            capture.release()


def _is_video_file(source: str | int) -> bool:
    return isinstance(source, str) and not source.isdigit() and "://" not in source


def _post_json(url: str, payload: dict[str, Any]) -> None:
    data = json.dumps(payload).encode()
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return


def fallback_video_path() -> str | None:
    for candidate in (
        os.environ.get("SNITCH_FALLBACK_SOURCE", ""),
        "/weights/person-loop.avi",
        "storage/engine/person-loop.avi",
        "/clips/demo.avi",
    ):
        if candidate and Path(candidate).is_file():
            return candidate
    return None


CAMERA_PERMISSION_MESSAGE = (
    "Não consegui abrir a câmera.\n"
    "No Mac: Ajustes do Sistema → Privacidade e Segurança → Câmera, "
    "e permita Terminal ou Cursor.\n"
    "O motor segue com o vídeo de demonstração para a porta 8765 não cair."
)


def warmup_source(source: str | int) -> str | int:
    """Abre a câmera na thread principal. Se falhar, devolve um arquivo de vídeo."""
    if not isinstance(source, int):
        return source
    capture = cv2.VideoCapture(source)
    opened = capture.isOpened()
    ok = False
    if opened:
        ok, _frame = capture.read()
    capture.release()
    if opened and ok:
        return source
    print(CAMERA_PERMISSION_MESSAGE, file=sys.stderr)
    fallback = fallback_video_path()
    if fallback is None:
        raise RuntimeError(CAMERA_PERMISSION_MESSAGE)
    print(f"Usando {fallback}", file=sys.stderr)
    return fallback


def encode_frame_jpeg(frame: np.ndarray, quality: int = 80) -> str:
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("Falha ao codificar JPEG")
    return base64.b64encode(buffer.tobytes()).decode("ascii")


def load_config_from_env() -> AnalyzeStreamConfig:
    zones_json = os.environ.get("SNITCH_ZONES_JSON", "[]")
    raw_zones = json.loads(zones_json)
    zones: list[ZoneConfig] = []
    for item in raw_zones:
        zones.append(
            ZoneConfig(
                name=str(item["name"]),
                polygon=np.array(item["polygon"], dtype=np.float32),
            )
        )

    required = tuple(
        p.strip()
        for p in os.environ.get("SNITCH_REQUIRED_PPE", "helmet,vest,boots,gloves").split(",")
        if p.strip()
    )

    return AnalyzeStreamConfig(
        camera_id=int(os.environ.get("SNITCH_CAMERA_ID", "1")),
        weights_path=Path(os.environ.get("SH17_WEIGHTS", "storage/engine/sh17.pt")),
        stream_source=os.environ.get("SNITCH_STREAM_SOURCE", "0"),
        jev_url=os.environ.get("JEV_URL", "http://127.0.0.1:8787"),
        required_ppe=required,
        zones=zones,
        mock=_env_flag("SNITCH_VISION_MOCK"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SNITCH vision engine")
    parser.add_argument("--serve", action="store_true", help="Inicia servidor SSE")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--camera-id", type=int, default=None)
    parser.add_argument("--source", default=None, help="RTSP, arquivo ou índice de webcam")
    args = parser.parse_args(argv)

    config = load_config_from_env()
    if args.camera_id is not None:
        config.camera_id = args.camera_id
    source: str | int = args.source if args.source is not None else config.stream_source
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    if args.serve:
        from sse_server import run_sse_server

        source = warmup_source(source)
        run_sse_server(config, host=args.host, port=args.port, source=source)
        return 0

    analyzer = StreamAnalyzer(config)
    for annotated, state in analyzer.frames(source):
        print(json.dumps({"frame": state["frame_index"], "jev": state.get("jev")}))
        _ = annotated
    return 0


if __name__ == "__main__":
    sys.exit(main())
