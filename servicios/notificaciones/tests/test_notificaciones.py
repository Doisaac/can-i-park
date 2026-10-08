from canipark_shared.eventos import EstadoEstacionamiento, EstadoEstacionamientoEvento
from notificaciones_app.dominio import GestorNotificaciones


def test_generar_alerta_pocos_espacios() -> None:
    gestor = GestorNotificaciones()
    evento = EstadoEstacionamientoEvento(
        capacidad=3,
        ocupados=2,
        disponibles=1,
        estado=EstadoEstacionamiento.POCOS_ESPACIOS,
        estado_anterior=EstadoEstacionamiento.DISPONIBLE,
    )

    alerta = gestor.procesar(evento)

    assert alerta is not None
    assert alerta["estado"] == "POCOS_ESPACIOS"
    assert alerta["mensaje"] == "POCOS ESPACIOS: queda 1 espacio disponible."


def test_generar_alerta_lleno() -> None:
    gestor = GestorNotificaciones()
    evento = EstadoEstacionamientoEvento(
        capacidad=100,
        ocupados=100,
        disponibles=0,
        estado=EstadoEstacionamiento.LLENO,
        estado_anterior=EstadoEstacionamiento.POCOS_ESPACIOS,
    )

    alerta = gestor.procesar(evento)

    assert alerta is not None
    assert alerta["estado"] == "LLENO"


def test_no_alerta_cuando_hay_disponibilidad_normal() -> None:
    gestor = GestorNotificaciones()
    evento = EstadoEstacionamientoEvento(
        capacidad=100,
        ocupados=50,
        disponibles=50,
        estado=EstadoEstacionamiento.DISPONIBLE,
    )

    alerta = gestor.procesar(evento)

    assert alerta is None
    assert gestor.listar() == []
