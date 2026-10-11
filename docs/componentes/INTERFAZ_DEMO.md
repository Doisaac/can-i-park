# Interfaz de Demostración y Proxy Nginx

## Propósito

La Interfaz de Demostración es la capa visual de Can I Park?.

Su función es servir como panel de control interactivo para **observar mediante HTTP** el recorrido completo del sistema distribuido: Control de Acceso recibe el dato y es este servicio el encargado de publicar los eventos a través de Kafka, Disponibilidad aplica las reglas de dominio y Notificaciones reacciona, sin que la interfaz se comunique directamente con el broker.

### Flujo general de interacción:

```text
Navegador (localhost:8080)
        ↓
Nginx Proxy (Contenedor - Puerto 80 interno)
        ├── /api/acceso/        → http://acceso:8000/
        ├── /api/disponibilidad/ → http://disponibilidad:8000/
        └── /api/notificaciones/ → http://notificaciones:8000/
```    

---

## Estructura

interfaz/
├── Dockerfile
├── nginx.conf
├── index.html
├── styles.css
└── app.js

scripts/
├── test_interfaz.py
├── demo.ps1
└── demo.sh

### Responsabilidad de los archivos

- Dockerfile: configura el contenedor basado en la imagen oficial de Nginx.
- nginx.conf: actúa como servidor estático y proxy inverso HTTP interno.
- index.html: estructura semántica del panel visual y sus secciones.
- styles.css: estilos CSS para barras, estados visuales y tarjetas.
- app.js: lógica de cliente HTTP, polling asíncrono, renderizado de estados y gestión de alertas.
- test_interfaz.py: prueba de humo (smoke test) para verificar la disponibilidad HTTP del panel.
- demo.ps1: script PowerShell para automatizar la ejecución de demostraciones en Windows.
- demo.sh: script equivalente en Bash para entornos Linux/macOS.

---

## Rol de Nginx como Proxy Inverso

Nginx resuelve dos problemas clave en la arquitectura:

1. Evita problemas de CORS: La aplicación web se sirve desde un único origen (localhost:8080). Todas las peticiones a la API usan rutas asociadas como /api/..., eliminando el bloqueo por políticas de mismo origen.
2. Resolución de nombres Docker: Mapea las peticiones HTTP externas hacia los nombres de servicio en la red de Docker Compose:
   - /api/acceso/ redirige a http://acceso:8000/
   - /api/disponibilidad/ redirige a http://disponibilidad:8000/
   - /api/notificaciones/ redirige a http://notificaciones:8000/

---

## Recorrido Visual del Evento

El panel visualiza el ciclo de vida del evento dividiendo el proceso en tarjetas interactivas:

[1. Control de Acceso] → [2. Evento Movimiento] → [3. Apache Kafka] → [4. Disponibilidad] → [5. Notificaciones]

### Significado de cada paso visual

1. Control de Acceso: Refleja la respuesta del POST /movimientos. Un estado HTTP 202 Accepted confirma la recepción y validación inicial del contrato.
2. Evento de Movimiento: Muestra el evento_id (UUID único) generado por Acceso.
3. Apache Kafka: Se marca como confirmado únicamente cuando Acceso valida la entrega en el topic can-i-park.movimientos.
4. Disponibilidad: Realiza polling continuo al endpoint GET /movimientos/{evento_id} hasta confirmar si la regla de negocio aceptó o rechazó el movimiento.
5. Notificaciones: Si el movimiento generó un cambio en la categoría del estacionamiento, Notificaciones consume can-i-park.estados y la UI despliega una alerta. Si no hubo cambio de categoría, la tarjeta indica SIN EVENTO.

---

## Polling HTTP y Consistencia Eventual

Debido a que la comunicación entre microservicios ocurre de forma asíncrona mediante Kafka, la respuesta 202 Accepted de Acceso no garantiza que Disponibilidad ya haya procesado el evento.

La interfaz gestiona esta consistencia eventual ejecutando polling en app.js:


