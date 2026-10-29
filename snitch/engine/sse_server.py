"""Servidor SSE mínimo — publica JPEG base64 anotado para o Laravel fazer proxy."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from aiohttp import web

from analyze_stream import AnalyzeStreamConfig, StreamAnalyzer, encode_frame_jpeg, load_config_from_env


async def health(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


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
    base_config = request.app["snitch_config"]
    source = request.app.get("stream_source", base_config.stream_source)
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    response = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
    await response.prepare(request)

    analyzer = _analyzer_for_camera(base_config, camera_id)

    def iterate():
        for annotated, state in analyzer.frames(source):
            payload = {
                "camera_id": camera_id,
                "image_jpeg_base64": encode_frame_jpeg(annotated),
                "state": state,
            }
            yield f"event: frame\ndata: {json.dumps(payload)}\n\n".encode()

    try:
        for chunk in iterate():
            await response.write(chunk)
            await asyncio.sleep(0)  # cooperativo
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        err = f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"
        await response.write(err.encode())

    return response


def create_app(config: AnalyzeStreamConfig | None = None, stream_source: Any = None) -> web.Application:
    app = web.Application()
    app["snitch_config"] = config or load_config_from_env()
    if stream_source is not None:
        app["stream_source"] = stream_source
    app.router.add_get("/health", health)
    app.router.add_get("/cameras/{camera}/stream", camera_stream)
    return app


def run_sse_server(
    config: AnalyzeStreamConfig,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    source: Any = None,
) -> None:
    app = create_app(config, stream_source=source)
    web.run_app(app, host=host, port=port, print=lambda *_args, **_kwargs: None)
