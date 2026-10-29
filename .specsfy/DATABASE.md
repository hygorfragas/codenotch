# Banco de dados

Mapa de persistência do sistema. O app SNITCH em `snitch/` usa Laravel;
CodeNotch na raiz não persiste domínio SNITCH.

## Fontes de dados

<!-- specsfy:database:start -->
| Fonte | Tecnologia/forma | Configuração segura | Evidência |
| --- | --- | --- | --- |
| SNITCH — produção (normativo) | PostgreSQL | `DB_CONNECTION`, `DB_HOST`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD` (sem valores) | spec §2, NFR-001, AC-016 |
| SNITCH — testes | SQLite (arquivo dedicado) | `DB_CONNECTION`, `DB_DATABASE` em `snitch/.env.testing` | `snitch/.env.testing` |
| SNITCH — desenvolvimento local | SQLite (padrão skeleton) | `DB_*` em `snitch/.env.example` | `snitch/.env.example` |

## Estruturas detectadas (implementadas)

| Estrutura | Tipo | Campos principais | Relações | Fonte |
| --- | --- | --- | --- | --- |
| users | Tabela | id, name, email, password, timestamps | — | `snitch/database/migrations/0001_01_01_000000_create_users_table.php` |
| password_reset_tokens | Tabela | email, token, created_at | — | idem |
| sessions | Tabela | id, user_id, payload, last_activity | user_id → users | idem |
| cache / cache_locks | Tabela | key, value, expiration | — | `snitch/database/migrations/0001_01_01_000001_create_cache_table.php` |
| jobs / job_batches / failed_jobs | Tabela | fila Laravel padrão | — | `snitch/database/migrations/0001_01_01_000002_create_jobs_table.php` |
<!-- specsfy:database:end -->

## Domínio SNITCH (normativo — aguarda T022)

Seção 9 da spec ainda tem placeholders; o plano técnico aponta
`2026_10_28_000001_create_snitch_tables.php` (T022). Até a migration existir,
trate a tabela abaixo como **contrato alvo** derivado da spec, backlog e testes
Pest (`/snitch/episodes/*`, `/snitch/cameras/*`, `/snitch/locations/*`).

| Entidade | Responsabilidade | Atributos / regras (resumo) | Relações |
| --- | --- | --- | --- |
| Empresa | Tenant lógico na VPS do cliente | Isolamento total por deploy (NFR-001) | 1:N localidades, colaboradores |
| Localidade | Unidade operacional do gestor | EPIs obrigatórios, regra smartphone, zonas | N câmeras, N zonas, N episódios |
| Colaborador | Pessoa rastreada (única por empresa) | Histórico com foto, data, hora por episódio | N episódios; sem acesso ao próprio histórico |
| Câmera | Fonte RTSP/DVR | URL fluxo, setor, credencial **fora** do histórico do colaborador (NFR-002) | Pertence à localidade |
| Zona | Polígono na câmera | Tipo descanso / passagem / risco; tempo máximo só em passagem (FR-002, AC-008, AC-009) | Pertence à câmera/localidade |
| Episódio (registro) | Prova EPI ou ociosidade | Foto, `recorded_at`, tipo (EPI, zona, smartphone); nasce só quando regra estoura (PR-002) | Colaborador, localidade |
| Configuração de aviso | Canais por tipo | Painel ao vivo sempre; WhatsApp/Telegram/SMS/e-mail opcionais (FR-005) | Por localidade/tipo |

### Estados e retenção

- **PR-003**: alteração de regra de smartphone vale só para episódios futuros;
  histórico conserva a regra vigente na gravação.
- Apagar zona, câmera ou localidade (admin) **não** apaga histórico de EPI e
  ociosidade (spec §7 erros e casos-limite).
- Obstrução, inconclusivo e erro técnico ficam em logs, não no histórico do
  colaborador.

**Sincronização:** parcial — PostgreSQL e entidades normativas documentadas;
inventário detectado cobre apenas migrations Laravel default. Reexecutar
`update_database.mjs --project /workspace/snitch` após T022.

**Última revisão doc (T031):** 2026-10-29.

## Decisões, ownership e retenção

- **Ownership:** dados de episódio pertencem à empresa da VPS; gestor vê só sua
  localidade; admin vê a empresa inteira (spec §3 atores).
- **Classificação:** fotos de episódio são evidência operacional/jurídica;
  credenciais de câmera são segredo operacional (NFR-002).
- **Retenção:** não fixada na spec — registrar política por contrato quando
  definida.
