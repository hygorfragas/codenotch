# Design system — SNITCH

| Campo | Valor |
| --- | --- |
| Escopo | Painéis Laravel SNITCH |
| Status | Ativo |
| Versão | 1.0.0 |
| Atualizado em | 2026-10-29 |

## Direção visual

- Fundo `slate-950`, superfícies `slate-900/40`, bordas `slate-800`.
- Acento operacional `emerald-400/600` (ações primárias e status ao vivo).
- Erro ao vivo `red-400` (SSE indisponível).
- Tipografia: `Instrument Sans` (via Tailwind theme), hierarquia H1 no layout, H2 por seção.
- Densidade operacional: KPIs no topo, listas investigáveis abaixo.

## Revisão visual (T026–T029)

- Viewports conferidos: 390×844 (mobile), 1280×800 (desktop).
- Estados: vazio, conteúdo, erro SSE na câmera expandida.
- Método: servidor local + inspeção DOM/render (Playwright manual via browser).

Made with 💻 by Hygor
