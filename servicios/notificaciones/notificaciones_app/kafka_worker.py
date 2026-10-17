from __future__ import annotations

import logging
import threading
from typing import Any

from canipark_shared.eventos import EstadoEstacionamientoEvento
from canipark_shared.kafka import crear_consumidor, consumir_bucle

from .config import ConfigNotificaciones
from .dominio import GestorNotificaciones

logger = logging.getLogger(__name__)


class WorkerNotificaciones:
    def __init__(self, config: ConfigNotificaciones, gestor: GestorNotificaciones) -> None:
        self.config = config
        self.gestor = gestor
        self._detener = threading.Event()
        self._hilo: threading.Thread | None = None

    @property
    def activo(self) -> bool:
        return bool(self._hilo and self._hilo.is_alive())

    def iniciar(self) -> None:
        if not self.config.kafka_enabled or self.activo:
            return
        self._detener.clear()
        self._hilo = threading.Thread(
            target=self._ejecutar,
            name="kafka-notificaciones",
            daemon=True,
        )
        self._hilo.start()

    def detener(self) -> None:
        self._detener.set()
        if self._hilo and self._hilo.is_alive():
            self._hilo.join(timeout=5)

    def _ejecutar(self) -> None:
        logger.info("Worker de Notificaciones iniciado")
        while not self._detener.is_set():
            consumidor = None
            try:
                consumidor = crear_consumidor(
                    self.config.kafka_bootstrap_servers,
                    "can-i-park-notificaciones",
                    self.config.topic_estados,
                )
                consumir_bucle(consumidor, self._procesar_payload, self._detener.is_set)
            except Exception:
                if not self._detener.is_set():
                    logger.exception("El worker de Notificaciones se reconectará a Kafka")
                    self._detener.wait(3)
            finally:
                if consumidor is not None:
                    consumidor.close()

        logger.info("Worker de Notificaciones detenido")

    def _procesar_payload(self, payload: dict[str, Any]) -> None:
        evento = EstadoEstacionamientoEvento.model_validate(payload)
        self.gestor.procesar(evento)