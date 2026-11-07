"""Adapter da Laya: juiz determinístico sobre fatos, sem imagem e sem GPU."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from fact_judge import judge_facts


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw.decode() or "{}")
        if not isinstance(data, dict):
            raise ValueError("JSON object expected")
        return data

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0].rstrip("/") == "/health":
            self._send(200, {"status": "ok", "engine": "laya", "judge": "facts"})
            return
        self._send(404, {"message": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/")
        try:
            data = self._read_json()
        except (json.JSONDecodeError, ValueError):
            self._send(400, {"message": "invalid json"})
            return
        if path == "/judge":
            verdict = judge_facts(data)
            self._send(200, {"engine": "laya", "judge": "facts", **verdict})
            return
        self._send(404, {"message": "not found"})


def main() -> None:
    ThreadingHTTPServer(("127.0.0.1", 8787), Handler).serve_forever()


if __name__ == "__main__":
    main()
