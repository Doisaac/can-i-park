# Decisiones de diseño

Este documento resume las principales decisiones técnicas tomadas durante el desarrollo de **Can I Park?** y las razones detrás de la arquitectura elegida.

---

## Python y FastAPI

Python fue autorizado para el desarrollo del proyecto. Se eligió FastAPI porque permite construir APIs pequeñas, genera Swagger automáticamente y se integra con Pydantic para validar contratos.

---

## Kafka para la comunicación entre microservicios

El Tema 6 requiere Kafka y, además, su uso permite desacoplar productores y consumidores.

Control de Acceso no necesita conocer la URL de Disponibilidad ni esperar a que finalice su procesamiento. Los servicios se comunican mediante eventos publicados en:

```text
can-i-park.movimientos
can-i-park.estados
```

---

## Tres microservicios independientes

Control de Acceso recibe los movimientos y Disponibilidad los procesa, cumpliendo el flujo mínimo requerido.

Notificaciones se agregó como un tercer microservicio para demostrar que pueden incorporarse nuevos consumidores sin modificar Control de Acceso.

---

## `shared` como componente reutilizable

Los contratos y utilidades comunes viven en `canipark_shared`.

Esto evita duplicar modelos, enumeraciones y lógica de comunicación con Kafka en cada microservicio, manteniendo un mismo contrato entre los componentes.

---

## Lógica de negocio separada del transporte

Los archivos `main.py` se concentran principalmente en HTTP y ciclo de vida.

`GestorDisponibilidad` contiene las reglas del estacionamiento, lo que permite probar el dominio sin levantar FastAPI ni Kafka.

---

## Inversión e inyección de dependencias

Control de Acceso depende de una abstracción con la operación `publicar(evento)` y no directamente de una implementación concreta de Kafka.

En producción se utiliza `PublicadorKafka`, mientras que en pruebas puede sustituirse por un publicador falso.

Esto reduce el acoplamiento y facilita las pruebas automatizadas.

---

## Patrones aplicados

La arquitectura utiliza **Publish/Subscribe** mediante Kafka: los productores publican eventos sin conocer directamente a los consumidores.

También aplica el modelo **Producer/Consumer**:

```text
Control de Acceso -> Kafka -> Disponibilidad
Disponibilidad -> Kafka -> Notificaciones
```

Estos patrones permiten mantener los servicios desacoplados y extender el sistema sin modificar componentes existentes.

---

## Bajo acoplamiento y alta cohesión

Cada microservicio posee una responsabilidad concreta:

- Control de Acceso: recibir movimientos.
- Disponibilidad: aplicar reglas del estacionamiento.
- Notificaciones: reaccionar a cambios de estado.

Los servicios no importan directamente el código interno de otros microservicios.

---

## Respuesta HTTP 202

`POST /movimientos` devuelve `202 Accepted` porque el movimiento fue recibido y publicado, pero su procesamiento termina posteriormente en Disponibilidad de forma asíncrona.

---

## `set` para vehículos dentro

Se utiliza un `set` para almacenar las placas presentes en el estacionamiento porque evita duplicados y permite verificar rápidamente si un vehículo ya se encuentra dentro.

---

## Idempotencia

Kafka puede reentregar mensajes. Disponibilidad conserva resultados recientes por `evento_id` para evitar aplicar dos veces el mismo movimiento.

Se mantienen hasta 1000 resultados recientes para evitar crecimiento ilimitado en memoria.

---

## Commit manual de offsets

El auto commit de Kafka está desactivado.

El offset se confirma después de procesar correctamente el mensaje, evitando marcarlo como atendido antes de aplicar la lógica de negocio.

---

## Estado en memoria

No se agregó una base de datos porque la persistencia no forma parte de los requisitos específicos del Tema 6.

La principal limitación es que el estado del estacionamiento se pierde al reiniciar Disponibilidad. Una versión productiva incorporaría persistencia.

---

## Worker en segundo plano

FastAPI atiende HTTP mientras un worker consume Kafka en un hilo `daemon`.

Para el alcance académico esta solución mantiene el diseño simple. En una versión de mayor escala, el consumidor podría ejecutarse como un proceso independiente.

---

## Interfaz con proxy Nginx

La interfaz no se conecta directamente con Kafka.

Nginx sirve los archivos estáticos y enruta:

```text
/api/acceso
/api/disponibilidad
/api/notificaciones
```

hacia los microservicios dentro de la red Docker.

Esto evita acoplar el frontend al broker y evita configuración CORS innecesaria.

---

## Notificaciones basadas en cambios de estado

Notificaciones consume `can-i-park.estados` y no todos los movimientos.

Disponibilidad publica en ese topic únicamente cuando cambia el estado general del estacionamiento, evitando generar alertas innecesarias.

---

## Contenedor auxiliar de pruebas

Las pruebas finales se ejecutan en un contenedor con Python 3.12 para evitar diferencias entre instalaciones locales.

El servicio `pruebas` no representa funcionalidad de negocio; existe únicamente para proporcionar un entorno reproducible de validación.

---

## Alcance académico

El proyecto prioriza demostrar:

```text
microservicios + Kafka + reutilización + modularidad + Docker + pruebas
```

No se implementaron reservas, pagos, autenticación, cámaras, reconocimiento de placas ni múltiples estacionamientos porque esas funciones no forman parte del alcance del Tema 6.