```text
POST /movimientos
        ↓
HTTP 202 + evento_id
        ↓
Polling GET /movimientos/{evento_id}
   ├── HTTP 404 → "Todavía no procesado" (Reintenta)
   └── HTTP 200 → "Procesado" (Muestra ACEPTADO o RECHAZADO)

Si el evento no obtiene un 200 tras reintentar durante un tiempo límite, la UI marca el procesamiento con tiempo agotado o error.
```

---

## Estados Visuales y Barra de Ocupación

El panel muestra el estado del estacionamiento de forma intuitiva:

- DISPONIBLE: Sin alertas activas.
- POCOS_ESPACIOS: Indicador y barra en tono ámbar (disponibles <= umbral).
- LLENO: Indicador y barra en tono rojo (disponibles == 0).

### Manejo de Alertas Activas vs. Historial Interno

Es crucial diferenciar el comportamiento de la UI frente al almacenamiento del backend:

- Microservicio Notificaciones: Conserva en memoria un historial de hasta 100 alertas.
- Interfaz (UI): Muestra como máximo las 2 alertas más recientes únicamente mientras el estado actual sea POCOS_ESPACIOS o LLENO.

Cuando el estacionamiento regresa a DISPONIBLE, la UI muestra "Sin alertas activas" y limpia la vista activa sin borrar el historial almacenado en el microservicio. Esto evita saturar la pantalla durante una exposición.

---

## Funcionamiento Técnico de los Scripts de Demo (`demo.ps1` / `demo.sh`)

Los scripts de automatización (`demo.ps1` para PowerShell y `demo.sh` para sistemas Unix) ejecutan un flujo controlado paso a paso mediante llamadas HTTP directas a las APIs:

1. **Envío de Entrada:** Envía un `POST` con la placa de prueba (`P123456`) y tipo `ENTRADA` al microservicio de Control de Acceso (`http://localhost:8001/movimientos`).   
2. **Polling de Validación:** Captura el `evento_id` devuelto y consulta repetidamente al microservicio de Disponibilidad (`http://localhost:8002/movimientos/{evento_id}`) hasta obtener una respuesta `200 OK` (evitando errores `404` por la demora asíncrona del broker Kafka).   
3. **Consulta de Estado:** Consulta el endpoint `GET http://localhost:8002/disponibilidad` para verificar la ocupación actualizada.   
4. **Envío de Salida:** Registra un nuevo `POST` con la misma placa (`P123456`) y tipo `SALIDA`.
5. **Polling y Cierre:** Vuelve a aplicar *polling* sobre el nuevo `evento_id` y muestra el estado de disponibilidad final del estacionamiento.

---

## Lo que la Interfaz DEMUESTRA vs. lo que NO HACE

### La interfaz SÍ hace:
- Consultar los microservicios mediante peticiones HTTP.
- Mostrar la capacidad, ocupados, disponibles y lista de vehículos en tiempo real.
- Visualizar el flujo de eventos, rechazos de negocio y alertas.

### La interfaz NO hace:
- No se conecta directamente con Apache Kafka: La UI no es un productor ni consumidor de Kafka.
- No decide las reglas de negocio: No calcula la ocupación ni valida placas por su cuenta.
- No sustituye a las APIs: Es únicamente una capa de demostración sobre las llamadas HTTP a los microservicios.

---

## Pruebas de la Interfaz

La validación de la interfaz se realiza a través de scripts/test_interfaz.py:

- Comprueba que el servidor Nginx responda con código de estado HTTP 200 OK.
- Revisa que la estructura HTML y las dependencias estáticas se sirvan correctamente.

Se ejecuta aisladamente o como parte del flujo de validación del sistema.

---

## Puntos clave para defender

Durante la evaluación debes explicar:

- Por qué Nginx actúa como proxy inverso y cómo evita problemas de CORS.
- Qué significa que Acceso responda 202 Accepted y por qué la UI necesita hacer polling.
- La diferencia entre que "Kafka funcione" y que "el dominio acepte el movimiento" (ej. cuando la placa o el parqueo están llenos).
- Por qué la UI solo muestra hasta 2 alertas activas mientras el backend conserva 100 en su historial.
- Por qué la interfaz no publica ni consume mensajes de Kafka directamente.

---
