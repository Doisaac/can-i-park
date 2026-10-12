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


def main() -> None:
    print("== Prueba E2E real: Acceso -> Kafka -> Disponibilidad ==")
    esperar_servicio(f"{ACCESO}/health")
    esperar_servicio(f"{DISPONIBILIDAD}/health")

    inicial = solicitar_json(f"{DISPONIBILIDAD}/disponibilidad")
    if inicial["disponibles"] <= 0:
        raise RuntimeError("La prueba necesita al menos un espacio disponible")

    placa = f"E2E{uuid4().hex[:6].upper()}"
    entrada_realizada = False

    try:
        entrada = registrar(placa, "ENTRADA")
        resultado_entrada = esperar_resultado(entrada["evento_id"])
        assert resultado_entrada["aceptado"] is True
        entrada_realizada = True

        despues_entrada = solicitar_json(f"{DISPONIBILIDAD}/disponibilidad")
        assert despues_entrada["ocupados"] == inicial["ocupados"] + 1
        assert despues_entrada["disponibles"] == inicial["disponibles"] - 1

        salida = registrar(placa, "SALIDA")
        resultado_salida = esperar_resultado(salida["evento_id"])
        assert resultado_salida["aceptado"] is True
        entrada_realizada = False

        final = solicitar_json(f"{DISPONIBILIDAD}/disponibilidad")
        assert final["ocupados"] == inicial["ocupados"]
        assert final["disponibles"] == inicial["disponibles"]

        evidencia = (
            "CAN I PARK? - EVIDENCIA E2E REAL\n"
            f"Fecha UTC: {datetime.now(timezone.utc).isoformat()}\n"
            "Flujo validado: Acceso -> Kafka -> Disponibilidad\n"
            f"Placa de prueba: {placa}\n"
            f"Evento ENTRADA: {entrada['evento_id']}\n"
            f"Evento SALIDA: {salida['evento_id']}\n"
            f"Estado inicial/final: {json.dumps(final, ensure_ascii=False)}\n"
            "Resultado: APROBADO\n"
        )
        (RAIZ / "docs" / "EVIDENCIA_E2E.txt").write_text(evidencia, encoding="utf-8")
        print("OK: el evento atravesó Kafka y la disponibilidad volvió al estado inicial.")
        print("Evidencia guardada en docs/EVIDENCIA_E2E.txt")
    finally:
        if entrada_realizada:
            try:
                salida = registrar(placa, "SALIDA")
                esperar_resultado(salida["evento_id"])
            except Exception:
                pass


if __name__ == "__main__":
    main()
