from __future__ import annotations

from typing import Protocol

from canipark_shared.eventos import MovimientoEvento
from canipark_shared.kafka import crear_productor, publicar_json

from .config import ConfigAcceso


class PublicadorMovimientos(Protocol):
    def publicar(self, evento: MovimientoEvento) -> None: ...


class PublicadorKafka:
    def __init__(self, config: ConfigAcceso) -> None:
        self.config = config
        self._productor = None

    def _obtener_productor(self):
        if self._productor is None:
            self._productor = crear_productor(self.config.kafka_bootstrap_servers)
        return self._productor

    def publicar(self, evento: MovimientoEvento) -> None:
        if not self.config.kafka_enabled:
            return
        publicar_json(
            self._obtener_productor(),
            self.config.topic_movimientos,
            evento.model_dump(mode="json"),
            key=evento.placa,
        )
