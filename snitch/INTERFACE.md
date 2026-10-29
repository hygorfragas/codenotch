# Interface SNITCH

| Campo | Valor |
| --- | --- |
| Produto | SNITCH — Encarregado Virtual |
| Stack UI | Laravel Blade + Tailwind (sem React nesta versão) |
| Atualizado em | 2026-10-29 |

## Menus e navegação

| Menu | Destino | Permissão | Responsivo |
| --- | --- | --- | --- |
| Painel global | `GET /snitch/company/dashboard` (`snitch.company.dashboard`) | Gestor / Admin | Layout fluido até `max-w-7xl`, colunas empilham em mobile |
| Localidade (lista no painel global) | `GET /snitch/locations/{id}` | Gestor da localidade | Grid 1→3 colunas |
| Câmera ao vivo (expandida) | `GET /snitch/cameras/{id}/live/painel` | Gestor da localidade | Área principal `aspect-video` |
| Perfil do funcionário | `GET /snitch/employees/{id}` | Gestor da localidade | Grid histórico / foto / anexos |

## Telas (seção 10)

| Tela | View | Controller | Estados |
| --- | --- | --- | --- |
| Painel global | `resources/views/company/dashboard.blade.php` | `CompanyDashboardController` | KPIs, lista de localidades, episódios anônimos, vazio |
| Painel da localidade | `resources/views/locations/show.blade.php` | `LocationDashboardController` | Câmeras vazias (AC-013), episódios com nome, quadro de funcionários |
| Câmera expandida | `resources/views/cameras/live.blade.php` | `LiveCameraController@panel` | SSE conectando, ao vivo, erro SSE (AC-012) |
| Painel do funcionário | `resources/views/employees/show.blade.php` | `EmployeeProfileController` | Médias, foto, anexos, histórico; credencial oculta |

## Layout e componentes

| Componente | Arquivo | Consumidores |
| --- | --- | --- |
| Shell SNITCH | `resources/views/layouts/snitch.blade.php` | Todas as telas T026–T029 |
| Faixa KPI | `resources/views/components/kpi-strip.blade.php` | Painel global, painel da localidade |

## Breadcrumb

Empresa → localidade (quando aplicável) → tela atual (`aria-current="page"`).

## APIs usadas pela UI

| Uso | Rota |
| --- | --- |
| SSE ao vivo | `GET /snitch/cameras/{id}/live/stream` (`EventSource`) |

Made with 💻 by Hygor
