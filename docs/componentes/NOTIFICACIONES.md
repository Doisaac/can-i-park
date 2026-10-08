# Microservicio de Notificaciones

## Objetivo

El microservicio de Notificaciones se encarga de recibir los cambios de estado generados por el microservicio de Disponibilidad y crear alertas cuando el estacionamiento se encuentra con pocos espacios o lleno.

Este servicio no calcula la disponibilidad ni controla los vehículos que entran o salen. Su función comienza cuando Disponibilidad publica un cambio de estado en Kafka.

## Funcionamiento

Disponibilidad publica eventos en el topic:

`can-i-park.estados`

Notificaciones consume esos eventos y revisa el estado recibido.

Los estados principales que procesa son:

- `DISPONIBLE`
- `POCOS_ESPACIOS`
- `LLENO`

Cuando el estado es `POCOS_ESPACIOS` o `LLENO`, el servicio genera una alerta.

Cuando el estacionamiento vuelve a `DISPONIBLE`, el servicio recibe el nuevo estado y lo procesa normalmente.

## Flujo de Notificaciones

```text
Disponibilidad
      |
      | EstadoEstacionamientoEvento
      v
Kafka: can-i-park.estados
      |
      v
Notificaciones
      |
      +--> procesa el estado
      |
      +--> genera alerta
      |
      +--> guarda la alerta en el historial