from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, status

from canipark_shared.eventos import ResultadoMovimiento

from .config import ConfigDisponibilidad
from .dominio import GestorDisponibilidad
from .kafka_worker import WorkerDisponibilidad


def crear_app(
    gestor: GestorDisponibilidad | None = None,
    iniciar_kafka: bool = True,
) -> FastAPI:
    config = ConfigDisponibilidad()
    gestor = gestor or GestorDisponibilidad(config.capacidad, config.umbral_pocos_espacios)
    worker = WorkerDisponibilidad(config, gestor)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if iniciar_kafka:
            worker.iniciar()
        try:
            yield
        finally:
            worker.detener()

    app = FastAPI(
        title="Can I Park? - Disponibilidad",
        version="1.1.0",
        description="Procesa movimientos y mantiene el estado actual del estacionamiento.",
        lifespan=lifespan,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "servicio": "disponibilidad"}

    @app.get("/disponibilidad")
    def obtener_disponibilidad() -> dict[str, int | str]:
        return gestor.resumen()

    @app.get("/vehiculos")
    def obtener_vehiculos() -> dict[str, list[str]]:
        return {"vehiculos": gestor.vehiculos_dentro()}

    @app.get("/movimientos/{evento_id}", response_model=ResultadoMovimiento)
    def obtener_resultado(evento_id: UUID) -> ResultadoMovimiento:
        resultado = gestor.resultado_evento(evento_id)
        if resultado is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento no encontrado o todavía no procesado",
            )
        return resultado

    app.state.gestor = gestor
    app.state.worker = worker
    return app


app = crear_app()
