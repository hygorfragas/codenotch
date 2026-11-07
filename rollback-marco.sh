#!/bin/zsh
# Volta o SNITCH para um marco gravado fora do Git.
#
# Uso:
#   ./rollback-marco.sh <tag> [--dry-run] [--with-database]
#
# O marco fica em ~/codenotch-marcos/<tag> (ou em $SNITCH_MARCOS_DIR):
#   weights/sh17.pt, weights/sh17.mlpackage, env/.env, database/database.sqlite
# e as imagens Docker snitch-web:<tag> e snitch-engine:<tag>.
#
# Sem --dry-run o comando:
#   1. recusa se a árvore tiver mudança rastreada
#   2. faz git reset --hard na tag, na branch atual
#   3. copia pesos e pacote CoreML de volta para snitch/storage/engine
#   4. recoloca as imagens :local a partir da tag e recria os containers sem rebuild
#   5. com --with-database, troca o SQLite do volume snitch-data pelo snapshot
#
# --dry-run só confere tag, pasta, arquivos e imagens, e imprime o que faria.
set -euo pipefail

export PATH="/usr/local/bin:/opt/homebrew/bin:${PATH:-/usr/bin:/bin}"
DOCKER=""
for candidate in /usr/local/bin/docker /opt/homebrew/bin/docker; do
  if [[ -x "$candidate" ]]; then
    DOCKER="$candidate"
    break
  fi
done
if [[ -z "$DOCKER" ]] && command -v docker >/dev/null 2>&1; then
  DOCKER="$(command -v docker)"
fi
if [[ -z "$DOCKER" ]]; then
  echo "docker não encontrado." >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")" && pwd)"
MARCOS_ROOT="${SNITCH_MARCOS_DIR:-$HOME/codenotch-marcos}"
DRY=0
WITH_DB=0
TAG=""

usage() {
  sed -n '2,20p' "$0"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --with-database) WITH_DB=1 ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    -*) echo "Opção desconhecida: $1" >&2; usage; exit 2 ;;
    *)
      if [[ -n "$TAG" ]]; then
        echo "Informe uma única tag." >&2
        exit 2
      fi
      TAG="$1"
      ;;
  esac
  shift
done

if [[ -z "$TAG" ]]; then
  usage
  exit 2
fi

DEST="$MARCOS_ROOT/$TAG"
say() { printf '%s\n' "$*"; }
run() {
  say "+ $*"
  if [[ "$DRY" == 0 ]]; then
    eval "$1"
  fi
}

if ! git -C "$ROOT" rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  echo "Tag ausente: $TAG" >&2
  exit 1
fi
COMMIT="$(git -C "$ROOT" rev-parse "$TAG^{commit}")"
say "Marco $TAG em $COMMIT"

for path in \
  "$DEST/weights/sh17.pt" \
  "$DEST/weights/sh17.mlpackage/Manifest.json" \
  "$DEST/env/.env" \
  "$DEST/database/database.sqlite"
do
  if [[ ! -e "$path" ]]; then
    echo "Arquivo do marco ausente: $path" >&2
    exit 1
  fi
done

for image in "snitch-web:$TAG" "snitch-engine:$TAG"; do
  if ! "$DOCKER" image inspect "$image" >/dev/null; then
    echo "Imagem Docker ausente: $image" >&2
    exit 1
  fi
done

say "Pesos, pacote CoreML, .env, SQLite e imagens encontrados em $DEST"

if [[ "$DRY" == 0 ]]; then
  if [[ -n "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]]; then
    echo "A árvore tem mudanças rastreadas. Guarde ou descarte antes do rollback." >&2
    exit 1
  fi
fi

run "git -C \"$ROOT\" reset --hard \"$TAG\""
run "cp -p \"$DEST/weights/sh17.pt\" \"$ROOT/snitch/storage/engine/sh17.pt\""
run "rm -rf \"$ROOT/snitch/storage/engine/sh17.mlpackage\""
run "cp -R \"$DEST/weights/sh17.mlpackage\" \"$ROOT/snitch/storage/engine/sh17.mlpackage\""
run "\"$DOCKER\" tag \"snitch-web:$TAG\" snitch-web:local"
run "\"$DOCKER\" tag \"snitch-engine:$TAG\" snitch-engine:local"
run "\"$DOCKER\" compose -f \"$ROOT/docker-compose.yml\" up -d --no-build --force-recreate --no-deps snitch-web snitch-engine"

if [[ "$WITH_DB" == 1 ]]; then
  run "\"$DOCKER\" compose -f \"$ROOT/docker-compose.yml\" cp \"$DEST/database/database.sqlite\" snitch-web:/data/database.sqlite"
  run "\"$DOCKER\" compose -f \"$ROOT/docker-compose.yml\" cp \"$DEST/env/.env\" snitch-web:/var/www/html/.env"
  say "Banco e .env restaurados no container."
else
  say "Banco mantido. Para restaurar o snapshot: ./rollback-marco.sh $TAG --with-database"
fi

if [[ "$DRY" == 1 ]]; then
  say "Dry-run concluído. Nada foi alterado."
fi
