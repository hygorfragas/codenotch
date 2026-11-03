FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/snitch/engine

COPY snitch/engine/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir pytest

COPY snitch/engine/ /opt/snitch/engine/
COPY docker/engine/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && mkdir -p /clips /weights \
    && ffmpeg -y -f lavfi -i "testsrc2=size=640x360:rate=8:duration=6" \
        -an -c:v mpeg4 -q:v 5 /clips/demo.avi \
    && python -c "import cv2; c=cv2.VideoCapture('/clips/demo.avi'); ok, frame=c.read(); assert ok and frame is not None, 'clipe de teste ilegivel'; print(frame.shape)"

ENV PYTHONUNBUFFERED=1 \
    SNITCH_VISION_MOCK=1 \
    SNITCH_LOOP_SOURCE=1 \
    SH17_WEIGHTS=/weights/sh17.pt \
    JEV_URL=http://snitch-jev:8787 \
    MPLCONFIGDIR=/tmp/matplotlib

EXPOSE 8765

ENTRYPOINT ["/entrypoint.sh"]
