FROM python:3.12-alpine

WORKDIR /opt/jev

COPY docker/jev/jev_stub.py /opt/jev/jev_stub.py

EXPOSE 8787

CMD ["python", "-u", "/opt/jev/jev_stub.py"]
