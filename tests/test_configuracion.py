from acceso_app.config import ConfigAcceso
from disponibilidad_app.config import ConfigDisponibilidad
from notificaciones_app.config import ConfigNotificaciones


def test_config_acceso_lee_variables_al_crear_instancia(monkeypatch) -> None:
    monkeypatch.setenv("TOPIC_MOVIMIENTOS", "prueba.movimientos")
    monkeypatch.setenv("KAFKA_ENABLED", "false")

    config = ConfigAcceso()

    assert config.topic_movimientos == "prueba.movimientos"
    assert config.kafka_enabled is False


def test_config_disponibilidad_lee_capacidad_y_umbral(monkeypatch) -> None:
    monkeypatch.setenv("CAPACIDAD_ESTACIONAMIENTO", "25")
    monkeypatch.setenv("UMBRAL_POCOS_ESPACIOS", "4")

    config = ConfigDisponibilidad()

    assert config.capacidad == 25
    assert config.umbral_pocos_espacios == 4


def test_config_notificaciones_lee_topic(monkeypatch) -> None:
    monkeypatch.setenv("TOPIC_ESTADOS", "prueba.estados")

    config = ConfigNotificaciones()

    assert config.topic_estados == "prueba.estados"
