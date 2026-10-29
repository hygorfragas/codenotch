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
import time
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

    def _annotate(self, frame: np.ndarray, detections) -> np.ndarray:
        import supervision as sv

        box_annotator = sv.BoxAnnotator(thickness=2)
        label_annotator = sv.LabelAnnotator(text_scale=0.5)
        labels = [
            SH17_CLASS_NAMES[int(cid)] if int(cid) < len(SH17_CLASS_NAMES) else str(int(cid))
            for cid in detections.class_id
        ]
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
            label = SH17_CLASS_NAMES[class_id] if class_id < len(SH17_CLASS_NAMES) else str(class_id)
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

        if self.config.jev_url and persons:
            try:
                answers = ask_jev_sync(
                    self.config.jev_url,
                    state,
                    list(self.config.jev_questions),
                )
                state["jev"] = answers
            except Exception as exc:  # noqa: BLE001 — motor continua se Jev estiver offline
                state["jev_error"] = str(exc)

        annotated = self._annotate(frame, detections)
        self._frame_index += 1
        return annotated, state

    def frames(self, source: str | int) -> Iterator[tuple[np.ndarray, dict[str, Any]]]:
        capture = cv2.VideoCapture(source)
        if not capture.isOpened():
            raise RuntimeError(f"Não foi possível abrir o fluxo: {source}")

        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                yield self.process_frame(frame)
        finally:
            capture.release()


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

        run_sse_server(config, host=args.host, port=args.port, source=source)
        return 0

    analyzer = StreamAnalyzer(config)
    for annotated, state in analyzer.frames(source):
        print(json.dumps({"frame": state["frame_index"], "jev": state.get("jev")}))
        _ = annotated
    return 0


if __name__ == "__main__":
    sys.exit(main())
