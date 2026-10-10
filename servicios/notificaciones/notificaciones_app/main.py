from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import ConfigNotificaciones
from .dominio import GestorNotificaciones
from .kafka_worker import WorkerNotificaciones


def crear_app(
    gestor: GestorNotificaciones | None = None,
    iniciar_kafka: bool = True,
) -> FastAPI:
    config = ConfigNotificaciones()
    gestor = gestor or GestorNotificaciones()
    worker = WorkerNotificaciones(config, gestor)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if iniciar_kafka:
            worker.iniciar()
        try:
            yield
        finally:
            worker.detener()

    app = FastAPI(
        title="Can I Park? - Notificaciones",
        version="1.1.0",
        description="Tercer microservicio de Can I Park? que consume cambios de estado desde Kafka y genera alertas cuando quedan pocos espacios o el estacionamiento se llena.",
        lifespan=lifespan,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "servicio": "notificaciones"}

    @app.get("/alertas")
    def alertas() -> dict[str, list[dict[str, str | int]]]:
        return {"alertas": gestor.listar()}

    app.state.gestor = gestor
    app.state.worker = worker
    return app


app = crear_app()