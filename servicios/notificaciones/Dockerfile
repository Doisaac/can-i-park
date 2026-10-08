FROM python:3.12-slim

WORKDIR /app
COPY servicios/notificaciones/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY shared /shared
RUN pip install --no-cache-dir /shared
COPY servicios/notificaciones/notificaciones_app /app/notificaciones_app

EXPOSE 8000
CMD ["uvicorn", "notificaciones_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
