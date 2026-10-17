from fastapi.testclient import TestClient

from disponibilidad_app.dominio import GestorDisponibilidad
from disponibilidad_app.main import crear_app


def test_consulta_disponibilidad_inicial() -> None:
    gestor = GestorDisponibilidad(capacidad=100, umbral_pocos_espacios=10)
    cliente = TestClient(crear_app(gestor=gestor, iniciar_kafka=False))

    respuesta = cliente.get("/disponibilidad")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "capacidad": 100,
        "ocupados": 0,
        "disponibles": 100,
        "estado": "DISPONIBLE",
    }


def test_evento_desconocido_retorna_404() -> None:
    gestor = GestorDisponibilidad(capacidad=100, umbral_pocos_espacios=10)
    cliente = TestClient(crear_app(gestor=gestor, iniciar_kafka=False))

    respuesta = cliente.get("/movimientos/00000000-0000-0000-0000-000000000001")

    assert respuesta.status_code == 404
