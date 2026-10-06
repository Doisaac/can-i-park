from __future__ import annotations

from collections import deque
from threading import RLock
from uuid import UUID

from canipark_shared.eventos import (
    EstadoEstacionamiento,
    EstadoEstacionamientoEvento,
    MovimientoEvento,
    ResultadoMovimiento,
    TipoMovimiento,
)


class GestorDisponibilidad:
    def __init__(self, capacidad: int = 100, umbral_pocos_espacios: int = 10) -> None:
        if capacidad <= 0:
            raise ValueError("La capacidad debe ser mayor que cero")
        if not 0 <= umbral_pocos_espacios < capacidad:
            raise ValueError("El umbral debe estar entre 0 y capacidad - 1")

        self.capacidad = capacidad
        self.umbral_pocos_espacios = umbral_pocos_espacios
        self._vehiculos_dentro: set[str] = set()
        self._procesados: dict[UUID, ResultadoMovimiento] = {}
        self._orden_procesados: deque[UUID] = deque(maxlen=1000)
        self._lock = RLock()

    @property
    def ocupados(self) -> int:
        with self._lock:
            return len(self._vehiculos_dentro)

    @property
    def disponibles(self) -> int:
        with self._lock:
            return self.capacidad - len(self._vehiculos_dentro)

    def estado(self) -> EstadoEstacionamiento:
        with self._lock:
            return self._estado_sin_lock()

    def resumen(self) -> dict[str, int | str]:
        with self._lock:
            ocupados = len(self._vehiculos_dentro)
            disponibles = self.capacidad - ocupados
            return {
                "capacidad": self.capacidad,
                "ocupados": ocupados,
                "disponibles": disponibles,
                "estado": self._estado_sin_lock().value,
            }

    def vehiculos_dentro(self) -> list[str]:
        with self._lock:
            return sorted(self._vehiculos_dentro)

    def resultado_evento(self, evento_id: UUID) -> ResultadoMovimiento | None:
        with self._lock:
            return self._procesados.get(evento_id)

    def procesar(
        self,
        evento: MovimientoEvento,
    ) -> tuple[ResultadoMovimiento, EstadoEstacionamientoEvento | None]:
        with self._lock:
            previo = self._procesados.get(evento.evento_id)
            if previo is not None:
                return previo, None

            estado_anterior = self._estado_sin_lock()
            aceptado = False

            if evento.tipo == TipoMovimiento.ENTRADA:
                if evento.placa in self._vehiculos_dentro:
                    motivo = "El vehículo ya se encuentra dentro del estacionamiento"
                elif len(self._vehiculos_dentro) >= self.capacidad:
                    motivo = "El estacionamiento está lleno"
                else:
                    self._vehiculos_dentro.add(evento.placa)
                    aceptado = True
                    motivo = "Entrada registrada correctamente"
            else:
                if evento.placa not in self._vehiculos_dentro:
                    motivo = "El vehículo no se encuentra registrado dentro"
                else:
                    self._vehiculos_dentro.remove(evento.placa)
                    aceptado = True
                    motivo = "Salida registrada correctamente"

            ocupados = len(self._vehiculos_dentro)
            disponibles = self.capacidad - ocupados
            estado_actual = self._estado_sin_lock()

            resultado = ResultadoMovimiento(
                evento_id=evento.evento_id,
                placa=evento.placa,
                tipo=evento.tipo,
                aceptado=aceptado,
                motivo=motivo,
                capacidad=self.capacidad,
                ocupados=ocupados,
                disponibles=disponibles,
                estado=estado_actual,
            )
            self._guardar_resultado(resultado)

            cambio_estado = None
            if aceptado and estado_actual != estado_anterior:
                cambio_estado = EstadoEstacionamientoEvento(
                    capacidad=self.capacidad,
                    ocupados=ocupados,
                    disponibles=disponibles,
                    estado=estado_actual,
                    estado_anterior=estado_anterior,
                )

            return resultado, cambio_estado

    def _estado_sin_lock(self) -> EstadoEstacionamiento:
        disponibles = self.capacidad - len(self._vehiculos_dentro)
        if disponibles == 0:
            return EstadoEstacionamiento.LLENO
        if disponibles <= self.umbral_pocos_espacios:
            return EstadoEstacionamiento.POCOS_ESPACIOS
        return EstadoEstacionamiento.DISPONIBLE

    def _guardar_resultado(self, resultado: ResultadoMovimiento) -> None:
        if len(self._orden_procesados) == self._orden_procesados.maxlen:
            mas_antiguo = self._orden_procesados[0]
            self._procesados.pop(mas_antiguo, None)
        self._orden_procesados.append(resultado.evento_id)
        self._procesados[resultado.evento_id] = resultado
