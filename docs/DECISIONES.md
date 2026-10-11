# Decisiones de diseño

Este documento resume por qué se eligieron las piezas principales del proyecto.

## Python y FastAPI

Python fue autorizado para el proyecto. FastAPI permite mantener cada API pequeña, genera Swagger automáticamente y se integra de forma directa con Pydantic para validar contratos.

## Kafka en lugar de una llamada HTTP entre microservicios

El Tema 6 requiere Kafka y, además, el broker permite desacoplar al productor del consumidor. Control de Acceso no necesita conocer la URL de Disponibilidad ni esperar a que termine su procesamiento.

## Dos microservicios principales y un tercero de extensión

Acceso y Disponibilidad forman el flujo mínimo requerido: uno recibe datos y otro los procesa. Notificaciones se implementó como un tercer microservicio para demostrar que un consumidor adicional puede incorporarse sin modificar Control de Acceso. En la entrega final los tres servicios se levantan juntos con Docker Compose.

## `shared` como componente reutilizable

Los contratos y utilidades comunes viven en `canipark_shared`. Esto evita copiar enums, modelos Pydantic y código de serialización en cada microservicio.

## Lógica de negocio fuera de `main.py`

`main.py` se limita principalmente al transporte HTTP y ciclo de vida. `GestorDisponibilidad` concentra las reglas para poder probarlas sin levantar FastAPI ni Kafka.

## `Protocol` para el publicador de movimientos

Control de Acceso depende de la forma `publicar(evento)`, no de una instancia concreta de Kafka. En producción se usa `PublicadorKafka`; en pruebas se sustituye por un publicador falso. Es una aplicación sencilla de inversión de dependencias.

## Respuesta HTTP 202

`POST /movimientos` devuelve 202 porque la solicitud fue aceptada y publicada para procesamiento, pero Disponibilidad termina el trabajo de forma asíncrona.

## `set` para vehículos dentro

El dominio necesita saber si una placa ya está dentro. Un `set` evita duplicados y permite búsquedas rápidas sin mantener solamente un contador que podría perder consistencia.

## Idempotencia

Kafka puede reentregar un mensaje. Disponibilidad conserva resultados recientes por `evento_id` y no aplica dos veces el mismo evento. Se guardan hasta 1000 resultados para evitar crecimiento ilimitado en memoria.

## Commit manual del consumidor

El auto commit está desactivado. El offset se confirma después de procesar correctamente el mensaje, evitando marcarlo como atendido antes de aplicar la lógica.

## Estado en memoria

No se agregó base de datos porque no forma parte del requisito del Tema 6 y habría desviado el alcance. La limitación está documentada y una versión productiva incorporaría persistencia.

## Hilo de fondo

FastAPI atiende HTTP mientras el worker consume Kafka. Para este alcance se utiliza un hilo daemon. Si el proyecto creciera, el consumidor podría separarse en un proceso dedicado.

## Interfaz con proxy Nginx

La interfaz no habla con Kafka. Nginx sirve los archivos estáticos y enruta `/api/acceso` y `/api/disponibilidad` hacia los microservicios dentro de la red de Docker. Esto evita acoplar el frontend al broker y también evita configuración CORS innecesaria.

## Comentarios en el código

Se dejaron comentarios únicamente donde una decisión no resulta evidente a simple vista, por ejemplo el orden de validación de la placa o el motivo de no confirmar un offset cuando falla el procesamiento. La intención es mantener el código legible sin llenarlo de explicaciones redundantes.


## Contenedor auxiliar de pruebas

Para evitar diferencias entre instalaciones locales de Python, las pruebas finales se ejecutan en un contenedor basado en Python 3.12. Este contenedor no representa funcionalidad de negocio y no se considera un microservicio; se crea únicamente para ejecutar validaciones de forma reproducible y se elimina al terminar.
