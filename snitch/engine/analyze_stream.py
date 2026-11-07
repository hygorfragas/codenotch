#!/usr/bin/env python3
"""
SNITCH — analisa fluxo RTSP/arquivo, YOLO (SH17), ByteTrack, PolygonZone,
desenha caixas e publica frames via SSE. Estado JSON vai ao Jev.
"""

from __future__ import annotations

import argparse
import base64
import json
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


def canonical_class_name(name: str) -> str:
    return CLASS_ALIASES.get(name, name)


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


def _import_supervision():
    import supervision as sv

    return sv


def _import_yolo():
    from ultralytics import YOLO

    return YOLO


@dataclass
class ZoneConfig:
    name: str
    polygon: np.ndarray  # Nx2 float


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
            device = os.environ.get("SNITCH_YOLO_DEVICE", "").strip()
            if device:
                self._model.to(device)
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
        results = self._model(frame, verbose=False)[0]
        import supervision as sv

        return sv.Detections.from_ultralytics(results)

    def _class_label(self, class_id: int) -> str:
        names = getattr(self._model, "names", None) if self._model is not None else None
        return lookup_class_name(class_id, names)

    def _box_label(self, class_id: int, tracker_id: int | None) -> str:
        label = self._class_label(class_id)
        if tracker_id is None:
            return label
        link = self._tracker_links.get(str(tracker_id))
        who = ""
        if isinstance(link, dict) and link.get("name"):
            who = f" {link['name']}"
        return f"[#{tracker_id}{who}] {label}"

    def _annotate(self, frame: np.ndarray, detections) -> np.ndarray:
        import supervision as sv

        box_annotator = sv.BoxAnnotator(thickness=2)
        label_annotator = sv.LabelAnnotator(text_scale=0.5)
        class_ids = list(detections.class_id) if detections.class_id is not None else []
        tracker_ids = list(detections.tracker_id) if detections.tracker_id is not None else []
        labels = []
        for index, class_id in enumerate(class_ids):
            tracker_id = tracker_ids[index] if index < len(tracker_ids) else None
            labels.append(self._box_label(int(class_id), None if tracker_id is None else int(tracker_id)))
        annotated = box_annotator.annotate(scene=frame.copy(), detections=detections)
        return label_annotator.annotate(scene=annotated, detections=detections, labels=labels)

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
    ) -> list[TrackedPerson]:
        persons: list[TrackedPerson] = []
        if detections.tracker_id is None:
            return persons

        by_tracker: dict[int, dict[str, Any]] = {}
        for i, tracker_id in enumerate(detections.tracker_id):
            if tracker_id is None:
                continue
            tid = int(tracker_id)
            class_id = int(detections.class_id[i]) if detections.class_id is not None else 0
            label = self._class_label(class_id)
            entry = by_tracker.setdefault(
                tid,
                {"bbox": detections.xyxy[i], "ppe": []},
            )
            if label in self.config.required_ppe or label in PPE_BODY_MAP:
                entry["ppe"].append(label)

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

    def process_frame(self, frame: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        detections = self._run_yolo(frame)
        if self.config.mock and detections.tracker_id is None:
            import supervision as sv

            detections = sv.Detections(
                xyxy=detections.xyxy,
                class_id=detections.class_id,
                confidence=detections.confidence,
                tracker_id=np.array([1] * len(detections)),
            )
        if self._tracker is not None:
            detections = self._tracker.update_with_detections(detections)

        zone_hits = self._zone_hits(detections)
        persons = self._persons_from_tracks(detections, zone_hits)
        state = build_jev_state(
            camera_id=self.config.camera_id,
            frame_index=self._frame_index,
            persons=persons,
            zones=[{"name": z.name} for z in self.config.zones],
        )

        if not self.config.mock:
            self._schedule_config()
        state["smartphone"] = dict(self._smartphone)
        self._attach_jev(state, persons)
        annotated = self._annotate(frame, detections)
        if persons and not self.config.mock:
            self._maybe_record_episode(annotated, state)
        self._frame_index += 1
        return annotated, state

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
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                body = json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            return None
        engine = body.get("engine") if isinstance(body, dict) else None
        return str(engine) if engine else None

    def _maybe_record_episode(self, annotated: np.ndarray, state: dict[str, Any]) -> None:
        web = os.environ.get("SNITCH_WEB_URL", "").rstrip("/")
        jev = state.get("jev")
        if not web or not isinstance(jev, dict):
            return
        photo = "data:image/jpeg;base64," + encode_frame_jpeg(annotated, quality=60)
        location_id = int(os.environ.get("SNITCH_LOCATION_ID", "2"))
        employee_id = self._linked_employee_id(state)
        cooldown = float(os.environ.get("SNITCH_EPISODE_COOLDOWN", "30"))
        now = time.time()
        jobs: list[tuple[str, str, dict[str, Any]]] = []
        if jev.get("any_missing_required_ppe") is True:
            jobs.append((
                "ppe",
                f"{web}/snitch/episodes/ppe",
                {
                    "employee_id": employee_id,
                    "location_id": location_id,
                    "camera_id": self.config.camera_id,
                    "required_ppe": "helmet",
                    "detected_ppe": [],
                    "photo": photo,
                },
            ))
        if jev.get("any_person_in_restricted_zone") is True:
            jobs.append((
                "zone",
                f"{web}/snitch/episodes/idle-zone",
                {
                    "employee_id": employee_id,
                    "location_id": location_id,
                    "zone": "passagem",
                    "zone_type": "passagem",
                    "max_time_seconds": 1,
                    "time_exceeded": True,
                    "photo": photo,
                },
            ))
        for key, url, payload in jobs:
            with self._episode_lock:
                if now - self._episode_at.get(key, 0.0) < cooldown:
                    continue
                self._episode_at[key] = now
            threading.Thread(
                target=_post_json,
                args=(url, payload),
                name=f"snitch-episode-{key}",
                daemon=True,
            ).start()

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
            zones.append(ZoneConfig(name=str(item.get("name") or "zona"), polygon=np.array(polygon, dtype=np.float32)))
        self.config.zones = zones
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
