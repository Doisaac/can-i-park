# Can I Park? — Microservicios con Kafka en Python

Can I Park? es un proyecto académico que mantiene actualizada la disponibilidad de un estacionamiento a partir de movimientos de entrada y salida. La solución separa la recepción de datos de su procesamiento y utiliza **Apache Kafka** como intermediario asíncrono entre microservicios.

## Arquitectura

```text
Interfaz / Swagger
        |
        | HTTP
        v
[ Control de Acceso ]
        |
        | can-i-park.movimientos
        v
[       Kafka       ]
        |
        v
[  Disponibilidad  ] -----> GET /disponibilidad
        |
        | can-i-park.estados
        v
[ Notificaciones ]
```

La interfaz solo consume las APIs HTTP. No se conecta directamente con Kafka.

En escritorio utiliza una **vista compacta de exposición** para mantener visibles movimiento, disponibilidad, recorrido, vehículos y alertas sin desplazamiento en resoluciones comunes. Durante la demostración muestra un **recorrido visual paso a paso** del movimiento: Control de Acceso, creación del UUID, publicación en `can-i-park.movimientos`, procesamiento en Disponibilidad y comportamiento de Notificaciones. Los estados cambian visualmente entre pendiente, procesando, confirmado, rechazado, alerta, sin evento o error. También consulta `GET /alertas` para mostrar las alertas reales generadas por el tercer microservicio. La interfaz muestra como máximo las **2 alertas más recientes** cuando existe una condición activa; si el estacionamiento vuelve a `DISPONIBLE`, muestra **Sin alertas activas**. El microservicio conserva internamente un historial limitado de hasta 100 alertas para trazabilidad. Las alertas `POCOS_ESPACIOS` se presentan en ámbar y `LLENO` en rojo para diferenciar claramente advertencia y condición crítica durante la demostración.

## Tecnologías

- Python 3.12 en los contenedores
- FastAPI y Pydantic
- Apache Kafka 3.9 en modo KRaft
- `confluent-kafka`
- Docker y Docker Compose
- Nginx para la interfaz de demostración
- pytest

## Estructura

```text
Can-I-Park/
├── docker-compose.yml
├── README.md
├── shared/
│   └── canipark_shared/
├── servicios/
│   ├── acceso/
│   ├── disponibilidad/
│   └── notificaciones/
├── interfaz/
├── tests/
├── docs/
└── scripts/
```

`shared` es un paquete reutilizable con contratos de eventos y utilidades Kafka. Cada microservicio conserva su responsabilidad y su Dockerfile.

## Ejecutar el proyecto

Requisito: Docker Desktop o Docker Engine con Docker Compose.

```bash
docker compose up --build
```

Servicios:

- Interfaz: `http://localhost:8080`
- Control de Acceso: `http://localhost:8001`
- Disponibilidad: `http://localhost:8002`
- Kafka: `localhost:9092` desde el host
- Notificaciones: `http://localhost:8003`

Swagger:

- `http://localhost:8001/docs`
- `http://localhost:8002/docs`

Los tres microservicios, Kafka y la interfaz se levantan juntos con el mismo comando.

Swagger de Notificaciones: `http://localhost:8003/docs`.

## Flujo de un movimiento

1. El cliente envía `placa` y `tipo` a `POST /movimientos`.
2. Pydantic normaliza y valida la entrada.
3. Acceso crea un `MovimientoEvento` con UUID y fecha/hora.
4. Acceso publica el evento en `can-i-park.movimientos`.
5. Disponibilidad consume el evento y aplica las reglas.
6. `GET /movimientos/{evento_id}` permite comprobar cuándo terminó el procesamiento.
7. `GET /disponibilidad` muestra el estado resultante.
8. Si cambia la categoría del estacionamiento, Disponibilidad publica en `can-i-park.estados`.
9. Notificaciones consume ese cambio y genera una alerta cuando el nuevo estado es `POCOS_ESPACIOS` o `LLENO`.

`POST /movimientos` responde **202 Accepted** porque el procesamiento termina de forma asíncrona.

## Reglas principales

- No se supera la capacidad.
- Una placa no puede entrar dos veces sin salir.
- Una placa no puede salir si no está dentro.
- Una reentrega con el mismo `evento_id` no repite el efecto.
- Estados: `DISPONIBLE`, `POCOS_ESPACIOS` y `LLENO`.
- La placa acepta entre 3 y 12 caracteres después de normalizar espacios y mayúsculas.

Por defecto la capacidad es 100 y el umbral de pocos espacios es 10.

## Pruebas y validación

El método oficial de validación usa **Docker**, por lo que no depende de la versión de Python, `pip` o `pytest` instalada en la computadora de cada integrante.

En Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\validar_entrega.ps1
```

En Linux/macOS:

```bash
chmod +x scripts/validar_entrega.sh
./scripts/validar_entrega.sh
```

El validador crea un contenedor auxiliar llamado `pruebas` con Python 3.12 y las dependencias necesarias. Este contenedor **no es un microservicio** y no queda ejecutándose con el sistema.

La validación:

1. comprueba Docker;
2. construye el entorno reproducible de pruebas;
3. ejecuta `compileall` dentro de Docker;
4. ejecuta las pruebas automatizadas dentro de Docker;
5. levanta Kafka, Acceso, Disponibilidad, Notificaciones e Interfaz;
6. comprueba `Acceso -> Kafka -> Disponibilidad`;
7. comprueba `Disponibilidad -> Kafka -> Notificaciones`;
8. verifica la interfaz;
9. genera las evidencias E2E en `docs/`;
10. restaura la configuración normal de capacidad 100 y umbral 10.

Por lo tanto, para **ejecutar y validar la entrega no es obligatorio instalar Python localmente**. Docker proporciona Python 3.12 de forma consistente para todos los integrantes.

### Desarrollo local opcional

Si alguien desea ejecutar las pruebas directamente desde VS Code puede usar un entorno virtual e instalar:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

Esto queda como opción de desarrollo, no como requisito para validar la entrega.

## Configuración

Variables principales:

```env
TOPIC_MOVIMIENTOS=can-i-park.movimientos
TOPIC_ESTADOS=can-i-park.estados
CAPACIDAD_ESTACIONAMIENTO=100
UMBRAL_POCOS_ESPACIOS=10
KAFKA_ENABLED=true
```

Hay un ejemplo en `.env.example`.

## Documentación

- `docs/ARQUITECTURA.md`: componentes y flujo.
- `docs/DECISIONES.md`: decisiones técnicas y principios aplicados.
- `docs/PRUEBAS.md`: estrategia y escenarios de prueba.
- `docs/RESULTADO_PRUEBAS.md`: validaciones realizadas en el paquete.
- `docs/REVISION_RUBRICA.md`: correspondencia entre el proyecto y la rúbrica.

## Limitaciones conocidas

El estado del estacionamiento está en memoria. Si se reinicia Disponibilidad se pierde el estado actual. Para el alcance académico se prioriza demostrar microservicios, Kafka, Docker, modularidad y reutilización. Una versión de producción incorporaría persistencia, observabilidad más completa y una estrategia de mensajes fallidos (DLQ).

## Detener

```bash
docker compose down
```
A partir de estos movimientos, el sistema actualizará la cantidad de espacios ocupados y disponibles.
