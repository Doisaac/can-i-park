from uuid import uuid4

from canipark_shared.eventos import MovimientoEvento, TipoMovimiento
from disponibilidad_app.dominio import GestorDisponibilidad


def movimiento(placa: str, tipo: TipoMovimiento) -> MovimientoEvento:
    return MovimientoEvento(evento_id=uuid4(), placa=placa, tipo=tipo)


def test_entrada_y_salida_actualizan_disponibilidad() -> None:
    gestor = GestorDisponibilidad(capacidad=3, umbral_pocos_espacios=1)

    entrada, _ = gestor.procesar(movimiento("P123456", TipoMovimiento.ENTRADA))
    assert entrada.aceptado is True
    assert entrada.ocupados == 1
    assert entrada.disponibles == 2

    salida, _ = gestor.procesar(movimiento("P123456", TipoMovimiento.SALIDA))
    assert salida.aceptado is True
    assert salida.ocupados == 0
    assert salida.disponibles == 3


def test_no_permite_entrada_duplicada() -> None:
    gestor = GestorDisponibilidad(capacidad=3, umbral_pocos_espacios=1)
    gestor.procesar(movimiento("P123456", TipoMovimiento.ENTRADA))

    resultado, _ = gestor.procesar(movimiento("P123456", TipoMovimiento.ENTRADA))

    assert resultado.aceptado is False
    assert resultado.ocupados == 1
    assert "ya se encuentra dentro" in resultado.motivo


def test_no_permite_salida_de_vehiculo_inexistente() -> None:
    gestor = GestorDisponibilidad(capacidad=3, umbral_pocos_espacios=1)

    resultado, _ = gestor.procesar(movimiento("P999999", TipoMovimiento.SALIDA))

    assert resultado.aceptado is False
    assert resultado.ocupados == 0


def test_no_supera_la_capacidad() -> None:
    gestor = GestorDisponibilidad(capacidad=1, umbral_pocos_espacios=0)
    gestor.procesar(movimiento("P111111", TipoMovimiento.ENTRADA))

    resultado, _ = gestor.procesar(movimiento("P222222", TipoMovimiento.ENTRADA))

    assert resultado.aceptado is False
    assert resultado.ocupados == 1
    assert resultado.disponibles == 0


def test_cambia_a_pocos_espacios_y_lleno() -> None:
    gestor = GestorDisponibilidad(capacidad=2, umbral_pocos_espacios=1)

    primero, cambio_1 = gestor.procesar(movimiento("P111111", TipoMovimiento.ENTRADA))
    segundo, cambio_2 = gestor.procesar(movimiento("P222222", TipoMovimiento.ENTRADA))

    assert primero.estado.value == "POCOS_ESPACIOS"
    assert cambio_1 is not None
    assert cambio_1.estado.value == "POCOS_ESPACIOS"
    assert segundo.estado.value == "LLENO"
    assert cambio_2 is not None
    assert cambio_2.estado.value == "LLENO"


def test_evento_repetido_es_idempotente() -> None:
    gestor = GestorDisponibilidad(capacidad=3, umbral_pocos_espacios=1)
    evento = movimiento("P123456", TipoMovimiento.ENTRADA)

    primera, _ = gestor.procesar(evento)
    segunda, cambio = gestor.procesar(evento)

    assert primera == segunda
    assert gestor.resumen()["ocupados"] == 1
    assert cambio is None
