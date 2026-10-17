from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def crear_productor(bootstrap_servers: str):
    from confluent_kafka import Producer

    return Producer(
        {
            "bootstrap.servers": bootstrap_servers,
            "client.id": "can-i-park",
            "enable.idempotence": True,
            "acks": "all",
        }
    )


def publicar_json(
    productor: Any,
    topic: str,
    payload: dict[str, Any],
    key: str | None = None,
    timeout: float = 5.0,
) -> None:
    errores_entrega: list[str] = []

    def confirmar_entrega(error: Any, _: Any) -> None:
        if error is not None:
            errores_entrega.append(str(error))

    productor.produce(
        topic=topic,
        key=key.encode("utf-8") if key else None,
        value=json.dumps(payload, default=str, ensure_ascii=False).encode("utf-8"),
        on_delivery=confirmar_entrega,
    )

    pendientes = productor.flush(timeout)
    if pendientes:
        raise RuntimeError(
            f"Kafka no confirmó la entrega de {pendientes} mensaje(s) dentro del tiempo esperado"
        )
    if errores_entrega:
        raise RuntimeError(f"Kafka reportó un error de entrega: {errores_entrega[0]}")


def crear_consumidor(bootstrap_servers: str, group_id: str, topic: str):
    from confluent_kafka import Consumer

    consumidor = Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumidor.subscribe([topic])
    return consumidor


def consumir_bucle(
    consumidor: Any,
    procesar: Callable[[dict[str, Any]], None],
    detener: Callable[[], bool],
) -> None:
    while not detener():
        mensaje = consumidor.poll(1.0)
        if mensaje is None:
            continue
        if mensaje.error():
            logger.warning("Kafka devolvió un error al consumir: %s", mensaje.error())
            continue

        try:
            payload = json.loads(mensaje.value().decode("utf-8"))
            procesar(payload)
        except Exception:
            # El offset no se confirma si la lógica falla.
            logger.exception("No se pudo procesar un mensaje de Kafka")
            raise

        consumidor.commit(message=mensaje, asynchronous=False)