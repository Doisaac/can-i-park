from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class TipoMovimiento(str, Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"


class EstadoEstacionamiento(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    POCOS_ESPACIOS = "POCOS_ESPACIOS"
    LLENO = "LLENO"


class MovimientoEntrada(BaseModel):
    placa: str = Field(min_length=3, max_length=12)
    tipo: TipoMovimiento

    @field_validator("placa", mode="before")
    @classmethod
    def normalizar_placa(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        # Se normaliza antes de validar la longitud para que los espacios
        # no permitan que una placa demasiado corta pase la validación.
        placa = "".join(value.upper().strip().split())
        permitidos = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")
        if placa and any(caracter not in permitidos for caracter in placa):
            raise ValueError("La placa solo puede contener letras, números y guion")
        return placa


class MovimientoEvento(MovimientoEntrada):
    evento_id: UUID = Field(default_factory=uuid4)
    ocurrido_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResultadoMovimiento(BaseModel):
    evento_id: UUID
    placa: str
    tipo: TipoMovimiento
    aceptado: bool
    motivo: str
    capacidad: int
    ocupados: int
    disponibles: int
    estado: EstadoEstacionamiento


class EstadoEstacionamientoEvento(BaseModel):
    evento_id: UUID = Field(default_factory=uuid4)
    ocurrido_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    capacidad: int
    ocupados: int
    disponibles: int
    estado: EstadoEstacionamiento
    estado_anterior: EstadoEstacionamiento | None = None
