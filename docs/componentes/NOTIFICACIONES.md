# Microservicio de Notificaciones

## Objetivo

El microservicio de Notificaciones recibe los cambios de estado generados por Disponibilidad y crea alertas cuando el estacionamiento se encuentra con pocos espacios o lleno.

Este servicio no calcula la disponibilidad ni controla los vehículos que entran o salen. Su responsabilidad comienza cuando Disponibilidad publica un cambio de estado en Kafka.

---

## Funcionamiento

Disponibilidad publica eventos en el topic:

```text
can-i-park.estados
```

Notificaciones consume estos eventos y revisa el estado recibido.

Los estados principales son:

- `DISPONIBLE`
- `POCOS_ESPACIOS`
- `LLENO`

Cuando el estado es `POCOS_ESPACIOS` o `LLENO`, el servicio genera una alerta.

Cuando el estado es `DISPONIBLE`, el evento se procesa pero no se genera una alerta, evitando notificaciones innecesarias.

---

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
      +--> genera alerta si corresponde
      |
      +--> guarda la alerta en el historial
```

---

## Gestor de notificaciones

La lógica principal se encuentra en:

```text
GestorNotificaciones
```

Este componente recibe un `EstadoEstacionamientoEvento` y determina si debe generar una alerta.

Si el estado es:

```text
POCOS_ESPACIOS
```

genera un mensaje indicando cuántos espacios permanecen disponibles.

Si el estado es:

```text
LLENO
```

genera una alerta indicando que ya no existen espacios disponibles.

Las alertas se almacenan en memoria en un historial limitado.

Por defecto se conservan hasta:

```text
100 alertas
```

Esto evita que el historial crezca de manera ilimitada durante la ejecución.

---

## Worker de Kafka

`WorkerNotificaciones` ejecuta el consumidor Kafka en segundo plano.

El worker:

- se conecta al topic `can-i-park.estados`;
- recibe los eventos publicados por Disponibilidad;
- valida cada evento mediante `EstadoEstacionamientoEvento`;
- envía el evento a `GestorNotificaciones`;
- intenta reconectarse si ocurre un fallo de conexión con Kafka.

El consumidor se ejecuta en un hilo independiente para que FastAPI pueda atender solicitudes HTTP al mismo tiempo.

---

## API HTTP

El microservicio expone dos endpoints principales.

### Estado del servicio

```http
GET /health
```

Permite comprobar que la API de Notificaciones está disponible.

Ejemplo de respuesta:

```json
{
  "status": "ok",
  "servicio": "notificaciones"
}
```

### Consultar alertas

```http
GET /alertas
```

Devuelve el historial de alertas generadas durante la ejecución.

Ejemplo:

```json
{
  "alertas": [
    {
      "estado": "POCOS_ESPACIOS",
      "disponibles": 2,
      "mensaje": "POCOS ESPACIOS: quedan 2 espacios disponibles.",
      "ocurrido_en": "2026-10-11T20:00:00"
    }
  ]
}
```

Las alertas más recientes se devuelven primero.

---

## Reutilización

Notificaciones reutiliza componentes definidos en:

```text
canipark_shared
```

Entre ellos:

```text
EstadoEstacionamiento
EstadoEstacionamientoEvento
crear_consumidor()
consumir_bucle()
```

Esto evita duplicar contratos y lógica de comunicación con Kafka.

El microservicio no importa código interno de Disponibilidad ni de Control de Acceso.

Su integración con el resto del sistema ocurre mediante eventos compartidos publicados en Kafka.

---

## Configuración

La configuración se obtiene mediante variables de entorno.

Entre los valores principales se encuentran:

```text
KAFKA_BOOTSTRAP_SERVERS
TOPIC_ESTADOS
KAFKA_ENABLED
```

Esto permite ejecutar el mismo servicio en diferentes entornos sin modificar el código.

---

## Contenerización

Notificaciones posee su propio `Dockerfile` y se ejecuta como un contenedor independiente.

Docker Compose se encarga de:

- construir el servicio;
- conectarlo con Kafka;
- configurar las variables necesarias;
- exponer su API;
- verificar su estado mediante healthcheck.

El servicio puede consultarse desde el host mediante:

```text
http://localhost:8003
```

Swagger está disponible en:

```text
http://localhost:8003/docs
```

---

## Pruebas

El microservicio participa en pruebas automatizadas y en el flujo E2E:

```text
Disponibilidad
      ↓
    Kafka
      ↓
Notificaciones
```

La validación final confirmó que Disponibilidad puede publicar cambios de estado en Kafka y que Notificaciones los consume correctamente para generar las alertas correspondientes.

---

## Responsabilidad dentro de la arquitectura

Notificaciones demuestra que la arquitectura puede extenderse agregando un nuevo consumidor sin modificar Control de Acceso.

Su responsabilidad se resume en:

```text
recibir cambio de estado
        ↓
evaluar condición
        ↓
generar alerta
        ↓
mantener historial
```

Esta separación mantiene el microservicio enfocado en una sola responsabilidad y reduce el acoplamiento con los demás componentes.
