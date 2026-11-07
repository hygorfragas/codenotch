"""Cliente HTTP para o engine de decisão Jev (estado JSON, perguntas atômicas)."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx

from jev_image import JevImageClient, noul_is_true
from jev_metrics import jev_metrics

IMAGE_QUESTIONS = {
    "helmet": "Is a safety helmet or hard hat being worn on the head in `photo`? True only when the helmet is visibly on the head. False when the head is bare.",
    "goggles": "Are protective goggles or safety glasses being worn over the eyes in `photo`? False when the eyes are uncovered.",
    "gloves": "Are protective work gloves being worn on the hands in `photo`? False for bare hands.",
    "vest": "Is a high-visibility safety vest being worn on the torso in `photo`? False when the torso has no safety vest.",
    "phone": "Is the person using a smartphone, by tapping it, looking at the screen, or holding it against the ear? A phone held still and ignored, or no phone at all, is false.",
}

_image_client: JevImageClient | None = None

DEFAULT_TIMEOUT = httpx.Timeout(5.0, connect=2.0)


def _record_call(
    *,
    endpoint: str,
    trigger: str,
    payload: dict[str, Any],
    started: float,
    status: str,
    decision: str | None,
) -> None:
    jev_metrics.record(
        endpoint=endpoint,
        trigger=trigger,
        payload_bytes=len(json.dumps(payload).encode()),
        latency_ms=(time.perf_counter() - started) * 1000,
        status=status,
        decision=decision,
    )


async def ask_jev(
    base_url: str,
    state: dict[str, Any],
    questions: list[str],
    *,
    timeout: httpx.Timeout | None = None,
    trigger: str = "ppe_zone",
) -> dict[str, Any]:
    """
    Envia o JSON de estado e consulta perguntas em paralelo.

    Retorna mapa pergunta -> resposta booleana ou valor retornado pela API.
    """
    if not questions:
        return {}

    client_timeout = timeout or DEFAULT_TIMEOUT

    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=client_timeout) as client:
        started = time.perf_counter()
        recorded = False
        try:
            state_response = await client.post("/state", json=state)
            _record_call(
                endpoint="/state",
                trigger=trigger,
                payload=state,
                started=started,
                status=str(state_response.status_code),
                decision=None,
            )
            recorded = True
            state_response.raise_for_status()
        except Exception as exc:
            if not recorded:
                _record_call(
                    endpoint="/state",
                    trigger=trigger,
                    payload=state,
                    started=started,
                    status="timeout" if isinstance(exc, httpx.TimeoutException) else "error",
                    decision=None,
                )
            raise

        async def one(question: str) -> tuple[str, Any]:
            payload = {"question": question}
            ask_started = time.perf_counter()
            ask_recorded = False
            try:
                response = await client.post("/ask", json=payload)
                body = response.json()
                answer = body.get("answer", body)
                _record_call(
                    endpoint="/ask",
                    trigger=question,
                    payload=payload,
                    started=ask_started,
                    status=str(response.status_code),
                    decision=json.dumps(answer, ensure_ascii=False)[:80],
                )
                ask_recorded = True
                response.raise_for_status()
                return question, answer
            except Exception as exc:
                if not ask_recorded:
                    _record_call(
                        endpoint="/ask",
                        trigger=question,
                        payload=payload,
                        started=ask_started,
                        status="timeout" if isinstance(exc, httpx.TimeoutException) else "error",
                        decision=None,
                    )
                raise

        pairs = await asyncio.gather(*(one(q) for q in questions))

    return dict(pairs)


def ask_jev_sync(
    base_url: str,
    state: dict[str, Any],
    questions: list[str],
) -> dict[str, Any]:
    """Wrapper síncrono para uso dentro do loop de vídeo."""
    return asyncio.run(ask_jev(base_url, state, questions))


def image_client() -> JevImageClient:
    global _image_client
    if _image_client is None:
        _image_client = JevImageClient()
    return _image_client


def ask_image(jpeg: bytes, questions: dict[str, str], *, trigger: str) -> dict[str, Any]:
    """Manda um JPEG ao JEV. Não registra a chave nem a imagem."""
    started = time.perf_counter()
    result = image_client().ask_jpeg(jpeg, questions)
    answers = result.get("answers") if isinstance(result.get("answers"), dict) else {}
    summary: list[str] = []
    for name in questions:
        flag = noul_is_true(answers.get(name))
        if name == "phone":
            label = "uso" if flag else "nao_uso"
        else:
            label = "com" if flag else "sem"
        if flag is not None:
            summary.append(f"{name}:{label}")
    ledger = image_client().ledger
    _record_call(
        endpoint="/v1/systemone",
        trigger=trigger,
        payload={"bytes": len(jpeg), "itens": list(questions)},
        started=started,
        status=str(result.get("status")),
        decision=",".join(summary)[:80] or None,
    )
    result["resumo"] = summary
    result["enviadas"] = ledger.get("images_sent")
    result["usd"] = ledger.get("usd")
    return result
