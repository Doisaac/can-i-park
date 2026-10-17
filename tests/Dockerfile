FROM python:3.12-slim

WORKDIR /workspace

COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install --no-cache-dir -r /tmp/requirements-dev.txt

COPY shared /shared
RUN pip install --no-cache-dir /shared

COPY pytest.ini /workspace/pytest.ini
COPY shared /workspace/shared
COPY servicios /workspace/servicios
COPY tests /workspace/tests
COPY scripts /workspace/scripts

RUN mkdir -p /workspace/docs

CMD ["python", "-m", "pytest"]
