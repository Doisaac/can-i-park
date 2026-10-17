from fastapi.testclient import TestClient

from acceso_app.main import crear_app as crear_app_acceso, obtener_publicador
from disponibilidad_app.dominio import GestorDisponibilidad
from disponibilidad_app.main import crear_app as crear_app_disponibilidad


class BusEnMemoria:
    def __init__(self, gestor: GestorDisponibilidad) -> None:
        self.gestor = gestor
        self.eventos = []

    def publicar(self, evento) -> None:
        self.eventos.append(evento)
        self.gestor.procesar(evento)


def test_flujo_entrada_desde_acceso_hasta_disponibilidad() -> None:
    gestor = GestorDisponibilidad(capacidad=100, umbral_pocos_espacios=10)
    bus = BusEnMemoria(gestor)

    app_acceso = crear_app_acceso()
    app_acceso.dependency_overrides[obtener_publicador] = lambda: bus
    cliente_acceso = TestClient(app_acceso)
    cliente_disponibilidad = TestClient(
        crear_app_disponibilidad(gestor=gestor, iniciar_kafka=False)
    )

    respuesta = cliente_acceso.post(
        "/movimientos",
        json={"placa": "P123456", "tipo": "ENTRADA"},
    )
    disponibilidad = cliente_disponibilidad.get("/disponibilidad")

    assert respuesta.status_code == 202
    assert disponibilidad.status_code == 200
    assert disponibilidad.json()["ocupados"] == 1
    assert disponibilidad.json()["disponibles"] == 99


def test_flujo_entrada_y_salida_completo() -> None:
    gestor = GestorDisponibilidad(capacidad=100, umbral_pocos_espacios=10)
    bus = BusEnMemoria(gestor)
    app_acceso = crear_app_acceso()
    app_acceso.dependency_overrides[obtener_publicador] = lambda: bus
    cliente = TestClient(app_acceso)

    assert cliente.post("/movimientos", json={"placa": "P123456", "tipo": "ENTRADA"}).status_code == 202
    assert gestor.resumen()["ocupados"] == 1

    assert cliente.post("/movimientos", json={"placa": "P123456", "tipo": "SALIDA"}).status_code == 202
    assert gestor.resumen()["ocupados"] == 0
    assert gestor.resumen()["disponibles"] == 100
