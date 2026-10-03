FROM python:3.12-slim

WORKDIR /app
COPY servicios/disponibilidad/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY shared /shared
RUN pip install --no-cache-dir /shared
COPY servicios/disponibilidad/disponibilidad_app /app/disponibilidad_app

EXPOSE 8000
CMD ["uvicorn", "disponibilidad_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
