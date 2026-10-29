# Projeto

## História e motivação

O repositório **codenotch** hospeda o app macOS/Windows que exibe limites de uso
de ferramentas de IA na borda da tela. A partir de 2026-10, o mesmo hub passou
a versionar o **SNITCH — Encarregado Virtual**, produto distinto em
`snitch/`, nascido da necessidade de substituir fiscalização presencial por
evidência estatística imparcial de EPI e ociosidade (inbox e backlog
`0001-snitch-encarregado-virtual`).

## Finalidade

- **CodeNotch**: monitorar e exibir cotas de Claude, Cursor, Codex, Antigravity
  e provedores afins no desktop.
- **SNITCH**: converter fluxos RTSP/DVR em registros auditáveis (foto, data,
  hora) de conformidade de EPI e ociosidade, com painéis para gestores e
  admins na VPS de cada empresa.

## Pessoas e contexto de uso

| Papel | SNITCH |
| --- | --- |
| Admin | Visão da empresa inteira; pode apagar zona, câmera ou localidade. |
| Gestor | Opera uma localidade: painéis, câmera ao vivo, histórico de colaboradores. |
| Colaborador | Identificado no vídeo; não consulta o próprio histórico no produto. |

CodeNotch atende a pessoa desenvolvedora no próprio computador.

## Capacidades principais

**SNITCH (SPEC-0001, em implementação)**

- Motor de visão (YOLO/SH17 + supervision + Jev) na VPS do cliente.
- Registro de episódios de EPI faltante, ociosidade em zona de passagem e uso
  de smartphone quando habilitado.
- Painel global (totais sem nome) e painel por localidade (com colaborador).
- Câmera ao vivo via SSE com caixas desenhadas, sem criar registro só por abrir
  o stream.
- Avisos no painel e canais extras configuráveis por tipo de evento.

**CodeNotch**

- Leitura de usage/APIs locais e exibição na notch/tray (escopo existente na
  raiz do repositório).

## Limites

- SNITCH v1: interface Laravel/Blade, sem React (spec §10).
- Imagem de conceito enviada no chat **não** é layout obrigatório.
- Fine-tuning de pesos SH17 por cliente não altera código base — só arquivo de
  pesos (backlog).
- CodeNotch não gerencia câmeras, EPI ou episódios SNITCH.

## Contexto técnico

- **Hub:** Swift + Rust/Tauri (CodeNotch) + diretório `snitch/` (Laravel 13).
- **SNITCH:** PostgreSQL em produção por VPS; Pest + SQLite isolado em testes.
- Detalhes verificáveis: `.specsfy/STACK.md`, `.specsfy/DATABASE.md`,
  `.specsfy/RULES.md`, spec `specs/draft/0001-snitch-encarregado-virtual/spec.md`.

Estado 2026-10-29: base Laravel e testes RED versionados; domínio SNITCH
(migrations T022, motor Python, telas) ainda em aberto — ver notas de
sincronização em `.specsfy/DATABASE.md`.

**Última revisão doc (T033):** 2026-10-29.
