# Stack do sistema

Documente tecnologias estruturais e a evidência executável que confirma cada
uma. Preserve decisões humanas nas seções livres deste arquivo.

## Inventário detectado

<!-- specsfy:stack:start -->
| Camada | Tecnologia | Evidência |
| --- | --- | --- |
| Framework | Laravel | `snitch/composer.json` (`laravel/framework`) |
| Linguagem | PHP | `snitch/composer.json` (`php`) |
| Testes | Pest | `snitch/composer.json` (`pestphp/pest`) |
| Testes | PHPUnit | `snitch/composer.json` (`phpunit/phpunit`) |
| Runtime | Node.js | snitch/package.json |
<!-- specsfy:stack:end -->

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

## Decisões e observações do projeto

Acrescente aqui escolhas, restrições e contexto que não podem ser inferidos dos
manifests.
