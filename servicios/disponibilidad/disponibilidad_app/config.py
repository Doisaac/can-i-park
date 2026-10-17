from __future__ import annotations

import os
from dataclasses import dataclass, field


def _kafka_habilitado() -> bool:
    return os.getenv("KAFKA_ENABLED", "true").lower() == "true"


@dataclass(frozen=True)
class ConfigDisponibilidad:
    kafka_bootstrap_servers: str = field(
        default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    )
    topic_movimientos: str = field(
        default_factory=lambda: os.getenv("TOPIC_MOVIMIENTOS", "can-i-park.movimientos")
    )
    topic_estados: str = field(
        default_factory=lambda: os.getenv("TOPIC_ESTADOS", "can-i-park.estados")
    )
    capacidad: int = field(
        default_factory=lambda: int(os.getenv("CAPACIDAD_ESTACIONAMIENTO", "100"))
    )
    umbral_pocos_espacios: int = field(
        default_factory=lambda: int(os.getenv("UMBRAL_POCOS_ESPACIOS", "10"))
    )
    kafka_enabled: bool = field(default_factory=_kafka_habilitado)
