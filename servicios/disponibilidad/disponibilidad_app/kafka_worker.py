from __future__ import annotations

import logging
import threading
from typing import Any

from canipark_shared.eventos import MovimientoEvento
from canipark_shared.kafka import crear_consumidor, crear_productor, consumir_bucle, publicar_json

from .config import ConfigDisponibilidad
from .dominio import GestorDisponibilidad

logger = logging.getLogger(__name__)


class WorkerDisponibilidad:
    def __init__(self, config: ConfigDisponibilidad, gestor: GestorDisponibilidad) -> None:
        self.config = config
        self.gestor = gestor
        self._detener = threading.Event()
        self._hilo: threading.Thread | None = None
        self._productor: Any = None

    @property
    def activo(self) -> bool:
        return bool(self._hilo and self._hilo.is_alive())

    def iniciar(self) -> None:
        if not self.config.kafka_enabled or self.activo:
            return
        self._detener.clear()
        self._hilo = threading.Thread(
            target=self._ejecutar,
            name="kafka-disponibilidad",
            daemon=True,
        )
        self._hilo.start()

    def detener(self) -> None:
        self._detener.set()
        if self._hilo and self._hilo.is_alive():
            self._hilo.join(timeout=5)

    def _ejecutar(self) -> None:
        logger.info("Worker de Disponibilidad iniciado")
        while not self._detener.is_set():
            consumidor = None
            try:
                consumidor = crear_consumidor(
                    self.config.kafka_bootstrap_servers,
                    "can-i-park-disponibilidad",
                    self.config.topic_movimientos,
                )
                self._productor = crear_productor(self.config.kafka_bootstrap_servers)
                consumir_bucle(consumidor, self._procesar_payload, self._detener.is_set)
            except Exception:
                if not self._detener.is_set():
                    logger.exception("El worker de Disponibilidad se reconectará a Kafka")
                    self._detener.wait(3)
            finally:
                if consumidor is not None:
                    consumidor.close()

        logger.info("Worker de Disponibilidad detenido")

    def _procesar_payload(self, payload: dict[str, Any]) -> None:
        evento = MovimientoEvento.model_validate(payload)
        resultado, cambio_estado = self.gestor.procesar(evento)

        logger.info(
            "Movimiento procesado: evento=%s placa=%s aceptado=%s estado=%s",
            resultado.evento_id,
            resultado.placa,
            resultado.aceptado,
            resultado.estado.value,
        )

        if cambio_estado is not None:
            publicar_json(
                self._productor,
                self.config.topic_estados,
                cambio_estado.model_dump(mode="json"),
                key="estacionamiento-principal",
            )
