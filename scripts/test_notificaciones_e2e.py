from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ACCESO = os.getenv("ACCESO_URL", "http://localhost:8001")
DISPONIBILIDAD = os.getenv("DISPONIBILIDAD_URL", "http://localhost:8002")
NOTIFICACIONES = os.getenv("NOTIFICACIONES_URL", "http://localhost:8003")
RAIZ = Path(__file__).resolve().parents[1]


def solicitar_json(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def esperar_servicio(url: str, intentos: int = 60) -> None:
    for _ in range(intentos):
        try:
            solicitar_json(url)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"El servicio no respondió: {url}")


def registrar(placa: str, tipo: str) -> dict:
    return solicitar_json(
        f"{ACCESO}/movimientos",
        method="POST",
        payload={"placa": placa, "tipo": tipo},
    )


def esperar_resultado(evento_id: str, intentos: int = 50) -> dict:
    for _ in range(intentos):
        try:
            return solicitar_json(f"{DISPONIBILIDAD}/movimientos/{evento_id}")
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
        time.sleep(0.25)
    raise RuntimeError(f"El evento {evento_id} no fue procesado a tiempo")


def esperar_alerta(intentos: int = 50) -> dict:
    for _ in range(intentos):
        alertas = solicitar_json(f"{NOTIFICACIONES}/alertas")["alertas"]
        if alertas:
            return alertas[0]
        time.sleep(0.25)
    raise RuntimeError("No se recibió una alerta desde Kafka")


def main() -> None:
    print("== Prueba E2E real: Disponibilidad -> Kafka -> Notificaciones ==")
    esperar_servicio(f"{ACCESO}/health")
    esperar_servicio(f"{DISPONIBILIDAD}/health")
    esperar_servicio(f"{NOTIFICACIONES}/health")

    estado = solicitar_json(f"{DISPONIBILIDAD}/disponibilidad")
    if estado["capacidad"] != 3:
        raise RuntimeError(
            "Esta prueba se ejecuta con CAPACIDAD_ESTACIONAMIENTO=3. "
            "Usa scripts/validar_entrega para preparar el entorno."
        )
    if estado["ocupados"] != 0:
        raise RuntimeError("La prueba de notificaciones necesita un estado inicial vacío")

    placas = [f"N{uuid4().hex[:7].upper()}" for _ in range(2)]
    entradas_confirmadas: list[str] = []

    try:
        for placa in placas:
            entrada = registrar(placa, "ENTRADA")
            resultado = esperar_resultado(entrada["evento_id"])
            assert resultado["aceptado"] is True
            entradas_confirmadas.append(placa)

        alerta = esperar_alerta()
        assert alerta["estado"] == "POCOS_ESPACIOS"
        assert alerta["disponibles"] == 1

        evidencia = (
            "CAN I PARK? - EVIDENCIA E2E NOTIFICACIONES\n"
            f"Fecha UTC: {datetime.now(timezone.utc).isoformat()}\n"
            "Flujo validado: Disponibilidad -> Kafka -> Notificaciones\n"
            f"Alerta: {json.dumps(alerta, ensure_ascii=False)}\n"
            "Resultado: APROBADO\n"
        )
        (RAIZ / "docs" / "EVIDENCIA_NOTIFICACIONES_E2E.txt").write_text(
            evidencia,
            encoding="utf-8",
        )
        print("OK: el cambio de estado viajó por Kafka y Notificaciones generó la alerta.")
        print("Evidencia guardada en docs/EVIDENCIA_NOTIFICACIONES_E2E.txt")
    finally:
        for placa in entradas_confirmadas:
            try:
                salida = registrar(placa, "SALIDA")
                esperar_resultado(salida["evento_id"])
            except Exception:
                pass


if __name__ == "__main__":
    main()