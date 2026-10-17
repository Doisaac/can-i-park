from fastapi.testclient import TestClient

from acceso_app.main import crear_app, obtener_publicador


class PublicadorFalso:
    def __init__(self) -> None:
        self.eventos = []

    def publicar(self, evento) -> None:
        self.eventos.append(evento)


class PublicadorConError:
    def publicar(self, evento) -> None:
        raise RuntimeError("Kafka no disponible")


def crear_cliente(publicador):
    app = crear_app()
    app.dependency_overrides[obtener_publicador] = lambda: publicador
    return TestClient(app)


def test_registra_y_publica_movimiento() -> None:
    publicador = PublicadorFalso()
    cliente = crear_cliente(publicador)

    respuesta = cliente.post(
        "/movimientos",
        json={"placa": "p123456", "tipo": "ENTRADA"},
    )

    assert respuesta.status_code == 202
    assert respuesta.json()["placa"] == "P123456"
    assert len(publicador.eventos) == 1
    assert publicador.eventos[0].tipo.value == "ENTRADA"


def test_rechaza_placa_con_caracteres_invalidos() -> None:
    publicador = PublicadorFalso()
    cliente = crear_cliente(publicador)

    respuesta = cliente.post(
        "/movimientos",
        json={"placa": "P12@34", "tipo": "ENTRADA"},
    )

    assert respuesta.status_code == 422
    assert publicador.eventos == []


def test_valida_longitud_despues_de_normalizar_placa() -> None:
    publicador = PublicadorFalso()
    cliente = crear_cliente(publicador)

    respuesta = cliente.post(
        "/movimientos",
        json={"placa": " P1 ", "tipo": "ENTRADA"},
    )

    assert respuesta.status_code == 422
    assert publicador.eventos == []


def test_elimina_espacios_y_normaliza_a_mayusculas() -> None:
    publicador = PublicadorFalso()
    cliente = crear_cliente(publicador)

    respuesta = cliente.post(
        "/movimientos",
        json={"placa": " p 123 456 ", "tipo": "ENTRADA"},
    )

    assert respuesta.status_code == 202
    assert respuesta.json()["placa"] == "P123456"


def test_responde_503_si_no_puede_publicar_en_kafka() -> None:
    cliente = crear_cliente(PublicadorConError())

    respuesta = cliente.post(
        "/movimientos",
        json={"placa": "P123456", "tipo": "ENTRADA"},
    )

    assert respuesta.status_code == 503
    assert respuesta.json()["detail"] == "No fue posible publicar el movimiento en Kafka"
