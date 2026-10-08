import json

import pytest

from canipark_shared.kafka import consumir_bucle, publicar_json


class ProductorExitoso:
    def __init__(self) -> None:
        self.mensaje = None
        self.callback = None

    def produce(self, **kwargs) -> None:
        self.mensaje = kwargs
        self.callback = kwargs["on_delivery"]

    def flush(self, timeout: float) -> int:
        self.callback(None, object())
        return 0


class ProductorConPendientes(ProductorExitoso):
    def flush(self, timeout: float) -> int:
        return 1


class ProductorConError(ProductorExitoso):
    def flush(self, timeout: float) -> int:
        self.callback("broker no disponible", object())
        return 0


class MensajeFalso:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def error(self):
        return None

    def value(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class ConsumidorFalso:
    def __init__(self, payload: dict) -> None:
        self.mensaje = MensajeFalso(payload)
        self.commits = 0

    def poll(self, timeout: float):
        return self.mensaje

    def commit(self, message, asynchronous: bool) -> None:
        self.commits += 1


def test_publicar_json_serializa_y_confirma_entrega() -> None:
    productor = ProductorExitoso()

    publicar_json(productor, "movimientos", {"placa": "P123456"}, key="P123456")

    assert productor.mensaje["topic"] == "movimientos"
    assert productor.mensaje["key"] == b"P123456"
    assert json.loads(productor.mensaje["value"].decode("utf-8")) == {"placa": "P123456"}


def test_publicar_json_falla_si_quedan_mensajes_pendientes() -> None:
    with pytest.raises(RuntimeError, match="no confirmó la entrega"):
        publicar_json(ProductorConPendientes(), "movimientos", {"placa": "P123456"})


def test_publicar_json_falla_si_kafka_reporta_error() -> None:
    with pytest.raises(RuntimeError, match="error de entrega"):
        publicar_json(ProductorConError(), "movimientos", {"placa": "P123456"})


def test_consumidor_confirma_offset_despues_de_procesar() -> None:
    consumidor = ConsumidorFalso({"dato": 1})
    procesado = False

    def procesar(payload: dict) -> None:
        nonlocal procesado
        assert payload == {"dato": 1}
        procesado = True

    consumir_bucle(consumidor, procesar, lambda: procesado)

    assert consumidor.commits == 1


def test_consumidor_no_confirma_offset_si_procesamiento_falla() -> None:
    consumidor = ConsumidorFalso({"dato": 1})

    def procesar(_: dict) -> None:
        raise RuntimeError("fallo de dominio")

    with pytest.raises(RuntimeError, match="fallo de dominio"):
        consumir_bucle(consumidor, procesar, lambda: False)

    assert consumidor.commits == 0
