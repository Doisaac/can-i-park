# Estrategia de pruebas

Can I Park? separa dos niveles de validación: pruebas rápidas sin broker y pruebas E2E contra Kafka real.

## Pruebas automatizadas sin Docker

`pytest` cubre:

- API de Control de Acceso;
- normalización y longitud de placas después de normalizar;
- respuesta 422 para entradas inválidas;
- respuesta 503 cuando el publicador falla;
- serialización y confirmación de entrega en la utilidad Kafka;
- rechazo cuando `flush` deja mensajes pendientes;
- error de entrega reportado por el productor;
- commit del consumidor solo después de procesar;
- ausencia de commit cuando falla la lógica;
- lectura de variables de entorno;
- entrada y salida;
- entrada duplicada;
- salida inexistente;
- capacidad máxima;
- transiciones de estado;
- idempotencia;
- API de Disponibilidad;
- alertas;
- flujo integrado Acceso -> Disponibilidad con bus en memoria.

Ejecutar:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

También se valida sintaxis:

```bash
python -m compileall -q .
```

## Por qué las pruebas unitarias no levantan Kafka

La lógica se desacopla del broker para que las pruebas sean rápidas y deterministas. Un publicador falso y un bus en memoria permiten comprobar contratos y dominio sin depender de Docker.

Eso no sustituye la prueba del broker real. Por eso el proyecto incorpora pruebas E2E separadas.

## E2E real del flujo principal

Con Docker levantado:

```bash
python scripts/test_e2e.py
```

La prueba:

1. comprueba las APIs;
2. registra una placa única;
3. obtiene el `evento_id`;
4. espera consultando `GET /movimientos/{evento_id}`;
5. valida que aumentó la ocupación;
6. registra la salida;
7. comprueba que el estado volvió al inicial;
8. guarda `docs/EVIDENCIA_E2E.txt`.

No usa un `sleep` fijo para asumir que Kafka terminó.

## E2E real de Notificaciones

La validación completa levanta capacidad 3 y umbral 1 para provocar una transición rápidamente:

```bash
python scripts/test_notificaciones_e2e.py
```

Comprueba el flujo:

```text
Disponibilidad -> Kafka -> Notificaciones
```

y guarda `docs/EVIDENCIA_NOTIFICACIONES_E2E.txt`.

## Validación completa recomendada

Windows:

```powershell
.\scripts\validar_entrega.ps1
```

Linux/macOS:

```bash
./scripts/validar_entrega.sh
```

Estos scripts levantan un entorno limpio, ejecutan las pruebas E2E y comprueban la interfaz. Deben ejecutarse en la computadora del equipo con Docker disponible antes de entregar.


## Entorno reproducible de pruebas

La validación final no usa el Python del sistema operativo. `tests/Dockerfile` define un entorno con Python 3.12, instala las dependencias de desarrollo y el paquete `canipark_shared`, y ejecuta las pruebas dentro de Docker.

El servicio `pruebas` usa el perfil `tools`: no es un cuarto microservicio y no participa en el funcionamiento normal de Can I Park?. Solo existe mientras se ejecutan validaciones.

Los scripts E2E conservan sus URLs `localhost` para ejecución manual, pero también aceptan variables de entorno. Dentro de Docker usan los nombres de servicio de Compose (`acceso`, `disponibilidad`, `notificaciones` e `interfaz`).
