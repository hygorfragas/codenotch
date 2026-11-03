#!/usr/bin/env python3
"""Stand-in local do Jev.

Contrato usado por snitch/engine/jev_client.py:
  POST /state  JSON do quadro (sem pixels)
  POST /ask    {"question": "..."} -> {"answer": <bool>}
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

_lock = threading.Lock()
_state: dict[str, Any] = {"persons": []}


def _answer(question: str, state: dict[str, Any]) -> bool:
    persons = state.get("persons") or []
    if question == "any_missing_required_ppe":
        return any(person.get("ppe_missing") for person in persons)
    if question == "any_person_in_restricted_zone":
        return any(person.get("in_zones") for person in persons)
    return False


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw.decode() or "{}")
        if not isinstance(data, dict):
            raise ValueError("JSON object expected")
        return data

    def _send(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0].rstrip("/") == "/health":
            self._send(200, {"status": "ok"})
            return
        self._send(404, {"message": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/")
        try:
            data = self._read_json()
        except (json.JSONDecodeError, ValueError):
            self._send(400, {"message": "invalid json"})
            return

        if path == "/state":
            with _lock:
                _state.clear()
                _state.update(data)
            self._send(200, {"ok": True})
            return

        if path == "/ask":
            question = str(data.get("question", ""))
            with _lock:
                snapshot = dict(_state)
            self._send(200, {"answer": _answer(question, snapshot), "question": question})
            return

        self._send(404, {"message": "not found"})


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 8787), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
