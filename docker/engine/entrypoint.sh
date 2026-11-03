#!/bin/sh
set -eu

cd /opt/snitch/engine
python -c "import cv2, numpy, supervision"

exec python analyze_stream.py \
    --serve \
    --host 0.0.0.0 \
    --port 8765 \
    --source "${SNITCH_STREAM_SOURCE:-/clips/demo.avi}"
