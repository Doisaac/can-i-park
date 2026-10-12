#!/usr/bin/env sh
set -eu

echo "== 0. Verificando Docker =="
docker info >/dev/null

echo "== 1. Construyendo entorno reproducible de pruebas =="
docker compose --profile tools build pruebas

echo "== 2. Validacion de sintaxis dentro de Docker =="
docker compose --profile tools run --rm pruebas python -m compileall -q .

echo "== 3. Pruebas automatizadas dentro de Docker =="
docker compose --profile tools run --rm pruebas python -m pytest

echo "== 4. Preparando prueba real con Kafka =="
docker compose down --remove-orphans

export CAPACIDAD_ESTACIONAMIENTO=3
export UMBRAL_POCOS_ESPACIOS=1
VALIDACION_OK=0

cleanup() {
  unset CAPACIDAD_ESTACIONAMIENTO || true
  unset UMBRAL_POCOS_ESPACIOS || true

  if [ "$VALIDACION_OK" -eq 1 ]; then
    echo "== 9. Restaurando configuracion normal (100 / 10) =="
    docker compose down --remove-orphans
    docker compose up -d
    echo
    echo "VALIDACION COMPLETA: OK"
    echo "Los contenedores quedaron nuevamente con la configuracion normal."
    echo "Interfaz: http://localhost:8080"
  fi
}
trap cleanup EXIT

docker compose up -d --build

echo "== 5. Flujo real Acceso -> Kafka -> Disponibilidad =="
docker compose --profile tools run --rm pruebas python scripts/test_e2e.py

echo "== 6. Flujo real Disponibilidad -> Kafka -> Notificaciones =="
docker compose --profile tools run --rm pruebas python scripts/test_notificaciones_e2e.py

echo "== 7. Interfaz =="
docker compose --profile tools run --rm pruebas python scripts/test_interfaz.py

echo "== 8. Estado de contenedores durante la prueba =="
docker compose ps

VALIDACION_OK=1
