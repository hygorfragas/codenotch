# SNITCH — Encarregado Virtual

Aplicação Laravel (`snitch/`) + motor de visão Python (`snitch/engine/`).

## Motor de visão (T023)

- **YOLO** com pesos **SH17** (`SH17_WEIGHTS`, padrão `storage/engine/sh17.pt`)
- **supervision**: `ByteTrack`, `PolygonZone`, anotação de caixas
- **Jev**: JSON de estado via `JEV_URL` (sem enviar pixels)

```bash
cd engine
pip install -r requirements.txt
export SNITCH_VISION_MOCK=1   # desenvolvimento sem GPU/pesos
python analyze_stream.py --serve --port 8765 --source 0
```

Endpoints do processo Python:

- `GET /health` — health check para o Laravel
- `GET /cameras/{id}/stream` — SSE (`event: frame`, JPEG base64 anotado)

## SSE ao vivo (T025)

Laravel faz proxy do SSE do Python:

- `GET /snitch/cameras/{id}/live` — metadados JSON (`creates_records: false`)
- `GET /snitch/cameras/{id}/stream` — fluxo SSE para o painel
- `GET /snitch/locations/{id}/cameras` — listagem (vazia até T022)

Configure `SNITCH_ENGINE_URL` (padrão `http://127.0.0.1:8765`).

## Testes

```bash
# PHP (Pest)
php artisan test --env=testing tests/Feature/Snitch

# Python (mock)
cd engine && SNITCH_VISION_MOCK=1 PYTHONPATH=. python3 -m pytest tests/ -q
```

## Docker no Mac

Sobe o painel Laravel, o motor de visão e um Jev local. As imagens oficiais são multi-arquitetura: o mesmo `docker-compose.yml` vale para Apple Silicon e Intel. O banco continua SQLite (volume `snitch-data`), sem Postgres.

Na raiz do repositório:

```bash
docker compose up -d --build
docker compose ps
docker compose down
```

`down` remove os containers e mantém o arquivo SQLite no volume.

O padrão é detecção simulada (`SNITCH_VISION_MOCK=1`). Os pesos oficiais SH17 já podem ficar em `snitch/storage/engine/sh17.pt` (montado no motor como `/weights/sh17.pt`, variável `SH17_WEIGHTS`). O arquivo neste Mac é o **YOLOv8n treinado no SH17** (`yolo8n.pt`, release `v1` de [ahmadmughees/SH17dataset](https://github.com/ahmadmughees/SH17dataset/releases/tag/v1)): **6252377 bytes (5,96 MiB)**. O `.gitignore` dessa pasta deixa o `.pt` fora do Git. Para a detecção real, recrie só o motor. No Docker do Mac o PyTorch da imagem é CPU:

```bash
SNITCH_VISION_MOCK=0 docker compose up -d --no-deps --force-recreate snitch-engine
```

Sem esse arquivo o motor recusa a inferência real. Volte ao mock com `SNITCH_VISION_MOCK=1` na mesma linha.

As 17 classes gravadas nesse `yolo8n.pt` seguem o `sh17.yaml` oficial (`person`, `ear`, `ear-mufs`, `face`, `face-guard`, `face-mask`, `foot`, `tool`, `glasses`, `gloves`, `helmet`, `hands`, `head`, `medical-suit`, `shoes`, `safety-suit`, `safety-vest`). A tupla `SH17_CLASS_NAMES` do motor ainda usa outros nomes; o id da classe do peso não coincide com essa tupla.

O clipe de teste (`/clips/demo.avi`, gerado na imagem) fica em loop no lugar da webcam, então a página ao vivo continua recebendo quadros.

URLs neste Mac:

- Painel: http://127.0.0.1:8000/ (redireciona para o dashboard global)
- Dashboard global: http://127.0.0.1:8000/snitch/company/dashboard
- Localidade com câmera (Pátio principal): http://127.0.0.1:8000/snitch/locations/2
- Localidade sem câmera: http://127.0.0.1:8000/snitch/locations/1
- Câmera ao vivo: http://127.0.0.1:8000/snitch/cameras/1/live/painel
- Health do motor: http://127.0.0.1:8765/health
- SSE do motor: http://127.0.0.1:8765/cameras/1/stream
- Health do Jev (túnel Laya no host): http://127.0.0.1:8787/health

Caixas e SSE: a página ao vivo abre `EventSource` em `/snitch/cameras/{id}/stream`. O Laravel faz proxy do motor. Cada evento `frame` traz `image_jpeg_base64` (JPEG já com as caixas) e `state`. No mock a caixa é de uma pessoa sintética, desenhada em todo quadro.

O motor fala com o Jev em `JEV_URL=http://host.docker.internal:8787` (túnel no Mac, porta 8787). `docker compose up -d` não sobe o `snitch-jev`. O stand-in local só entra com `docker compose --profile stub-jev up -d snitch-jev`, e essa porta não pode estar ocupada pelo túnel.

O contrato continua o de `engine/jev_client.py`:

1. `POST /state` com o JSON do quadro (pessoas, EPI faltando, zonas). Não vai pixel.
2. `POST /ask` com `{"question":"any_missing_required_ppe"}` (ou `any_person_in_restricted_zone`).
3. Resposta: `{"answer": true}` ou `{"answer": false}`.

No mock a pessoa sintética não usa EPI e a zona restrita não entra na conta, então o painel mostra **EPI obrigatório faltando: sim** e **Pessoa em zona restrita: não**.

Testes, sem apagar o SQLite de demonstração:

```bash
docker compose exec snitch-web sh -lc 'touch database/testing.sqlite && php artisan test --env=testing tests/Feature/Snitch'
docker compose exec -e SNITCH_VISION_MOCK=1 snitch-engine python -m pytest tests/ -q
```
