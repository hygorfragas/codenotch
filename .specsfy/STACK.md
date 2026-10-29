# Stack do sistema

Documente tecnologias estruturais e a evidência executável que confirma cada
uma. Preserve decisões humanas nas seções livres deste arquivo.

## Inventário detectado

<!-- specsfy:stack:start -->
| Camada | Tecnologia | Evidência |
| --- | --- | --- |
| Aplicação desktop | Swift (macOS) | `Package.swift`, `Sources/` |
| Aplicação desktop | Rust / Tauri (Windows) | `windows/codenotch/Cargo.toml` |
| Framework | Laravel | `snitch/composer.json` (`laravel/framework` ^13.17) |
| Linguagem | PHP | `snitch/composer.json` (`php` ^8.3) |
| Testes | Pest | `snitch/composer.json` (`pestphp/pest`) |
| Testes | PHPUnit | `snitch/composer.json` (`phpunit/phpunit`) |
| Runtime front-end (build) | Node.js | `snitch/package.json` |
<!-- specsfy:stack:end -->

## Decisões e observações do projeto

### Repositório hub (CodeNotch + SNITCH)

- **CodeNotch** permanece o produto principal versionado na raiz (Swift/Rust).
- **SNITCH — Encarregado Virtual** vive em `snitch/` (Laravel), spec
  `specs/draft/0001-snitch-encarregado-virtual/spec.md` (SPEC-0001).

### Stack normativa do SNITCH (SPEC-0001, NFR-001, AC-016, AC-017)

| Camada | Decisão | Fonte |
| --- | --- | --- |
| Painel web | Laravel 13, PHP 8.3, views Blade (sem React nesta versão) | spec §10, `snitch/composer.json` |
| Motor de visão | Python: YOLO (pesos SH17), `roboflow/supervision` (ByteTrack, PolygonZone, IoS), desenho de caixas no quadro | spec §2–3, backlog BACKLOG-0001 |
| Decisão estruturada | Jev Decide — POST com estado JSON (não imagem por quadro) | spec §2, FR implícito no plano |
| Ao vivo no painel | SSE com imagem já anotada pelo Python | spec §2, FR-004 |
| Persistência produção | PostgreSQL na VPS de cada empresa | spec §2, NFR-001, AC-016 |
| Isolamento | Uma VPS por empresa: Laravel + Python + PostgreSQL no mesmo ambiente | NFR-001, AC-017 |
| Testes aplicação | Pest (`snitch/tests/Feature/Snitch/`), runner TDD da spec | spec §11, `snitch/phpunit.xml` |
| Octane / Open Swoole | **Não decidido** para SNITCH nesta versão | spec §10 |

### Pendências de implementação (sincronização parcial)

- Migration `database/migrations/2026_10_28_000001_create_snitch_tables.php`
  (T022) ainda não commitada — motor Python (`engine/`) e rotas `/snitch/*`
  ainda ausentes; suíte Pest em RED (404).
- Pacotes Python (ultralytics, supervision, jev) entram quando T023+ forem
  implementados; não constam nos manifests atuais.

**Última revisão doc (T030):** 2026-10-29 — alinhado à spec; inventário
detectado reflete manifests; decisões SNITCH registradas acima.
