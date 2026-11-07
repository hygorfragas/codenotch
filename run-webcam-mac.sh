#!/bin/zsh
# Webcam do Mac (FaceTime) + MPS, no lugar do clipe em loop do Docker.
# O painel continua em http://127.0.0.1:8000 e lê o motor em host.docker.internal:8765.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
ENGINE="$ROOT/snitch/engine"
VENV="$ENGINE/.venv"
WEIGHTS="$ROOT/snitch/storage/engine/sh17.pt"

if [[ ! -f "$WEIGHTS" ]]; then
  echo "Pesos ausentes: $WEIGHTS"
  exit 1
fi

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip
  "$VENV/bin/pip" install -r "$ENGINE/requirements.txt"
fi

STOPPED=0
restart_docker() {
  if [[ "$STOPPED" == 1 ]]; then
    echo "Religando o snitch-engine do Docker na porta 8765."
    docker compose -f "$ROOT/docker-compose.yml" up -d --no-deps snitch-engine || true
  fi
}
trap restart_docker EXIT

if docker compose -f "$ROOT/docker-compose.yml" ps --status running --services 2>/dev/null | grep -qx snitch-engine; then
  echo "Parando o snitch-engine do Docker para liberar a porta 8765."
  docker compose -f "$ROOT/docker-compose.yml" stop snitch-engine
  STOPPED=1
fi

export SNITCH_VISION_MOCK=0
export JEV_URL="${JEV_URL:-http://127.0.0.1:8787}"
export SNITCH_WEB_URL="${SNITCH_WEB_URL:-http://127.0.0.1:8000}"
export SH17_WEIGHTS="$WEIGHTS"
export SNITCH_YOLO_DEVICE="${SNITCH_YOLO_DEVICE:-mps}"
export SNITCH_LOOP_SOURCE=0
export SNITCH_FALLBACK_SOURCE="${SNITCH_FALLBACK_SOURCE:-$ROOT/snitch/storage/engine/person-loop.avi}"

cd "$ENGINE"
echo "Se a câmera falhar: Ajustes do Sistema → Privacidade e Segurança → Câmera, e permita Terminal ou Cursor."
echo "Motor nativo em http://127.0.0.1:8765  dispositivo=$SNITCH_YOLO_DEVICE  fonte=${SNITCH_STREAM_SOURCE:-0}"
exec "$VENV/bin/python" analyze_stream.py --serve --host 0.0.0.0 --port 8765 --source "${SNITCH_STREAM_SOURCE:-0}"
