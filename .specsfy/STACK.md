<!-- specsfy:documentator:start -->
## SNITCH (snitch/)

| Camada | Tecnologia | Fonte |
| --- | --- | --- |
| API / painel | Laravel 13, PHP 8.3 | `snitch/composer.json` |
| Motor de visão | Python 3.12, YOLO (SH17), supervision, OpenCV | `snitch/engine/requirements.txt` |
| Ao vivo | SSE Python → proxy Laravel | `snitch/config/snitch.php` |
| Decisão | Jev (HTTP JSON de estado) | `snitch/engine/jev_client.py` |
| Testes | Pest (PHP), pytest (engine mock) | `snitch/tests/`, `snitch/engine/tests/` |

## Codenotch (raiz)

Aplicação macOS Swift — ver `project.yml` e `docs/architecture.md`.
<!-- specsfy:documentator:end -->
