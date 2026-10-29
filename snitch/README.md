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
