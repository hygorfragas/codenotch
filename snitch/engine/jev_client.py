"""Cliente HTTP para o engine de decisão Jev (estado JSON, perguntas atômicas)."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx

from jev_metrics import jev_metrics

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
