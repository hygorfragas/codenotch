"""Servidor SSE mínimo — publica JPEG base64 anotado para o Laravel fazer proxy."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from typing import Any

import cv2
from aiohttp import web

from analyze_stream import (
    AnalyzeStreamConfig,
    StreamAnalyzer,
    _is_video_file,
    encode_frame_jpeg,
    load_config_from_env,
)

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "*",
}


async def health(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"}, headers=_CORS)


async def preflight(_request: web.Request) -> web.Response:
    return web.Response(status=204, headers=_CORS)


class FrameGrabber:
    """Leitura aberta na thread principal; o loop seguinte só consome o último quadro."""

    def __init__(self, source: str | int) -> None:
        self.source = source
        self.capture = cv2.VideoCapture(source)
        if not self.capture.isOpened():
            raise RuntimeError(f"Não foi possível abrir o fluxo: {source}")
        ok, frame = self.capture.read()
        if not ok or frame is None:
            self.capture.release()
            raise RuntimeError(f"Não foi possível ler o primeiro quadro: {source}")
        self.latest = frame
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="snitch-grabber", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            ok, frame = self.capture.read()
            if not ok or frame is None:
                if _is_video_file(self.source):
                    self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                time.sleep(0.05)
                continue
            self.latest = frame

    def close(self) -> None:
        self._stop.set()
        self.capture.release()


def _analyzer_for_camera(config: AnalyzeStreamConfig, camera_id: int) -> StreamAnalyzer:
    cfg = AnalyzeStreamConfig(
        camera_id=camera_id,
        weights_path=config.weights_path,
        stream_source=config.stream_source,
        jev_url=config.jev_url,
        required_ppe=config.required_ppe,
        zones=config.zones,
        mock=config.mock,
        jev_questions=config.jev_questions,
    )
    return StreamAnalyzer(cfg)


async def camera_stream(request: web.Request) -> web.StreamResponse:
    camera_id = int(request.match_info["camera"])

    response = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            **_CORS,
        },
    )
    await response.prepare(request)

    latest = request.app["latest"]
    lock: threading.Lock = request.app["latest_lock"]
    started = time.perf_counter()
    sent = 0
    try:
        while True:
            with lock:
                jpeg = latest.get("jpeg")
                state = latest.get("state")
            if not jpeg or not isinstance(state, dict):
                await asyncio.sleep(0.05)
                continue
            sent += 1
            elapsed = time.perf_counter() - started
            payload_state = json.loads(json.dumps(state))
            telemetry = dict(payload_state.get("telemetry") or {})
            telemetry["fps"] = round(sent / elapsed, 1) if elapsed >= 0.5 else 0.0
            if camera_id:
                payload_state["camera_id"] = camera_id
            payload_state["telemetry"] = telemetry
            payload = {
                "camera_id": camera_id,
                "image_jpeg_base64": jpeg,
                "state": payload_state,
            }
            await response.write(f"event: frame\ndata: {json.dumps(payload)}\n\n".encode())
            await asyncio.sleep(1 / 30)
    except (asyncio.CancelledError, ConnectionResetError, RuntimeError):
        raise

    return response


def create_app(config: AnalyzeStreamConfig | None = None, stream_source: Any = None) -> web.Application:
    app = web.Application()
    app["snitch_config"] = config or load_config_from_env()
    if stream_source is not None:
        app["stream_source"] = stream_source
    app["latest"] = {}
    app["latest_lock"] = threading.Lock()
    app.router.add_get("/health", health)
    app.router.add_route("OPTIONS", "/cameras/{camera}/stream", preflight)
    app.router.add_get("/cameras/{camera}/stream", camera_stream)
    return app


def _detect_loop(analyzer: StreamAnalyzer, grabber: FrameGrabber, latest: dict[str, Any], lock: threading.Lock) -> None:
    seen: int | None = None
    while True:
        frame = grabber.latest
        marker = id(frame)
        if frame is None or marker == seen:
            time.sleep(0.01)
            continue
        seen = marker
        try:
            annotated, state = analyzer.process_frame(frame.copy())
            jpeg = encode_frame_jpeg(annotated)
        except Exception as exc:  # noqa: BLE001
            with lock:
                latest["error"] = str(exc)
            time.sleep(0.2)
            continue
        with lock:
            latest["jpeg"] = jpeg
            latest["state"] = state
            latest["error"] = None


def run_sse_server(
    config: AnalyzeStreamConfig,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    source: Any = None,
) -> None:
    app = create_app(config, stream_source=source)
    active_source = source if source is not None else config.stream_source
    if isinstance(active_source, str) and active_source.isdigit():
        active_source = int(active_source)
    grabber = FrameGrabber(active_source)
    analyzer = _analyzer_for_camera(config, config.camera_id)
    threading.Thread(
        target=_detect_loop,
        args=(analyzer, grabber, app["latest"], app["latest_lock"]),
        name="snitch-detect",
        daemon=True,
    ).start()
    web.run_app(app, host=host, port=port, print=lambda *_args, **_kwargs: None)
