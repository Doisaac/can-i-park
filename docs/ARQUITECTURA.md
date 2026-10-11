# Arquitectura de Can I Park?

## Objetivo

Can I Park? mantiene la disponibilidad actual de un estacionamiento a partir de eventos de entrada y salida. El punto central del diseño no es la resta de espacios, sino la separación entre recepción, transporte y procesamiento.

## Componentes

### Control de Acceso

Expone `POST /movimientos`. Valida la forma del dato, crea un evento y lo publica en Kafka. No conoce la capacidad, las placas que están dentro ni las reglas de disponibilidad.

### Kafka

Funciona como broker de eventos. Acceso publica en `can-i-park.movimientos` y Disponibilidad consume ese topic. De esta forma los servicios no necesitan una llamada HTTP directa entre ellos.

### Disponibilidad

Es el dueño de las reglas de negocio. Mantiene un `set` de placas, controla capacidad, calcula el estado y conserva resultados recientes por `evento_id` para idempotencia.

Expone:

- `GET /disponibilidad`
- `GET /vehiculos`
- `GET /movimientos/{evento_id}`
- `GET /health`

### Notificaciones

Es una extensión del núcleo mínimo del proyecto. En la entrega final se levanta junto con los demás servicios. Disponibilidad publica en `can-i-park.estados` únicamente cuando cambia la categoría del estacionamiento. Notificaciones consume ese topic y genera alertas para `POCOS_ESPACIOS` y `LLENO`.

### Interfaz

Es una capa de demostración servida con Nginx. Usa HTTP contra Acceso, Disponibilidad y Notificaciones a través de un proxy interno. No conoce el broker ni se conecta directamente a Kafka.

Para la defensa muestra el recorrido del evento de forma progresiva. La confirmación de Acceso proviene de la respuesta HTTP 202; el procesamiento de Disponibilidad se confirma consultando `GET /movimientos/{evento_id}`; y las alertas se obtienen realmente desde `GET /alertas`. Cuando no existe cambio de estado, la interfaz explica que no se publica un segundo evento en `can-i-park.estados`.

## Flujo principal

```text
Interfaz / Swagger
        |
        | POST /movimientos
        v
Control de Acceso
        |
        | MovimientoEvento
        v
Kafka: can-i-park.movimientos
        |
        v
Disponibilidad
        |
        +--> estado y consultas HTTP
        |
        +--> EstadoEstacionamientoEvento
             (solo cuando cambia el estado)
                    |
                    v
             Kafka: can-i-park.estados
                    |
                    v
             Notificaciones
```

## Reutilización

`shared/canipark_shared` evita duplicar los contratos de eventos y las funciones básicas de mensajería. El paquete puede instalarse dentro de cada contenedor y funciona como vocabulario común entre productor y consumidores.

## Consistencia e idempotencia

Acceso responde 202 porque aceptar el movimiento no significa que ya fue procesado. El evento debe viajar por Kafka y ser consumido.

Disponibilidad guarda el resultado de cada `evento_id` reciente. Si Kafka vuelve a entregar el mismo evento, se devuelve el resultado anterior y no se aplica otra vez.

El productor también usa `enable.idempotence=True`, pero esa protección pertenece a la publicación Kafka; la idempotencia del dominio se resuelve con `evento_id`.

## Concurrencia

Disponibilidad usa `RLock` para proteger sus estructuras en memoria porque el worker Kafka y las consultas HTTP pueden ejecutarse desde hilos diferentes.

## Recuperación básica del worker

Si el consumo falla de forma inesperada, el worker registra el error, cierra el consumidor y vuelve a intentar la conexión después de una pausa corta. Los offsets se confirman después de procesar el mensaje.

## Persistencia

El estado está en memoria por alcance académico. Reiniciar Disponibilidad vacía placas y resultados. Una evolución natural sería persistir estado e idempotency keys o reconstruir el estado a partir de eventos.

### Alertas activas e historial

El microservicio de Notificaciones conserva un historial en memoria limitado a 100 alertas. La interfaz no elimina ese historial: muestra como máximo las 2 alertas más recientes mientras el estado sea `POCOS_ESPACIOS` o `LLENO`. Cuando el estacionamiento vuelve a `DISPONIBLE`, la pantalla muestra `Sin alertas activas`, aunque el historial siga disponible mediante `GET /alertas`.
