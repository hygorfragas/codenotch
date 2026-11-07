"""Cliente de imagem do JEV.

A chave fica só em ~/.config/snitch/jev_api_key. Este módulo não imprime
nem grava o valor. Cada JPEG enviado é cacheado pelo SHA-256: uma repetição
não gera outra cobrança. O teto padrão é US$ 0,50 e a chamada que o cruzaria
não sai.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

PRICE_PER_IMAGE_USD = 0.0001
CEILING_USD = 0.50
MIN_SIDE = 280
MAX_SIDE = 1568
MIN_AREA = 78_400
API_URL = "https://api.typesafe.ai/v1/systemone"
KEY_PATH = Path.home() / ".config" / "snitch" / "jev_api_key"
CACHE_DIR = Path.home() / ".config" / "snitch" / "jev-image-cache"

Transport = Callable[[bytes, dict[str, str]], tuple[int, dict[str, Any], float]]


def fit_bgr(image: np.ndarray) -> np.ndarray:
    """Encaixa no intervalo aceito pela API: lados de 280 a 1568 e área mínima.

    Sobe o recorte quando isso não estoura o lado máximo. Se a foto é larga
    demais para subir, completa com borda preta até o mínimo.
    """
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    height, width = image.shape[:2]
    scale = 1.0
    if max(height, width) > MAX_SIDE:
        scale = MAX_SIDE / float(max(height, width))
    if min(height, width) * scale < MIN_SIDE:
        scale_up = MIN_SIDE / float(min(height, width))
        if max(height, width) * scale_up <= MAX_SIDE:
            scale = scale_up
    if scale != 1.0:
        interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
        image = cv2.resize(
            image,
            (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
            interpolation=interpolation,
        )
    height, width = image.shape[:2]
    if max(height, width) > MAX_SIDE:
        scale = MAX_SIDE / float(max(height, width))
        image = cv2.resize(
            image,
            (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
            interpolation=cv2.INTER_AREA,
        )
        height, width = image.shape[:2]
    pad_bottom = max(0, MIN_SIDE - height)
    pad_right = max(0, MIN_SIDE - width)
    if pad_bottom or pad_right:
        image = cv2.copyMakeBorder(
            image,
            pad_bottom // 2,
            pad_bottom - pad_bottom // 2,
            pad_right // 2,
            pad_right - pad_right // 2,
            cv2.BORDER_CONSTANT,
            value=(0, 0, 0),
        )
    return image


def encode_jpeg(image: np.ndarray, quality: int = 85) -> bytes:
    fitted = fit_bgr(image)
    ok, encoded = cv2.imencode(".jpg", fitted, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("não foi possível codificar o JPEG")
    return encoded.tobytes()


def crop_box(image: np.ndarray, box: Any, pad_ratio: float) -> np.ndarray:
    height, width = image.shape[:2]
    x1, y1, x2, y2 = (float(value) for value in box)
    pad_x = (x2 - x1) * pad_ratio
    pad_y = (y2 - y1) * pad_ratio
    left = max(0, int(x1 - pad_x))
    top = max(0, int(y1 - pad_y))
    right = min(width, int(x2 + pad_x))
    bottom = min(height, int(y2 + pad_y))
    if right - left < 8 or bottom - top < 8:
        return image
    return image[top:bottom, left:right]


def noul_is_true(answer: Any, threshold: float = 0.5) -> bool | None:
    if isinstance(answer, bool):
        return answer
    if not isinstance(answer, dict):
        return None
    for key in ("noul", "probability", "confidence"):
        value = answer.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value) >= threshold
    for key in ("answer", "value"):
        value = answer.get(key)
        if isinstance(value, bool):
            return value
    return None


def _atomic_write(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


class JevImageClient:
    def __init__(
        self,
        cache_dir: Path | None = None,
        key_path: Path | None = None,
        ceiling_usd: float | None = None,
        price_usd: float = PRICE_PER_IMAGE_USD,
        transport: Transport | None = None,
        url: str = API_URL,
    ) -> None:
        self.cache_dir = Path(cache_dir or CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.key_path = Path(key_path or KEY_PATH)
        self.ceiling_usd = None if ceiling_usd is None else float(ceiling_usd)
        self.price_usd = float(price_usd)
        self.transport = transport
        self.url = url
        self.ledger_path = self.cache_dir / "ledger.json"
        self.reconcile()

    def reconcile(self) -> dict[str, float | int]:
        sent = 0
        for path in self.cache_dir.glob("*.json"):
            if path.name in {"ledger.json", "ledger.json.tmp"}:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if payload.get("charged"):
                sent += 1
        ledger = {
            "images_sent": sent,
            "usd": round(sent * self.price_usd, 6),
            "price_per_image_usd": self.price_usd,
            "ceiling_usd": self.ceiling_usd,
        }
        _atomic_write(self.ledger_path, json.dumps(ledger, indent=2) + "\n")
        self.ledger = ledger
        return ledger

    def remaining_usd(self) -> float:
        return round(self.ceiling_usd - float(self.ledger["usd"]), 6)

    def cache_path(self, digest: str) -> Path:
        return self.cache_dir / f"{digest}.json"

    def read_cache(self, digest: str) -> dict[str, Any] | None:
        path = self.cache_path(digest)
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def ask_jpeg(self, jpeg: bytes, questions: dict[str, str]) -> dict[str, Any]:
        digest = hashlib.sha256(jpeg).hexdigest()
        cached = self.read_cache(digest)
        if cached and cached.get("status") == 200 and isinstance(cached.get("answers"), dict):
            if all(name in cached["answers"] for name in questions):
                return {
                    "sha256": digest,
                    "status": 200,
                    "answers": cached["answers"],
                    "latency_ms": cached.get("latency_ms"),
                    "charged": False,
                    "cache": True,
                    "usage": cached.get("usage"),
                }
        if (
            self.ceiling_usd is not None
            and float(self.ledger["usd"]) + self.price_usd >= self.ceiling_usd
        ):
            return {
                "sha256": digest,
                "status": "teto",
                "answers": None,
                "latency_ms": None,
                "charged": False,
                "cache": False,
                "usage": None,
            }
        status, body, latency_ms = self._send(jpeg, questions)
        answers = body.get("answers") if isinstance(body, dict) else None
        charged = status != 401
        record = {
            "sha256": digest,
            "status": status,
            "answers": answers if isinstance(answers, dict) else None,
            "latency_ms": round(latency_ms, 1),
            "charged": charged and status == 200,
            "usage": body.get("usage") if isinstance(body, dict) else None,
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        if status == 200 and isinstance(answers, dict):
            _atomic_write(self.cache_path(digest), json.dumps(record) + "\n")
            self.reconcile()
            return {**record, "cache": False}
        if status == 401:
            return {**record, "cache": False, "error": "auth"}
        record["charged"] = False
        return {**record, "cache": False, "error": "http"}

    def _send(self, jpeg: bytes, questions: dict[str, str]) -> tuple[int, dict[str, Any], float]:
        if self.transport is not None:
            return self.transport(jpeg, questions)
        try:
            key = self.key_path.read_text(encoding="utf-8").strip()
        except OSError:
            return 401, {}, 0.0
        if not key:
            return 401, {}, 0.0
        try:
            return self._post(jpeg, questions, key)
        except Exception:
            return 0, {}, 0.0

    def _post(self, jpeg: bytes, questions: dict[str, str], key: str) -> tuple[int, dict[str, Any], float]:
        reference = "snitch-img"
        payload = {
            "model": "jev-latest",
            "state": {"photo": reference},
            "assets": {reference: {"type": "image", "part": "photo"}},
            "questions": {
                name: {"type": "noul", "instructions": text}
                for name, text in questions.items()
            },
        }
        boundary = "snitch" + uuid.uuid4().hex
        body = b"".join((
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"request\"\r\nContent-Type: application/json\r\n\r\n".encode(),
            json.dumps(payload).encode(),
            f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"photo.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n".encode(),
            jpeg,
            f"\r\n--{boundary}--\r\n".encode(),
        ))
        request = urllib.request.Request(
            self.url,
            data=body,
            method="POST",
            headers={
                "Authorization": "Bearer " + key,
                "TypeSafe-Danger-Zone-Images": "true",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                raw = response.read()
                status = int(getattr(response, "status", 200))
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            status = int(exc.code)
        except (urllib.error.URLError, TimeoutError, OSError):
            return 0, {}, (time.perf_counter() - started) * 1000
        latency_ms = (time.perf_counter() - started) * 1000
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {}
        return status, parsed, latency_ms
