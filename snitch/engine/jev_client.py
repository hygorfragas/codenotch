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

        async def one(question: str) -> tuple[str, Any]:
            response = await client.post("/ask", json={"question": question})
            response.raise_for_status()
            body = response.json()
            return question, body.get("answer", body)

        pairs = await asyncio.gather(*(one(q) for q in questions))

    return dict(pairs)


def ask_jev_sync(
    base_url: str,
    state: dict[str, Any],
    questions: list[str],
) -> dict[str, Any]:
    """Wrapper síncrono para uso dentro do loop de vídeo."""
    return asyncio.run(ask_jev(base_url, state, questions))
