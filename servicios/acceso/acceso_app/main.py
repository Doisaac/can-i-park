from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, status

from canipark_shared.eventos import MovimientoEntrada, MovimientoEvento

from .config import ConfigAcceso
from .productor import PublicadorKafka, PublicadorMovimientos

logger = logging.getLogger(__name__)

_config = ConfigAcceso()
_publicador: PublicadorMovimientos | None = None


def obtener_publicador() -> PublicadorMovimientos:
    global _publicador
    if _publicador is None:
        _publicador = PublicadorKafka(_config)
    return _publicador


def crear_app() -> FastAPI:
    app = FastAPI(
        title="Can I Park? - Control de Acceso",
        version="1.1.0",
        description="Recibe entradas y salidas y publica los movimientos en Kafka.",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "servicio": "control-acceso"}

    @app.post("/movimientos", status_code=status.HTTP_202_ACCEPTED)
    def registrar_movimiento(
        entrada: MovimientoEntrada,
        publicador: PublicadorMovimientos = Depends(obtener_publicador),
    ) -> dict[str, str]:
        evento = MovimientoEvento(**entrada.model_dump())
        try:
            publicador.publicar(evento)
        except Exception as exc:
            logger.exception("No fue posible publicar el movimiento %s", evento.evento_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No fue posible publicar el movimiento en Kafka",
            ) from exc

        logger.info(
            "Movimiento aceptado: evento=%s placa=%s tipo=%s",
            evento.evento_id,
            evento.placa,
            evento.tipo.value,
        )
        return {
            "mensaje": "Movimiento recibido y enviado para procesamiento",
            "evento_id": str(evento.evento_id),
            "placa": evento.placa,
            "tipo": evento.tipo.value,
        }

    return app


app = crear_app()
