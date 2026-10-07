from __future__ import annotations

import logging
from collections import deque
from threading import Lock

from canipark_shared.eventos import EstadoEstacionamiento, EstadoEstacionamientoEvento

logger = logging.getLogger(__name__)


class GestorNotificaciones:
    def __init__(self, max_alertas: int = 100) -> None:
        self._alertas: deque[dict[str, str | int]] = deque(maxlen=max_alertas)
        self._lock = Lock()

    def procesar(self, evento: EstadoEstacionamientoEvento) -> dict[str, str | int] | None:
        if evento.estado == EstadoEstacionamiento.POCOS_ESPACIOS:
            if evento.disponibles == 1:
                mensaje = "POCOS ESPACIOS: queda 1 espacio disponible."
            else:
                mensaje = f"POCOS ESPACIOS: quedan {evento.disponibles} espacios disponibles."
        elif evento.estado == EstadoEstacionamiento.LLENO:
            mensaje = "ESTACIONAMIENTO LLENO: no quedan espacios disponibles."
        else:
            return None

        alerta: dict[str, str | int] = {
            "estado": evento.estado.value,
            "disponibles": evento.disponibles,
            "mensaje": mensaje,
            "ocurrido_en": evento.ocurrido_en.isoformat(),
        }
        with self._lock:
            self._alertas.append(alerta)

        logger.info("Alerta generada: %s", mensaje)
        return alerta

    def listar(self) -> list[dict[str, str | int]]:
        with self._lock:
            return list(reversed(self._alertas))
