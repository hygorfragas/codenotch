#!/usr/bin/env python3
"""
SNITCH — analisa fluxo RTSP/arquivo, YOLO (SH17), ByteTrack, PolygonZone,
desenha caixas e publica frames via SSE. Estado JSON vai ao Jev.
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import math
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from fact_judge import (
    IMAGE_PERSIST_SECONDS,
    IMAGE_REQUALIFY_SECONDS,
    judge_facts,
    needs_image_review,
    review_is_due,
)
from jev_client import IMAGE_QUESTIONS, ask_image, ask_jev_sync
from jev_image import crop_box, encode_jpeg, noul_is_true
from jev_metrics import jev_metrics
from phone_watch import PhoneClock, PhoneSighting, phone_near_body
from pose_read import describe_pose, face_toward_phone, nearest, phone_pose_trigger
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
}


def canonical_class_name(name: str) -> str:
    return CLASS_ALIASES.get(name, name)


def display_class_name(name: str) -> str:
    return DISPLAY_LABELS.get(name, name)


DWELL_GRACE_SECONDS = 4.5
DWELL_REID_PIXELS = 220.0
ZONE_MIN_OVERLAP = 0.15
YOLO_BASE_CONF = 0.10
STRONG_CLASS_CONF = 0.25
SMALL_PPE_CONF = 0.10
GLASSES_ZOOM_INTERVAL = 0.6
VOTE_WINDOW = 5
VOTE_NEED = 3
NANO_PHONE_CONF = 0.10
HEAD_REVIEW = frozenset({"helmet", "goggles"})
BODY_REVIEW = frozenset({"vest", "gloves"})
PPE_NMS_IOU = 0.40
SMALL_PPE_LABELS = frozenset({"goggles", "ear_protection", "mask", "gloves", "face-guard"})
CROP_PPE_LABELS = frozenset({"goggles", "helmet", "mask", "ear_protection", "face-guard"})
VOTED_PPE_LABELS = frozenset({"goggles", "ear_protection", "gloves"})


def dynamic_min_confidence(label: str, span: float) -> float:
    """Cabeça ou mão pequena (longe) exige mais confiança. Perto, o limiar desce."""
    clamped = (float(span) - 36.0) / (160.0 - 36.0)
    if clamped < 0.0:
        clamped = 0.0
    elif clamped > 1.0:
        clamped = 1.0
    if label == "goggles":
        high, low = 0.42, 0.16
    elif label == "ear_protection":
        high, low = 0.40, 0.18
    elif label == "gloves":
        high, low = 0.35, 0.15
    else:
        return SMALL_PPE_CONF
    return high - clamped * (high - low)
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
    chosen = os.environ.get("SNITCH_YOLO_DEVICE", "").strip().lower()
    if chosen in {"cpu", "mps", "cuda"}:
        return chosen
    try:
        import torch
    except Exception:  # noqa: BLE001
        return "cpu"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def coreml_requested() -> bool:
    """CoreML só no Mac, e só quando o dispositivo não foi fixado em cpu, mps ou cuda."""
    if sys.platform != "darwin":
        return False
    chosen = os.environ.get("SNITCH_YOLO_DEVICE", "").strip().lower()
    return chosen in {"", "auto", "coreml", "ane"}


def _ensure_coreml_package(weights: Path, imgsz: int = 640) -> Path:
    """Gera o pacote FP16 ao lado do .pt. 640 fica sem sufixo, para não trocar o marco do SH17."""
    suffix = "" if int(imgsz) == 640 else f"-{int(imgsz)}"
    package = weights.with_name(f"{weights.stem}{suffix}.mlpackage")
    marker = package / "Manifest.json"
    if marker.is_file() and marker.stat().st_mtime >= weights.stat().st_mtime:
        return package
    exported = Path(_import_yolo()(str(weights)).export(format="coreml", imgsz=int(imgsz), quantize=16, nms=False))
    if exported.is_dir() and exported.resolve() != package.resolve():
        if package.exists():
            shutil.rmtree(package)
        exported.rename(package)
    if not (package / "Manifest.json").is_file():
        raise FileNotFoundError(f"CoreML não gerou {package}")
    return package


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
        self._smartphone: dict[str, Any] = {"enabled": False, "hand_limit_seconds": None}
        self._config_lock = threading.Lock()
        self._config_inflight = False
        self._config_ts = 0.0
        self._occupancy: dict[tuple[str, int, str], dict[str, Any]] = {}
        self._device = "cpu"
        self._backend = "pytorch"
        self._ppe_memory: dict[tuple[int, str], dict[str, Any]] = {}
        self._ppe_votes: dict[tuple[int, str], deque[bool]] = {}
        self._vote_at: dict[int, float] = {}
        self._roi_at: dict[int, float] = {}
        self._inference_fps = 0.0
        self._phone_model = None
        self._phone_backend: str | None = None
        self._phone_unavailable = False
        self._phone_models: dict[str, Any] = {}
        self._phone_backends: dict[str, str] = {}
        self._phone_missing: set[str] = set()
        self._phone_candidates: dict[int, float] = {}
        self._pose_at: dict[int, float] = {}
        self._pose_clock = 0.0
        self._image_books: dict[int, dict[str, Any]] = {}
        self._image_lock = threading.Lock()
        self._phone_at = 0.0
        self._phone_cursor = 0
        self._phone_seen: dict[int, float] = {}
        self._phone_use: dict[int, bool] = {}
        self._phone_tracks: list[dict[str, Any]] = []
        self._phone_crop: dict[str, Any] | None = None
        self._phone_clock = PhoneClock(DWELL_GRACE_SECONDS, DWELL_REID_PIXELS)
        self._pose_model = None
        self._pose_unavailable = False
        self._pose_backend: str | None = None
        self._pose_cache: dict[int, dict[str, Any]] = {}
        self._fact_votes: dict[tuple[int, str], deque[bool]] = {}
        self._zoom_status: dict[int, str] = {}
        self._phone_votes: dict[int, deque[bool]] = {}
        self._phone_centers: dict[int, tuple[float, float]] = {}
        self._facts_sig = ""
        self._judge_at = 0.0
        self._judge_ok = False
        self._remote_verdict: dict[str, Any] | None = None
        self._remote_sig = ""

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
            self._load_model(weights)
            print(
                f"SH17 {weights} backend={self._backend} device={self._device}",
                file=sys.stderr,
                flush=True,
            )
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

    def _load_pytorch(self, weights: str) -> None:
        self._model = _import_yolo()(weights)
        self._backend = "pytorch"
        self._device = _resolve_device()
        try:
            self._model.to(self._device)
        except Exception:  # noqa: BLE001
            self._device = "cpu"
            self._model.to(self._device)

    def _load_model(self, weights: str) -> None:
        if coreml_requested():
            try:
                package = _ensure_coreml_package(Path(weights))
                self._model = _import_yolo()(str(package))
                self._backend = "coreml"
                self._device = "ane"
                self._predict(np.zeros((64, 64, 3), dtype=np.uint8), YOLO_BASE_CONF, 640)
                return
            except Exception as exc:  # noqa: BLE001 — Mac sem CoreML segue no MPS
                print(f"CoreML indisponível ({exc}); usando PyTorch.", file=sys.stderr, flush=True)
        self._load_pytorch(weights)

    def _predict(self, image: np.ndarray, conf: float, imgsz: int):
        assert self._model is not None
        if self._backend == "coreml":
            return self._model(image, verbose=False, conf=conf, imgsz=imgsz)[0]
        return self._model(image, verbose=False, conf=conf, imgsz=imgsz, device=self._device)[0]

    def _run_yolo(self, frame: np.ndarray):
        if self.config.mock:
            return self._mock_detections(frame)

        import supervision as sv

        detected = sv.Detections.from_ultralytics(self._predict(frame, YOLO_BASE_CONF, 640))
        return self._filter_by_class_confidence(detected)

    def _keep_detection(self, label: str, confidence: float, box: np.ndarray, anchors: list[np.ndarray]) -> bool:
        if label in {"person", "head", "face"}:
            return confidence >= STRONG_CLASS_CONF
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
            filtered = self._empty_detections()
        else:
            filtered = detections[keep]
        return self._per_class_nms(self._associate_ppe(filtered))

    def _box_span(self, box: np.ndarray) -> float:
        return max(float(box[2]) - float(box[0]), float(box[3]) - float(box[1]), 1.0)

    def _indices_for(self, detections, labels: set[str]) -> dict[str, list[int]]:
        grouped: dict[str, list[int]] = {label: [] for label in labels}
        if detections.class_id is None:
            return grouped
        for index, class_id in enumerate(detections.class_id):
            label = self._class_label(int(class_id))
            if label in grouped:
                grouped[label].append(index)
        return grouped

    def _first_containing(self, detections, indices: list[int], cx: float, cy: float) -> np.ndarray | None:
        point = np.array([cx, cy, cx, cy], dtype=np.float32)
        for index in indices:
            box = detections.xyxy[index]
            if self._center_inside(point, box):
                return box
        return None

    def _on_a_person(self, box: np.ndarray, person_boxes: list[np.ndarray]) -> bool:
        if not person_boxes:
            return True
        return any(self._center_inside(box, person) for person in person_boxes)

    def _anchor_for_ppe(self, label: str, box: np.ndarray, detections, grouped, person_boxes: list[np.ndarray]) -> np.ndarray | None:
        cx = (float(box[0]) + float(box[2])) / 2
        cy = (float(box[1]) + float(box[3])) / 2
        if label == "goggles":
            for kind in ("face", "head"):
                anchor = self._first_containing(detections, grouped.get(kind, []), cx, cy)
                if anchor is not None and self._on_a_person(anchor, person_boxes):
                    return anchor
            return None
        if label == "ear_protection":
            for kind in ("head", "ear"):
                anchor = self._first_containing(detections, grouped.get(kind, []), cx, cy)
                if anchor is not None and self._on_a_person(anchor, person_boxes):
                    return anchor
            return None
        if label == "gloves":
            anchor = self._first_containing(detections, grouped.get("hand", []), cx, cy)
            if anchor is not None and self._on_a_person(anchor, person_boxes):
                return anchor
            return None
        return None

    def _ppe_size_ok(self, label: str, box: np.ndarray, anchor: np.ndarray) -> bool:
        width = float(box[2]) - float(box[0])
        height = float(box[3]) - float(box[1])
        anchor_w = max(float(anchor[2]) - float(anchor[0]), 1.0)
        anchor_h = max(float(anchor[3]) - float(anchor[1]), 1.0)
        if width < 1 or height < 1:
            return False
        if label == "goggles":
            return 0.12 * anchor_w <= width <= 1.25 * anchor_w and height <= 0.9 * anchor_h
        if label == "ear_protection":
            return 0.08 * anchor_w <= width <= 1.05 * anchor_w and height <= 1.05 * anchor_h
        if label == "gloves":
            area = width * height
            anchor_area = anchor_w * anchor_h
            return 0.1 * anchor_area <= area <= 4.0 * anchor_area
        return True

    def _associate_ppe(self, detections):
        if detections.class_id is None or len(detections) == 0:
            return detections
        grouped = self._indices_for(detections, {"person", "head", "face", "ear", "hand"})
        person_boxes = [detections.xyxy[index] for index in grouped["person"]]
        keep: list[int] = []
        for index, class_id in enumerate(detections.class_id):
            label = self._class_label(int(class_id))
            if label not in VOTED_PPE_LABELS:
                keep.append(index)
                continue
            box = detections.xyxy[index]
            anchor = self._anchor_for_ppe(label, box, detections, grouped, person_boxes)
            if anchor is None or not self._ppe_size_ok(label, box, anchor):
                continue
            if float(detections.confidence[index]) < dynamic_min_confidence(label, self._box_span(anchor)):
                continue
            keep.append(index)
        if not keep:
            return self._empty_detections()
        return detections[keep]

    def _iou_one_to_many(self, box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
        x1 = np.maximum(float(box[0]), boxes[:, 0])
        y1 = np.maximum(float(box[1]), boxes[:, 1])
        x2 = np.minimum(float(box[2]), boxes[:, 2])
        y2 = np.minimum(float(box[3]), boxes[:, 3])
        inter = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
        area_box = max(0.0, float(box[2]) - float(box[0])) * max(0.0, float(box[3]) - float(box[1]))
        area_many = np.maximum(0.0, boxes[:, 2] - boxes[:, 0]) * np.maximum(0.0, boxes[:, 3] - boxes[:, 1])
        union = area_box + area_many - inter
        return np.where(union > 0, inter / union, 0.0)

    def _per_class_nms(self, detections):
        if detections.class_id is None or len(detections) == 0:
            return detections
        grouped: dict[int, list[int]] = {}
        for index, class_id in enumerate(detections.class_id):
            grouped.setdefault(int(class_id), []).append(index)
        keep: list[int] = []
        for indices in grouped.values():
            if len(indices) == 1:
                keep.append(indices[0])
                continue
            boxes = np.array([detections.xyxy[index] for index in indices], dtype=np.float32)
            scores = np.array([float(detections.confidence[index]) for index in indices], dtype=np.float32)
            order = np.argsort(-scores)
            chosen: list[int] = []
            while order.size:
                current = int(order[0])
                chosen.append(current)
                if order.size == 1:
                    break
                rest = order[1:]
                order = rest[self._iou_one_to_many(boxes[current], boxes[rest]) < PPE_NMS_IOU]
            for local in chosen:
                keep.append(indices[local])
        keep.sort()
        return detections[keep]

    def _vote_confirmed(self, tracker_id: int, label: str) -> bool:
        history = self._ppe_votes.get((tracker_id, label))
        if not history:
            return False
        return sum(1 for seen in history if seen) >= VOTE_NEED

    def _push_vote(
        self,
        tracker_id: int,
        label: str,
        present: bool,
        box: np.ndarray | None,
        anchor: np.ndarray | None,
        class_id: int | None,
        now: float,
    ) -> bool:
        history = self._ppe_votes.setdefault((tracker_id, label), deque(maxlen=VOTE_WINDOW))
        history.append(bool(present))
        self._vote_at[tracker_id] = now
        if present and box is not None and anchor is not None and class_id is not None:
            self._remember_ppe(tracker_id, label, box, anchor, class_id, now)
        return self._vote_confirmed(tracker_id, label)

    def _seed_vote(
        self,
        tracker_id: int,
        label: str,
        box: np.ndarray,
        anchor: np.ndarray,
        class_id: int,
        now: float,
    ) -> None:
        history = self._ppe_votes.setdefault((tracker_id, label), deque(maxlen=VOTE_WINDOW))
        history.clear()
        for _ in range(VOTE_NEED):
            history.append(True)
        self._vote_at[tracker_id] = now
        self._remember_ppe(tracker_id, label, box, anchor, class_id, now)

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
        if not self._vote_confirmed(tracker_id, label):
            return None
        record = self._ppe_memory.get((tracker_id, label))
        if record is None:
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
        # O pacote CoreML aceita 640 fixo. No PyTorch o recorte continua em 416.
        infer_size = 640 if self._backend == "coreml" else 416
        resized = cv2.resize(crop, (infer_size, infer_size), interpolation=cv2.INTER_CUBIC)
        results = self._predict(resized, SMALL_PPE_CONF, infer_size)
        import supervision as sv

        detections = sv.Detections.from_ultralytics(results)
        if detections.class_id is None or len(detections) == 0:
            return []
        scale_x = (right - left) / infer_size
        scale_y = (bottom - top) / infer_size
        found: list[tuple[list[float], int, float, str]] = []
        for index, class_id in enumerate(detections.class_id):
            label = self._class_label(int(class_id))
            confidence = float(detections.confidence[index])
            if label not in CROP_PPE_LABELS or confidence < SMALL_PPE_CONF:
                continue
            box = detections.xyxy[index]
            found.append((
                [
                    left + float(box[0]) * scale_x,
                    top + float(box[1]) * scale_y,
                    left + float(box[2]) * scale_x,
                    top + float(box[3]) * scale_y,
                ],
                int(class_id),
                confidence,
                label,
            ))
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

    def _glasses_required(self) -> bool:
        required = set(self.config.required_ppe)
        return "goggles" in required or "glasses" in required

    def _owned_voted_parts(self, person_box: np.ndarray, parts) -> dict[str, tuple[np.ndarray, int, float, int]]:
        owned: dict[str, tuple[np.ndarray, int, float, int]] = {}
        if parts is None or parts.class_id is None:
            return owned
        for part_index, class_id in enumerate(parts.class_id):
            label = self._class_label(int(class_id))
            if label not in VOTED_PPE_LABELS:
                continue
            box = parts.xyxy[part_index]
            if not self._center_inside(box, person_box):
                continue
            confidence = float(parts.confidence[part_index]) if parts.confidence is not None else 0.0
            current = owned.get(label)
            if current is None or confidence >= current[2]:
                owned[label] = (box, int(class_id), confidence, part_index)
        return owned

    def _vote_anchor(self, label: str, person_box: np.ndarray, parts, box: np.ndarray | None) -> np.ndarray | None:
        if label != "gloves":
            return self._facial_anchor(person_box, parts)
        hands: list[np.ndarray] = []
        if parts is not None and parts.class_id is not None:
            for index, class_id in enumerate(parts.class_id):
                if self._class_label(int(class_id)) != "hand":
                    continue
                hand = parts.xyxy[index]
                if self._center_inside(hand, person_box):
                    hands.append(hand)
        if box is not None:
            for hand in hands:
                if self._center_inside(box, hand):
                    return hand
        if hands:
            return hands[0]
        return None

    def _refine_facial_ppe(self, frame: np.ndarray, people, parts):
        if people.tracker_id is None or len(people) == 0:
            return parts
        now = time.time()
        added: list[tuple[list[float], int, float]] = []
        drop: set[int] = set()
        owned_by: set[int] = set()
        observations: list[tuple[int, np.ndarray, dict[str, tuple[np.ndarray, int, float, int]]]] = []
        zoom_target: tuple[int, np.ndarray] | None = None
        for index, tracker_id in enumerate(people.tracker_id):
            if tracker_id is None:
                continue
            tid = int(tracker_id)
            person_box = people.xyxy[index]
            owned = self._owned_voted_parts(person_box, parts)
            for payload in owned.values():
                owned_by.add(payload[3])
            observations.append((tid, person_box, owned))
            history = self._ppe_votes.get((tid, "goggles"))
            misses = 0 if history is None else sum(1 for seen in history if not seen)
            if (
                zoom_target is None
                and self._glasses_required()
                and "goggles" not in owned
                and history is not None
                and len(history) >= VOTE_WINDOW - 1
                and misses >= VOTE_NEED
                and now - self._roi_at.get(-1, 0.0) >= GLASSES_ZOOM_INTERVAL
            ):
                zoom_target = (tid, self._facial_anchor(person_box, parts))
        zoom_tid: int | None = None
        glasses_seeded = False
        if zoom_target is not None:
            zoom_tid, anchor = zoom_target
            self._roi_at[-1] = now
            for box, class_id, confidence, label in self._infer_crop(frame, anchor):
                if label == "goggles" and confidence >= dynamic_min_confidence("goggles", self._box_span(anchor)):
                    found = np.array(box, dtype=np.float32)
                    self._seed_vote(zoom_tid, "goggles", found, anchor, class_id, now)
                    added.append((found.tolist(), class_id, confidence))
                    glasses_seeded = True
                    break
                if label not in VOTED_PPE_LABELS:
                    added.append((box, class_id, confidence))
            self._zoom_status[zoom_tid] = "found" if glasses_seeded else "missed"
        for tid, person_box, owned in observations:
            for label in VOTED_PPE_LABELS:
                if glasses_seeded and label == "goggles" and tid == zoom_tid:
                    continue
                found = owned.get(label)
                if found is None:
                    anchor = self._vote_anchor(label, person_box, parts, None)
                    if self._push_vote(tid, label, False, None, None, None, now) and anchor is not None:
                        recalled = self._recall_ppe(tid, label, anchor, now)
                        if recalled is not None:
                            box, class_id = recalled
                            added.append((box, class_id, 0.2))
                    continue
                box, class_id, _confidence, part_index = found
                anchor = self._vote_anchor(label, person_box, parts, box)
                if anchor is None:
                    anchor = self._facial_anchor(person_box, parts)
                if not self._push_vote(tid, label, True, box, anchor, class_id, now):
                    drop.add(part_index)
        if parts is not None and parts.class_id is not None:
            for part_index, class_id in enumerate(parts.class_id):
                if self._class_label(int(class_id)) in VOTED_PPE_LABELS and part_index not in owned_by:
                    drop.add(part_index)
            if drop:
                keep = [index for index in range(len(parts)) if index not in drop]
                parts = parts[keep] if keep else self._empty_detections()
        stale = [tid for tid, seen in self._vote_at.items() if now - seen > 8.0]
        for tid in stale:
            self._vote_at.pop(tid, None)
            for key in [key for key in self._ppe_votes if key[0] == tid]:
                self._ppe_votes.pop(key, None)
                self._ppe_memory.pop(key, None)
        return self._append_detections(parts, added)

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

    def _phone_weights(self, kind: str) -> Path | None:
        name = "yolov8n-coco.pt" if kind == "n" else "yolov8s.pt"
        path = self.config.weights_path.with_name(name)
        return path if path.is_file() else None

    def _load_phone_model(self, kind: str) -> bool:
        if kind in self._phone_models:
            return True
        if kind in self._phone_missing:
            return False
        weights = self._phone_weights(kind)
        if weights is None:
            self._phone_missing.add(kind)
            return False
        try:
            if self._backend == "coreml" or coreml_requested():
                package = _ensure_coreml_package(weights, imgsz=320)
                model = _import_yolo()(str(package))
                self._warm_predict(model, "coreml", 320)
                self._phone_models[kind] = model
                self._phone_backends[kind] = "coreml"
                return True
        except Exception as exc:  # noqa: BLE001
            print(f"CoreML do celular indisponível ({exc}); usando PyTorch.", file=sys.stderr, flush=True)
        try:
            model = _import_yolo()(str(weights))
            device = self._device if self._device in {"cpu", "mps", "cuda"} else "cpu"
            model.to(device)
            self._warm_predict(model, "pytorch", 320)
            self._phone_models[kind] = model
            self._phone_backends[kind] = "pytorch"
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"Detector de celular indisponível ({exc}).", file=sys.stderr, flush=True)
            self._phone_missing.add(kind)
            return False

    def _phone_boxes(self, crop: np.ndarray, kind: str, confidence: float) -> list[np.ndarray]:
        if not self._load_phone_model(kind):
            return []
        model = self._phone_models[kind]
        if self._phone_backends.get(kind) == "coreml":
            result = model(crop, verbose=False, conf=confidence, imgsz=320)[0]
        else:
            device = self._device if self._device in {"cpu", "mps", "cuda"} else "cpu"
            result = model(crop, verbose=False, conf=confidence, imgsz=320, device=device)[0]
        if result.boxes is None or len(result.boxes) == 0:
            return []
        names = getattr(model, "names", {}) or {}
        found: list[np.ndarray] = []
        for box, class_id in zip(result.boxes.xyxy.cpu().numpy(), result.boxes.cls.cpu().numpy()):
            label = str(names.get(int(class_id), class_id)).lower().replace(" ", "")
            if label in {"cellphone", "mobilephone"} or int(class_id) == 67:
                found.append(np.array(box, dtype=np.float32))
        return found

    def _body_boxes(self, person_box: np.ndarray, parts, labels: set[str]) -> list[np.ndarray]:
        found: list[np.ndarray] = []
        if parts is None or parts.class_id is None:
            return found
        for index, class_id in enumerate(parts.class_id):
            if self._class_label(int(class_id)) not in labels:
                continue
            box = parts.xyxy[index]
            if self._center_inside(box, person_box):
                found.append(box)
        return found

    def _watch_phone(self, frame: np.ndarray, people, parts) -> None:
        """O celular não entra no quadro. A sonda assíncrona está em _phone_probe_job, sem o v8s."""
        return
        self._phone_crop = None
        now = time.time()
        self._phone_candidates = {
            tracker_id: until
            for tracker_id, until in self._phone_candidates.items()
            if until > now
        }
        if not self._smartphone.get("enabled"):
            return
        if people.tracker_id is None or len(people) == 0:
            return
        indexes = [index for index, tracker_id in enumerate(people.tracker_id) if tracker_id is not None]
        if not indexes or now - self._phone_at < 0.5:
            return
        self._phone_at = now
        index = indexes[self._phone_cursor % len(indexes)]
        self._phone_cursor += 1
        tracker_id = int(people.tracker_id[index])
        person_box = people.xyxy[index]
        found = False
        if self._scan_phone(frame, person_box, parts, "n", 0.20) is not None:
            confirmed = self._scan_phone(frame, person_box, parts, "s", 0.25)
            if confirmed is not None:
                found = True
                self._phone_candidates[tracker_id] = now + 0.6
                self._remember_phone(tracker_id, confirmed, parts, person_box, now)
        votes = self._phone_votes.setdefault(tracker_id, deque(maxlen=VOTE_WINDOW))
        votes.append(found)

    def _scan_phone(self, frame: np.ndarray, person_box: np.ndarray, parts, kind: str, confidence: float) -> np.ndarray | None:
        height, width = frame.shape[:2]
        x1 = max(0, int(person_box[0]))
        y1 = max(0, int(person_box[1]))
        x2 = min(width, int(person_box[2]))
        y2 = min(height, int(person_box[3]))
        if x2 - x1 < 12 or y2 - y1 < 12:
            return None
        crop = frame[y1:y2, x1:x2]
        resized = cv2.resize(crop, (320, 320), interpolation=cv2.INTER_LINEAR)
        scale_x = (x2 - x1) / 320
        scale_y = (y2 - y1) / 320
        hands = self._body_boxes(person_box, parts, {"hand"})
        faces = self._body_boxes(person_box, parts, {"face"})
        heads = self._body_boxes(person_box, parts, {"head"})
        for box in self._phone_boxes(resized, kind, confidence):
            mapped = np.array([
                x1 + float(box[0]) * scale_x,
                y1 + float(box[1]) * scale_y,
                x1 + float(box[2]) * scale_x,
                y1 + float(box[3]) * scale_y,
            ], dtype=np.float32)
            if phone_near_body(mapped, hands, faces, heads) is None:
                continue
            return mapped
        return None

    def _remember_phone(self, tracker_id: int, box: np.ndarray, parts, person_box: np.ndarray, now: float) -> None:
        hands = self._body_boxes(person_box, parts, {"hand"})
        faces = self._body_boxes(person_box, parts, {"face"})
        heads = self._body_boxes(person_box, parts, {"head"})
        where = phone_near_body(box, hands, faces, heads) or "hand"
        self._phone_seen[tracker_id] = now
        self._phone_where = where
        self._phone_holder = tracker_id
        self._phone_centers[tracker_id] = ((float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2)

    def _ask_phone_use(self, frame: np.ndarray, people) -> None:
        if not self.config.jev_url or getattr(self, "_phone_ask_inflight", False):
            return
        holder = getattr(self, "_phone_holder", None)
        if holder is None or time.time() - self._phone_seen.get(int(holder), 0.0) > 1.0:
            return
        if time.time() - getattr(self, "_phone_asked_at", 0.0) < 1.5:
            return
        person_box = None
        for index, tracker_id in enumerate(people.tracker_id):
            if tracker_id is not None and int(tracker_id) == int(holder):
                person_box = people.xyxy[index]
                break
        if person_box is None:
            return
        height, width = frame.shape[:2]
        x1 = max(0, int(person_box[0]))
        y1 = max(0, int(person_box[1]))
        x2 = min(width, int(person_box[2]))
        y2 = min(height, int(person_box[3]))
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return
        preview = cv2.resize(crop, (320, 320), interpolation=cv2.INTER_AREA)
        ok, encoded = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not ok:
            return
        payload = {
            "question": "smartphone_in_use",
            "tracker_id": int(holder),
            "phone_near": getattr(self, "_phone_where", "hand"),
            "use_modes": ["handling", "looking", "at_ear"],
            "crop_jpeg_base64": base64.b64encode(encoded.tobytes()).decode("ascii"),
        }
        self._phone_ask_inflight = True
        self._phone_asked_at = time.time()
        threading.Thread(
            target=self._phone_use_background,
            args=(int(holder), payload),
            name="snitch-phone",
            daemon=True,
        ).start()

    def _phone_use_background(self, tracker_id: int, payload: dict[str, Any]) -> None:
        started = time.perf_counter()
        try:
            url = self.config.jev_url.rstrip("/") + "/ask"
            request = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                raw = response.read()
                body = json.loads(raw.decode())
            decision = body.get("answer") if isinstance(body, dict) else None
            jev_metrics.record(
                endpoint="/ask",
                trigger="smartphone_in_use",
                payload_bytes=len(request.data or b""),
                latency_ms=(time.perf_counter() - started) * 1000,
                status=str(getattr(response, "status", 200)),
                decision=json.dumps(decision, ensure_ascii=False),
            )
            self._phone_use[tracker_id] = decision is True
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            jev_metrics.record(
                endpoint="/ask",
                trigger="smartphone_in_use",
                payload_bytes=len(json.dumps(payload).encode()),
                latency_ms=(time.perf_counter() - started) * 1000,
                status="timeout" if isinstance(exc, TimeoutError) else "error",
                decision=None,
            )
            return
        finally:
            self._phone_ask_inflight = False

    def _draw_phone(self, frame: np.ndarray) -> np.ndarray:
        labels = [
            (
                f"Uso de smartphone: {int(track['elapsed_s'])}s / {int(track['limit_s'])}s",
                16,
                16 + index * 28,
                (255, 255, 255),
            )
            for index, track in enumerate(self._phone_tracks)
            if int(track.get("limit_s") or 0) > 0
        ]
        return draw_unicode_labels(frame, labels)

    def _load_pose_model(self) -> bool:
        if self._pose_model is not None:
            return True
        if self._pose_unavailable:
            return False
        weights = self.config.weights_path.with_name("yolov8n-pose.pt")
        if not weights.is_file():
            self._pose_unavailable = True
            return False
        try:
            if self._backend == "coreml" or coreml_requested():
                package = _ensure_coreml_package(weights, imgsz=160)
                self._pose_model = _import_yolo()(str(package))
                self._pose_backend = "coreml"
                self._warm_predict(self._pose_model, "coreml", 160)
                return True
        except Exception as exc:  # noqa: BLE001
            print(f"CoreML da pose indisponível ({exc}); usando PyTorch.", file=sys.stderr, flush=True)
        try:
            self._pose_model = _import_yolo()(str(weights))
            device = self._device if self._device in {"cpu", "mps", "cuda"} else "cpu"
            self._pose_model.to(device)
            self._pose_backend = "pytorch"
            self._warm_predict(self._pose_model, "pytorch", 160)
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"Pose indisponível ({exc}).", file=sys.stderr, flush=True)
            self._pose_unavailable = True
            return False

    def _warm_predict(self, model: Any, backend: str, imgsz: int) -> None:
        blank = np.zeros((imgsz, imgsz, 3), dtype=np.uint8)
        if backend == "coreml":
            model(blank, verbose=False, conf=0.25, imgsz=imgsz)
            return
        device = self._device if self._device in {"cpu", "mps", "cuda"} else "cpu"
        model(blank, verbose=False, conf=0.25, imgsz=imgsz, device=device)

    def _pose_wanted(self, tracker_id: int, person_box: np.ndarray, parts) -> bool:
        now = time.time()
        phone = tracker_id in self._phone_candidates
        if now - self._pose_clock < (0.25 if phone else 1.0):
            return False
        if phone:
            return True
        if self._head_height(person_box, parts) < 110:
            return False
        part_for = {
            "helmet": "head",
            "goggles": "face",
            "mask": "face",
            "ear_protection": "ear",
            "gloves": "hand",
        }
        for label in self.config.required_ppe:
            part = part_for.get(label)
            if part and not self._body_boxes(person_box, parts, {part}):
                return True
        return False

    def _poses(self, frame: np.ndarray, people, parts) -> dict[int, dict[str, Any]]:
        if people.tracker_id is None or len(people) == 0:
            return {}
        wanted = [
            index
            for index, tracker_id in enumerate(people.tracker_id)
            if tracker_id is not None and self._pose_wanted(int(tracker_id), people.xyxy[index], parts)
        ]
        if not wanted or not self._load_pose_model():
            return {}
        assert self._pose_model is not None
        height, width = frame.shape[:2]
        found: dict[int, dict[str, Any]] = {}
        for index in wanted:
            tracker_id = people.tracker_id[index]
            if tracker_id is None:
                continue
            self._pose_clock = time.time()
            self._pose_at[int(tracker_id)] = self._pose_clock
            box = people.xyxy[index]
            x1 = max(0, int(box[0]))
            y1 = max(0, int(box[1]))
            x2 = min(width, int(box[2]))
            y2 = min(height, int(box[3]))
            if x2 - x1 < 12 or y2 - y1 < 12:
                continue
            crop = frame[y1:y2, x1:x2]
            if self._pose_backend == "coreml":
                result = self._pose_model(crop, verbose=False, conf=0.25, imgsz=160)[0]
            else:
                device = self._device if self._device in {"cpu", "mps", "cuda"} else "cpu"
                result = self._pose_model(crop, verbose=False, conf=0.25, imgsz=160, device=device)[0]
            if result.keypoints is None or result.boxes is None or len(result.boxes) == 0:
                continue
            boxes = result.boxes.xyxy.cpu().numpy()
            areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
            best = int(np.argmax(areas))
            xy = result.keypoints.xy.cpu().numpy()[best].copy()
            xy[:, 0] += x1
            xy[:, 1] += y1
            conf = result.keypoints.conf
            scores = None if conf is None else conf.cpu().numpy()[best]
            described = describe_pose(xy, scores)
            described["ran"] = True
            found[int(tracker_id)] = described
        return found

    def _head_height(self, person_box: np.ndarray, parts) -> float:
        heads = self._body_boxes(person_box, parts, {"head"})
        if heads:
            return max(float(box[3]) - float(box[1]) for box in heads)
        return 0.35 * max(float(person_box[3]) - float(person_box[1]), 1.0)

    def _item_facts(self, tracker_id: int, label: str, person_box: np.ndarray, parts, pose: dict[str, Any]) -> dict[str, Any]:
        present = False
        conf = 0.0
        on_part = False
        if parts is not None and parts.class_id is not None:
            for index, class_id in enumerate(parts.class_id):
                if self._class_label(int(class_id)) != label:
                    continue
                box = parts.xyxy[index]
                if not self._center_inside(box, person_box):
                    continue
                present = True
                score = float(parts.confidence[index]) if parts.confidence is not None else 0.0
                conf = max(conf, score)
                part = {"helmet": "head", "goggles": "face", "ear_protection": "ear", "gloves": "hand", "mask": "face", "boots": "foot"}.get(label)
                anchors = self._body_boxes(person_box, parts, {part}) if part else []
                on_part = on_part or any(self._center_inside(box, anchor) for anchor in anchors) or part in {None, "torso"}
        votes = self._fact_votes.setdefault((tracker_id, label), deque(maxlen=VOTE_WINDOW))
        votes.append(present and (on_part or label in {"vest", "harness"}))
        part_name = {"helmet": "head", "goggles": "face", "ear_protection": "ear", "earplug": "ear", "gloves": "hand", "mask": "face", "boots": "foot"}.get(label, "torso")
        box_name = {"head": "head", "face": "face", "ear": "ear", "hand": "hand"}.get(part_name)
        if part_name in {"torso", "foot"}:
            part_visible = True
        elif box_name and self._body_boxes(person_box, parts, {box_name}):
            part_visible = True
        elif pose.get("ran"):
            part_visible = {
                "head": not pose.get("occluded", True),
                "face": bool(pose.get("face_visible")),
                "ear": bool(pose.get("ear_visible")),
                "hand": bool(pose.get("hand_visible")),
            }.get(part_name, False)
        else:
            part_visible = False
        return {
            "conf": round(conf, 3),
            "on_part": on_part or label in {"vest", "harness"},
            "part_visible": part_visible,
            "votes_present": sum(1 for seen in votes if seen),
            "votes_window": len(votes),
            "zoom": self._zoom_status.get(tracker_id, "not_run") if label == "goggles" else "not_run",
            "detector": label != "earplug",
        }

    def _phone_facts(self, tracker_id: int, pose: dict[str, Any], head_height: float) -> dict[str, Any]:
        votes = self._phone_votes.get(tracker_id, ())
        center = self._phone_centers.get(tracker_id)
        previous = getattr(self, "_phone_previous", {}).get(tracker_id)
        motion = 0.0 if center is None or previous is None else float(np.hypot(center[0] - previous[0], center[1] - previous[1]))
        if not hasattr(self, "_phone_previous"):
            self._phone_previous = {}
        if center is not None:
            self._phone_previous[tracker_id] = center
        return {
            "votes_present": sum(1 for seen in votes if seen),
            "votes_window": len(votes) or 1,
            "dist_wrist_px": nearest(center, pose.get("wrists") or []),
            "dist_face_px": nearest(center, [pose["nose"]] if pose.get("nose") else []),
            "dist_ear_px": nearest(center, pose.get("ears") or []),
            "face_toward_phone": face_toward_phone(pose, center, head_height),
            "motion_px": round(motion, 1),
        }

    def _perceive(self, frame: np.ndarray, people, parts) -> None:
        self._verdict = {"persons": []}
        if people.tracker_id is None or len(people) == 0:
            self._facts = {"persons": []}
            return
        poses: dict[int, dict[str, Any]] = {}
        persons = []
        limit = self._smartphone.get("hand_limit_seconds")
        try:
            limit_s = int(limit) if limit else None
        except (TypeError, ValueError):
            limit_s = None
        now = time.time()
        for index, tracker_id in enumerate(people.tracker_id):
            if tracker_id is None:
                continue
            tid = int(tracker_id)
            person_box = people.xyxy[index]
            pose = poses.get(tid) or {
                "ran": False,
                "occluded": False,
                "yaw": "unknown",
                "face_visible": False,
                "ear_visible": False,
                "hand_visible": False,
                "wrists": [],
                "ears": [],
                "nose": None,
                "eyes": [],
            }
            head_height = self._head_height(person_box, parts)
            items = {
                label: self._item_facts(tid, label, person_box, parts, pose)
                for label in self.config.required_ppe
            }
            if "earplug" in items:
                items["earplug"]["detector"] = False
            persons.append({
                "tracker_id": tid,
                "head_height_px": round(head_height, 1),
                "head_occluded": bool(pose.get("ran") and pose.get("occluded")),
                "head_yaw": pose.get("yaw", "unknown"),
                "items": items,
                "phone": self._phone_facts(tid, pose, head_height) if self._smartphone.get("enabled") else {"votes_present": 0, "votes_window": 1},
            })
        facts = {"persons": persons}
        local = judge_facts(facts)
        signature = json.dumps(facts, sort_keys=True)
        verdict = local
        if self._remote_sig == signature and self._remote_verdict is not None:
            verdict = self._remote_verdict
        self._facts = facts
        self._facts_signature = signature
        self._verdict = verdict
        self._schedule_judge(facts, signature)
        sightings: list[PhoneSighting] = []
        if self._smartphone.get("enabled"):
            for person in persons:
                saved = self._image_answer(int(person["tracker_id"]), "phone")
                if not saved or saved.get("status") != "uso":
                    continue
                box = people.xyxy[list(people.tracker_id).index(person["tracker_id"])]
                center = ((float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2)
                sightings.append(PhoneSighting(person["tracker_id"], center, True, True))
        self._phone_tracks = self._phone_clock.update(sightings, now, limit_s) if self._smartphone.get("enabled") else []

    def _schedule_judge(self, facts: dict[str, Any], signature: str) -> None:
        if not self.config.jev_url or not facts.get("persons"):
            return
        now = time.time()
        if signature == self._facts_sig and (self._judge_ok or now - self._judge_at < 3):
            return
        self._facts_sig = signature
        self._judge_at = now
        threading.Thread(target=self._judge_background, args=(facts, signature), name="snitch-judge", daemon=True).start()

    def _judge_background(self, facts: dict[str, Any], signature: str) -> None:
        started = time.perf_counter()
        payload = json.dumps(facts).encode()
        try:
            request = urllib.request.Request(
                self.config.jev_url.rstrip("/") + "/judge",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=2.5) as response:
                body = json.loads(response.read().decode())
            jev_metrics.record(
                endpoint="/judge",
                trigger="fatos",
                payload_bytes=len(payload),
                latency_ms=(time.perf_counter() - started) * 1000,
                status=str(getattr(response, "status", 200)),
                decision="ok",
            )
            if isinstance(body, dict) and isinstance(body.get("persons"), list):
                self._remote_verdict = body
                self._remote_sig = signature
                self._judge_ok = True
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            self._judge_ok = False
            jev_metrics.record(
                endpoint="/judge",
                trigger="fatos",
                payload_bytes=len(payload),
                latency_ms=(time.perf_counter() - started) * 1000,
                status="timeout" if isinstance(exc, TimeoutError) else "error",
                decision=None,
            )

    def _log_image(self, tracker_id: int, role: str, action: str, detail: str) -> None:
        print(
            f"JEV imagem tracker={tracker_id} papel={role} acao={action} {detail}",
            file=sys.stderr,
            flush=True,
        )

    def _log_image_once(self, book: dict[str, Any], key: str, tracker_id: int, action: str, detail: str) -> None:
        token = f"{action}:{detail}"
        if book.setdefault("logged", {}).get(key) == token:
            return
        book["logged"][key] = token
        self._log_image(tracker_id, key, action, detail)

    def _image_book(self, tracker_id: int, now: float) -> dict[str, Any]:
        book = self._image_books.get(tracker_id)
        if book is not None and now - float(book["seen"]) > 3.0:
            self._log_image(tracker_id, "track", "reset", "motivo=pessoa_sumiu")
            book = None
        if book is None:
            book = {
                "born": now,
                "seen": now,
                "since": {},
                "answers": {},
                "failed": {},
                "pending": set(),
                "logged": {},
                "phone_probe": None,
            }
            self._image_books[tracker_id] = book
        else:
            book["seen"] = now
        return book

    def _image_answer(self, tracker_id: int, name: str) -> dict[str, Any] | None:
        with self._image_lock:
            book = self._image_books.get(tracker_id)
            if not book:
                return None
            saved = book["answers"].get(name)
            return dict(saved) if saved else None

    def _answer_blocks(self, saved: dict[str, Any] | None, now: float, local_status: str) -> bool:
        if not saved:
            return False
        age = now - float(saved["at"])
        if saved["status"] in {"sem", "uso"} and local_status in {"sem", "indeterminado", "uso"} and age >= IMAGE_REQUALIFY_SECONDS:
            return False
        return True

    def _overlay_image_answers(self, state: dict[str, Any]) -> None:
        facts = {
            int(person["tracker_id"]): person
            for person in (getattr(self, "_facts", None) or {}).get("persons") or []
            if person.get("tracker_id") is not None
        }
        now = time.time()
        with self._image_lock:
            for person in state.get("persons") or []:
                if person.get("tracker_id") is None or "ppe_judge" not in person:
                    continue
                tid = int(person["tracker_id"])
                book = self._image_books.get(tid) or {}
                fact_items = (facts.get(tid) or {}).get("items") or {}
                judged = person["ppe_judge"]
                missing: list[str] = []
                for name, verdict in list(judged.items()):
                    local = str(verdict.get("status") or "")
                    fact = fact_items.get(name) or {}
                    detected = int(fact.get("votes_present") or 0) > 0
                    reason = needs_image_review(name, local, float(fact.get("conf") or 0), detected)
                    saved = book.get("answers", {}).get(name)
                    failed = name in book.get("failed", {})
                    if saved and self._answer_blocks(saved, now, local):
                        status = "sem" if saved["status"] == "sem" else "com"
                        judged[name] = {**verdict, "status": status, "rule": "jev_imagem"}
                    elif reason and not failed and local == "sem":
                        judged[name] = {**verdict, "status": "indeterminado", "rule": "aguardando_jev"}
                    if judged[name].get("status") == "sem":
                        missing.append(name)
                person["ppe_missing"] = missing
                person["ppe_judge"] = judged

    def _store_image_answers(self, tracker_id: int, questions: dict[str, str], result: dict[str, Any]) -> None:
        answers = result.get("answers") if isinstance(result.get("answers"), dict) else {}
        now = time.time()
        with self._image_lock:
            book = self._image_books.get(tracker_id)
            if not book:
                return
            for name in questions:
                flag = noul_is_true(answers.get(name))
                if flag is None:
                    book["failed"][name] = now
                    continue
                status = ("uso" if flag else "nao_uso") if name == "phone" else ("com" if flag else "sem")
                book["answers"][name] = {"status": status, "at": now}
                book["failed"].pop(name, None)

    def _mark_image_failed(self, tracker_id: int, questions: dict[str, str]) -> None:
        now = time.time()
        with self._image_lock:
            book = self._image_books.get(tracker_id)
            if not book:
                return
            for name in questions:
                book["failed"][name] = now

    def _crop_origin(self, frame: np.ndarray, box: np.ndarray, pad_ratio: float) -> tuple[np.ndarray, int, int]:
        height, width = frame.shape[:2]
        x1, y1, x2, y2 = (float(value) for value in box)
        pad_x = (x2 - x1) * pad_ratio
        pad_y = (y2 - y1) * pad_ratio
        left = max(0, int(x1 - pad_x))
        top = max(0, int(y1 - pad_y))
        right = min(width, int(x2 + pad_x))
        bottom = min(height, int(y2 + pad_y))
        if right - left < 8 or bottom - top < 8:
            return frame.copy(), 0, 0
        return frame[top:bottom, left:right].copy(), left, top

    def _shift_boxes(self, boxes: list[np.ndarray], left: int, top: int) -> list[np.ndarray]:
        shifted = []
        for box in boxes:
            shifted.append(np.array([
                float(box[0]) - left,
                float(box[1]) - top,
                float(box[2]) - left,
                float(box[3]) - top,
            ], dtype=np.float32))
        return shifted

    def _pose_on_crop(self, crop: np.ndarray) -> dict[str, Any]:
        if crop.size == 0 or not self._load_pose_model():
            return {}
        assert self._pose_model is not None
        if self._pose_backend == "coreml":
            result = self._pose_model(crop, verbose=False, conf=0.25, imgsz=160)[0]
        else:
            device = self._device if self._device in {"cpu", "mps", "cuda"} else "cpu"
            result = self._pose_model(crop, verbose=False, conf=0.25, imgsz=160, device=device)[0]
        if result.keypoints is None or result.boxes is None or len(result.boxes) == 0:
            return {}
        boxes = result.boxes.xyxy.cpu().numpy()
        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        best = int(np.argmax(areas))
        conf = result.keypoints.conf
        scores = None if conf is None else conf.cpu().numpy()[best]
        described = describe_pose(result.keypoints.xy.cpu().numpy()[best], scores)
        described["ran"] = True
        return described

    def _nano_on_crop(self, crop: np.ndarray, hands: list[np.ndarray], faces: list[np.ndarray], heads: list[np.ndarray]) -> bool:
        if crop.size == 0 or not self._load_phone_model("n"):
            return False
        resized = cv2.resize(crop, (320, 320), interpolation=cv2.INTER_LINEAR)
        scale_x = crop.shape[1] / 320
        scale_y = crop.shape[0] / 320
        for box in self._phone_boxes(resized, "n", NANO_PHONE_CONF):
            mapped = np.array([
                float(box[0]) * scale_x,
                float(box[1]) * scale_y,
                float(box[2]) * scale_x,
                float(box[3]) * scale_y,
            ], dtype=np.float32)
            if phone_near_body(mapped, hands, faces, heads) is not None:
                return True
        return False

    def _schedule_image_review(self, frame: np.ndarray, people, parts) -> None:
        if people.tracker_id is None or len(people) == 0:
            return
        now = time.time()
        verdicts = {
            int(person["tracker_id"]): person
            for person in (self._verdict or {}).get("persons") or []
            if person.get("tracker_id") is not None
        }
        facts = {
            int(person["tracker_id"]): person
            for person in (self._facts or {}).get("persons") or []
            if person.get("tracker_id") is not None
        }
        for index, tracker_id in enumerate(people.tracker_id):
            if tracker_id is None:
                continue
            tid = int(tracker_id)
            with self._image_lock:
                book = self._image_book(tid, now)
                judged = (verdicts.get(tid) or {}).get("ppe") or {}
                fact_items = (facts.get(tid) or {}).get("items") or {}
                head_questions: dict[str, str] = {}
                body_questions: dict[str, str] = {}
                for name in self.config.required_ppe:
                    verdict = judged.get(name) or {}
                    local = str(verdict.get("status") or "")
                    fact = fact_items.get(name) or {}
                    detected = int(fact.get("votes_present") or 0) > 0
                    reason = needs_image_review(name, local, float(fact.get("conf") or 0), detected)
                    if reason is None:
                        book["since"].pop(name, None)
                        if name in HEAD_REVIEW or name in BODY_REVIEW:
                            self._log_image_once(book, name, tid, "pulado", "motivo=marco_com")
                        continue
                    saved = book["answers"].get(name)
                    if name in book["failed"]:
                        self._log_image_once(book, name, tid, "pulado", "motivo=falha_anterior_usa_marco")
                        continue
                    if self._answer_blocks(saved, now, local):
                        self._log_image_once(book, name, tid, "pulado", "motivo=resposta_no_track")
                        continue
                    if saved and not self._answer_blocks(saved, now, local):
                        book["answers"].pop(name, None)
                        self._log_image(tid, name, "reconsulta", "motivo=dez_minutos")
                    if reason == "sempre":
                        ready = review_is_due(book["born"], now)
                    else:
                        book["since"].setdefault(name, now)
                        ready = review_is_due(book["since"].get(name), now)
                    if not ready:
                        self._log_image_once(book, name, tid, "pulado", "motivo=aguardando_persistencia")
                        continue
                    question = IMAGE_QUESTIONS.get(name)
                    if not question:
                        continue
                    if name in HEAD_REVIEW:
                        head_questions[name] = question
                    elif name in BODY_REVIEW:
                        body_questions[name] = question
                phone_due = False
                if self._smartphone.get("enabled") and "celular" not in book["pending"]:
                    saved_phone = book["answers"].get("phone")
                    if "phone" in book["failed"]:
                        self._log_image_once(book, "phone", tid, "pulado", "motivo=falha_anterior")
                    elif self._answer_blocks(saved_phone, now, "uso" if saved_phone and saved_phone.get("status") == "uso" else "nao_uso"):
                        self._log_image_once(book, "phone", tid, "pulado", "motivo=resposta_no_track")
                    elif review_is_due(book["born"], now) and (
                        book["phone_probe"] is None or review_is_due(book["phone_probe"], now)
                    ):
                        phone_due = True
                        book["phone_probe"] = now
                        book["pending"].add("celular")
                person_box = people.xyxy[index].copy()
                head_boxes = self._body_boxes(person_box, parts, {"head"})
                head_box = max(head_boxes, key=lambda box: float(box[3] - box[1])) if head_boxes else None
                if head_questions and "cabeca" not in book["pending"] and head_box is not None:
                    book["pending"].add("cabeca")
                    head_crop = crop_box(frame, head_box, 0.5).copy()
                    self._log_image(tid, "cabeca", "agendado", "motivo=" + ",".join(f"{name}:pedido" for name in head_questions))
                else:
                    head_crop = None
                    if head_questions and head_box is None:
                        self._log_image_once(book, "cabeca", tid, "pulado", "motivo=sem_cabeca")
                if body_questions and "corpo" not in book["pending"]:
                    book["pending"].add("corpo")
                    body_crop = crop_box(frame, person_box, 0.08).copy()
                    self._log_image(tid, "corpo", "agendado", "motivo=" + ",".join(body_questions))
                else:
                    body_crop = None
                if phone_due:
                    phone_crop, left, top = self._crop_origin(frame, person_box, 0.08)
                    hands = self._shift_boxes(self._body_boxes(person_box, parts, {"hand"}), left, top)
                    faces = self._shift_boxes(self._body_boxes(person_box, parts, {"face"}), left, top)
                    heads = self._shift_boxes(self._body_boxes(person_box, parts, {"head"}), left, top)
                    head_height = self._head_height(person_box, parts)
                    self._log_image(tid, "celular", "sonda", "motivo=nano_ou_pose")
                else:
                    phone_crop = None
                    hands = faces = heads = []
                    head_height = 0.0
            if head_crop is not None and head_questions:
                threading.Thread(
                    target=self._image_job,
                    args=(tid, "cabeca", head_crop, dict(head_questions)),
                    name="snitch-jev-cabeca",
                    daemon=True,
                ).start()
            if body_crop is not None and body_questions:
                threading.Thread(
                    target=self._image_job,
                    args=(tid, "corpo", body_crop, dict(body_questions)),
                    name="snitch-jev-corpo",
                    daemon=True,
                ).start()
            if phone_crop is not None:
                threading.Thread(
                    target=self._phone_probe_job,
                    args=(tid, phone_crop, hands, faces, heads, head_height),
                    name="snitch-jev-celular",
                    daemon=True,
                ).start()

    def _image_job(self, tracker_id: int, role: str, crop: np.ndarray, questions: dict[str, str]) -> None:
        try:
            result = ask_image(encode_jpeg(crop), questions, trigger=role)
            sha = str(result.get("sha256") or "")[:8]
            resumo = ",".join(result.get("resumo") or [])
            if result.get("status") == 200 and resumo:
                self._store_image_answers(tracker_id, questions, result)
                action = "cache" if result.get("cache") else "enviado"
                self._log_image(
                    tracker_id,
                    role,
                    action,
                    f"sha={sha} resultado={resumo} enviadas={result.get('enviadas')} usd={result.get('usd')}",
                )
            else:
                self._mark_image_failed(tracker_id, questions)
                motivo = "sem_chave" if result.get("status") == 401 else f"status={result.get('status')}"
                self._log_image(tracker_id, role, "falhou", f"motivo={motivo}")
        except Exception as exc:  # noqa: BLE001
            self._mark_image_failed(tracker_id, questions)
            self._log_image(tracker_id, role, "falhou", f"motivo={exc.__class__.__name__}")
        finally:
            with self._image_lock:
                book = self._image_books.get(tracker_id)
                if book:
                    book["pending"].discard(role)

    def _phone_probe_job(
        self,
        tracker_id: int,
        crop: np.ndarray,
        hands: list[np.ndarray],
        faces: list[np.ndarray],
        heads: list[np.ndarray],
        head_height: float,
    ) -> None:
        try:
            pose = self._pose_on_crop(crop)
            triggered = self._nano_on_crop(crop, hands, faces, heads) or phone_pose_trigger(pose, head_height)
            if not triggered:
                self._log_image(tracker_id, "celular", "pulado", "motivo=sem_gatilho")
                return
            self._image_job(tracker_id, "celular", crop, {"phone": IMAGE_QUESTIONS["phone"]})
        finally:
            with self._image_lock:
                book = self._image_books.get(tracker_id)
                if book:
                    book["pending"].discard("celular")

    def _apply_verdict(self, state: dict[str, Any]) -> None:
        verdict = self._verdict if isinstance(getattr(self, "_verdict", None), dict) else {"persons": []}
        by_id = {
            int(person["tracker_id"]): person
            for person in verdict.get("persons") or []
            if person.get("tracker_id") is not None
        }
        for person in state.get("persons") or []:
            judged = by_id.get(int(person.get("tracker_id")))
            if not judged:
                continue
            person["ppe_missing"] = [
                name for name, item in (judged.get("ppe") or {}).items() if item.get("status") == "sem"
            ]
            person["ppe_judge"] = judged.get("ppe") or {}
        self._overlay_image_answers(state)
        state["judge"] = verdict

    def process_frame(self, frame: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        detect_started = time.perf_counter()
        people, parts = self._track_people_only(self._run_yolo(frame))
        if not self.config.mock:
            parts = self._refine_facial_ppe(frame, people, parts)
            self._perceive(frame, people, parts)
        detect_elapsed = time.perf_counter() - detect_started
        self._inference_fps = round(1.0 / detect_elapsed, 1) if detect_elapsed > 0 else 0.0
        if not self.config.mock:
            self._schedule_image_review(frame, people, parts)
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
            self._apply_verdict(state)
        phone_state = dict(self._smartphone)
        phone_state["tracks"] = list(self._phone_tracks)
        state["smartphone"] = phone_state
        state["dwell_exceeded"] = dwell_exceeded
        state["zone_dwell"] = zone_dwell
        self._attach_missing_ppe(state)
        self._attach_jev(state, persons)
        missing_labels = {
            int(person["tracker_id"]): list(person.get("missing_ppe_labels_pt") or [])
            for person in state["persons"]
            if person.get("missing_ppe_labels_pt")
        }
        annotated = self._annotate(frame, people, missing_labels)
        if len(parts):
            annotated = self._annotate(annotated, parts)
        annotated = self._draw_zones(annotated, zone_dwell)
        annotated = self._draw_phone(annotated)
        telemetry = dict(state.get("telemetry") or {})
        telemetry["inference_fps"] = self._inference_fps
        state["telemetry"] = telemetry
        if persons and not self.config.mock:
            self._maybe_record_episode(annotated, state)
        self._frame_index += 1
        return annotated, state

    def _attach_jev(self, state: dict[str, Any], persons: list[TrackedPerson]) -> None:
        with self._jev_lock:
            if self._last_jev_error:
                state["jev_error"] = self._last_jev_error
        with self._jev_lock:
            state["telemetry"] = {
                "frame_index": self._frame_index,
                "jev_updated_at": self._last_jev_ts,
                "jev_latency_ms": self._last_jev_latency_ms,
                "laya_engine": self._laya_engine,
                "inference_fps": self._inference_fps,
                **jev_metrics.snapshot(),
            }

    def _schedule_jev(self, state: dict[str, Any], persons: list[TrackedPerson]) -> None:
        if not self.config.jev_url or not persons:
            return
        interval = float(os.environ.get("SNITCH_JEV_INTERVAL", "1.5"))
        now = time.time()
        with self._jev_lock:
            if self._jev_inflight:
                return
            if self._last_jev is not None and (now - self._last_jev_ts) < interval:
                return
            self._jev_inflight = True
        snapshot = json.loads(json.dumps(state))
        threading.Thread(
            target=self._ask_jev_background,
            args=(snapshot,),
            name="snitch-jev",
            daemon=True,
        ).start()

    def _ask_jev_background(self, snapshot: dict[str, Any]) -> None:
        try:
            self._ask_jev_now(snapshot)
        finally:
            with self._jev_lock:
                self._jev_inflight = False

    def _ask_jev_now(self, state: dict[str, Any]) -> None:
        started = time.perf_counter()
        try:
            answers = ask_jev_sync(
                self.config.jev_url,
                state,
                list(self.config.jev_questions),
            )
            latency_ms = (time.perf_counter() - started) * 1000
            engine = self._read_laya_engine()
            with self._jev_lock:
                self._last_jev = answers
                self._last_jev_error = None
                self._last_jev_ts = time.time()
                self._last_jev_latency_ms = latency_ms
                if engine:
                    self._laya_engine = engine
            state["jev"] = answers
        except Exception as exc:  # noqa: BLE001 — motor continua se Jev estiver offline
            with self._jev_lock:
                self._last_jev_error = str(exc)
            state["jev_error"] = str(exc)

    def _read_laya_engine(self) -> str | None:
        url = self.config.jev_url.rstrip("/") + "/health"
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                body = json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            jev_metrics.record(
                endpoint="/health",
                trigger="nome_do_motor",
                payload_bytes=0,
                latency_ms=(time.perf_counter() - started) * 1000,
                status="timeout" if isinstance(exc, TimeoutError) else "error",
                decision=None,
            )
            return None
        engine = body.get("engine") if isinstance(body, dict) else None
        jev_metrics.record(
            endpoint="/health",
            trigger="nome_do_motor",
            payload_bytes=0,
            latency_ms=(time.perf_counter() - started) * 1000,
            status="200",
            decision=str(engine) if engine else None,
        )
        return str(engine) if engine else None

    def _maybe_record_episode(self, annotated: np.ndarray, state: dict[str, Any]) -> None:
        web = os.environ.get("SNITCH_WEB_URL", "").rstrip("/")
        if not web:
            return
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
        for track in (state.get("smartphone") or {}).get("tracks") or []:
            if not isinstance(track, dict) or not track.get("limit_exceeded"):
                continue
            jobs.append((
                f"smartphone:{track.get('tracker_id')}",
                f"{web}/snitch/episodes/smartphone",
                {
                    "enabled": True,
                    "limit_exceeded": True,
                    "employee_id": self._employee_id_for_tracker(int(track["tracker_id"])) if track.get("tracker_id") is not None else None,
                    "location_id": location_id,
                    "camera_id": self.config.camera_id,
                    "tracker_id": track.get("tracker_id"),
                    "elapsed_seconds": track.get("elapsed_s"),
                    "hand_limit_seconds": track.get("limit_s"),
                },
            ))
        if not jobs:
            return
        photo = "data:image/jpeg;base64," + encode_frame_jpeg(annotated, quality=60)
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
            self._smartphone = {
                "enabled": bool(phone.get("enabled")),
                "hand_limit_seconds": phone.get("hand_limit_seconds"),
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
