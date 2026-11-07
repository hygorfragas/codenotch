"""Cliente HTTP para o engine de decisão Jev (estado JSON, perguntas atômicas)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

DEFAULT_TIMEOUT = httpx.Timeout(5.0, connect=2.0)


async def ask_jev(
    base_url: str,
    state: dict[str, Any],
    questions: list[str],
    *,
    timeout: httpx.Timeout | None = None,
) -> dict[str, Any]:
    """
    Envia o JSON de estado e consulta perguntas em paralelo.

    Retorna mapa pergunta -> resposta booleana ou valor retornado pela API.
    """
    if not questions:
        return {}

    client_timeout = timeout or DEFAULT_TIMEOUT

    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=client_timeout) as client:
        await client.post("/state", json=state)
        batched = await _ask_batched(client, questions)
        if batched is not None:
            return batched

        async def one(question: str) -> tuple[str, Any]:
            try:
                response = await client.post("/ask", json={"question": question})
                response.raise_for_status()
                body = response.json()
            except Exception:  # noqa: BLE001 — uma pergunta desconhecida não apaga as outras
                return question, None
            return question, body.get("answer", body)

        pairs = await asyncio.gather(*(one(q) for q in questions))

    return dict(pairs)


_BATCH_SUPPORTED: bool | None = None


async def _ask_batched(client: httpx.AsyncClient, questions: list[str]) -> dict[str, Any] | None:
    """Uma ida só quando a Laya entende várias perguntas. Senão, o chamador paraleliza."""
    global _BATCH_SUPPORTED
    if _BATCH_SUPPORTED is False:
        return None
    try:
        response = await client.post("/ask", json={"questions": questions})
    except Exception:  # noqa: BLE001
        _BATCH_SUPPORTED = False
        return None
    if response.status_code != 200:
        _BATCH_SUPPORTED = False
        return None
    try:
        body = response.json()
    except Exception:  # noqa: BLE001
        _BATCH_SUPPORTED = False
        return None
    answers = body.get("answers") if isinstance(body, dict) else None
    if not isinstance(answers, dict):
        _BATCH_SUPPORTED = False
        return None
    _BATCH_SUPPORTED = True
    return {question: answers.get(question) for question in questions}


def ask_jev_sync(
    base_url: str,
    state: dict[str, Any],
    questions: list[str],
) -> dict[str, Any]:
    """Wrapper síncrono para uso dentro do loop de vídeo."""
    return asyncio.run(ask_jev(base_url, state, questions))
