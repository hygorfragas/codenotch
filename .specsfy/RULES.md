# Regras do sistema

Estas regras complementam as instruções dos agentes sem substituir specs ou
critérios de aceite. SNITCH (SPEC-0001) em `snitch/`; CodeNotch segue regras
próprias na raiz.

## Arquitetura

- **PR-001**: análise de vídeo e painel na VPS da empresa; câmera só entrega RTSP.
- **PR-002**: abrir câmera ao vivo **não** cria registro; registro nasce quando
  regra configurada estoura (FR-001–FR-003).
- **PR-003**: mudança de regra de smartphone aplica-se só adiante; passado
  mantém regra anterior (AC-003, FR-003).
- **Fronteira Laravel ↔ Python**: Python produz quadros anotados e estado JSON
  para Jev; Laravel persiste episódios, expõe painel e SSE (spec §8).
- **Multi-tenant**: isolamento por VPS (NFR-001), não por row-level sharing
  entre empresas.

## Código e qualidade

- App SNITCH: código Laravel em `snitch/` (PSR-4 `App\`), rotas e controllers
  sob prefixo `/snitch` conforme testes Pest.
- Alterações de schema exigem migration versionada em
  `snitch/database/migrations/` e tarefa `[MIGRATION]` na spec.
- Interface SNITCH: Blade na v1 (sem React); não introduzir Octane até decisão
  explícita na spec (§10).
- Hub: não promover arquivos SNITCH para a raiz Swift/Rust nem misturar
  dependências Composer do `snitch/` com CodeNotch.

## Testes

- Runner TDD SNITCH: Pest com `--env=testing` e banco SQLite dedicado
  (`snitch/.env.testing`, distinto de `.env`).
- Antes de migrate/test: `check_database_safety.mjs --project /workspace/snitch`.
- Marcadores `SPECSFY:` nos testes em `snitch/tests/Feature/Snitch/` ligam AC/FR
  à spec; RED esperado até T022+ implementarem rotas.
- Proibido `migrate:fresh`, `db:wipe` e equivalentes em agentes (Specsfy 07).

## Segurança e privacidade

- **NFR-002**: credencial de câmera/DVR nunca aparece no histórico do
  colaborador (AC-019–AC-021).
- Papéis: **Admin** (empresa inteira, apaga zona/câmera/localidade); **Gestor**
  (só sua localidade); **Colaborador** (sem visão do próprio histórico).
- Gestor não vê dados de outra empresa (AC-018).
- Não registrar valores de `.env`, tokens RTSP ou senhas em docs ou evidências.

## Operação

- Deploy SNITCH: Laravel + PostgreSQL + serviço Python na mesma VPS do cliente.
- Canais de aviso (WhatsApp, Telegram, SMS, e-mail) são opt-in por tipo;
  painel ao vivo é canal padrão (FR-005, AC-014, AC-015).
- SSE interrompido: UI mostra erro; registros já gravados permanecem (AC-012).

## Regras específicas do projeto

- **FR-003 / smartphone**: se desligado na localidade, celular na mão não gera
  ociosidade (AC-010); se ligado, após o limite conta 1 minuto de ociosidade por
  minuto adicional.
- **FR-002 / zonas**: ociosidade por tempo máximo só em zona tipo **passagem**
  com tempo configurado (AC-008, AC-009).
- **EPI**: registro quando falta EPI marcado obrigatório na localidade, com foto
  e timestamp (FR-001, AC-001).
- Specsfy: `specs/draft/0001-snitch-encarregado-virtual/spec.md` é fonte
  normativa; contexto em `.specsfy/` e `PROJECT.md` é derivado.

**Última revisão doc (T032):** 2026-10-29.
