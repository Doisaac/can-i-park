# Microservicio Control de Acceso

## Propósito

El microservicio de **Control de Acceso** funciona como la puerta de entrada del flujo principal de **Can I Park?**.

Su responsabilidad es recibir una solicitud HTTP con la información de un movimiento, validar que el dato cumpla el contrato definido por el sistema, convertir la solicitud en un `MovimientoEvento` y publicarlo en Apache Kafka para que posteriormente sea procesado por el microservicio de Disponibilidad.

Control de Acceso no administra el estado interno del estacionamiento y tampoco decide si una entrada o salida debe ser aceptada por las reglas del dominio.

Su función puede resumirse de la siguiente manera:

```text
Solicitud HTTP
      ↓
Control de Acceso
      ↓
validación del contrato
      ↓
creación de MovimientoEvento
      ↓
publicación en Kafka
      ↓
respuesta HTTP
```

La implementación se encuentra principalmente en:

`servicios/acceso`

---

## Estructura del componente

El microservicio se organiza de la siguiente manera:

```text
servicios/
└── acceso/
    ├── Dockerfile
    ├── requirements.txt
    ├── acceso_app/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── productor.py
    │   └── main.py
    └── tests/
        └── test_api_acceso.py
```

Cada archivo tiene una responsabilidad específica:

- `Dockerfile`: define la imagen utilizada para ejecutar el microservicio.
- `requirements.txt`: contiene las dependencias propias del servicio.
- `acceso_app/__init__.py`: identifica `acceso_app` como paquete Python.
- `acceso_app/config.py`: centraliza la configuración utilizada por el servicio.
- `acceso_app/productor.py`: define la abstracción de publicación y su implementación basada en Kafka.
- `acceso_app/main.py`: contiene la aplicación FastAPI y sus endpoints.
- `tests/test_api_acceso.py`: contiene las pruebas automatizadas del contrato HTTP y comportamiento del servicio.

Esta distribución separa configuración, transporte, API y pruebas para evitar concentrar toda la responsabilidad en un único archivo.

---

## Responsabilidad dentro de Can I Park?

Control de Acceso representa el punto donde un movimiento entra al sistema.

Su responsabilidad principal es:

1. recibir los datos;
2. validar el contrato;
3. generar un evento identificable;
4. publicar el evento;
5. responder al cliente.

Conceptualmente:

```text
Usuario / Interfaz / Swagger
            ↓
    POST /movimientos
            ↓
     Control de Acceso
            ↓
    MovimientoEvento
            ↓
          Kafka
            ↓
can-i-park.movimientos
            ↓
     Disponibilidad
```

Control de Acceso no llama directamente al microservicio de Disponibilidad para procesar el movimiento.

La comunicación de negocio entre ambos servicios ocurre mediante Kafka.

Esto permite mantener los microservicios desacoplados.

---

## Lo que Control de Acceso sí conoce

Control de Acceso conoce información necesaria para recibir y publicar correctamente un movimiento.

Entre los elementos que utiliza se encuentran:

- placa del vehículo;
- tipo de movimiento;
- contratos compartidos;
- configuración de Kafka;
- topic de movimientos;
- mecanismo de publicación;
- identificador del evento;
- fecha y hora asociada al evento.

También conoce si la publicación hacia Kafka pudo confirmarse correctamente.

---

## Lo que Control de Acceso no conoce

Control de Acceso no debe contener las reglas globales del estacionamiento.

Por diseño, no conoce:

- cuántos vehículos están actualmente dentro;
- cuántos espacios están disponibles;
- la capacidad total como regla de decisión;
- si el estacionamiento está lleno;
- si una placa ya se encuentra dentro;
- si una salida corresponde a un vehículo existente;
- si un movimiento debe modificar la ocupación;
- el estado `DISPONIBLE`;
- el estado `POCOS_ESPACIOS`;
- el estado `LLENO`.

Estas responsabilidades pertenecen al microservicio de Disponibilidad.

La separación puede representarse así:

```text
Control de Acceso
        │
        │ recibe y publica
        ▼
      Kafka
        │
        ▼
Disponibilidad
        │
        │ aplica reglas
        ▼
 estado del parqueo
```

Esta decisión evita duplicar reglas de negocio en diferentes servicios.

---

## Contratos reutilizados desde `shared`

Control de Acceso reutiliza los contratos definidos en el paquete compartido:

`shared/canipark_shared`

Esto evita que el servicio cree una definición independiente de los movimientos.

Entre los contratos relevantes se encuentran:

- `TipoMovimiento`
- `MovimientoEntrada`
- `MovimientoEvento`

La relación conceptual es:

```text
shared
  │
  ├── TipoMovimiento
  ├── MovimientoEntrada
  └── MovimientoEvento
          │
          ▼
   Control de Acceso
```

De esta manera, el servicio utiliza el mismo vocabulario que será utilizado posteriormente por los consumidores del evento.

---

## `MovimientoEntrada`

`MovimientoEntrada` representa la información recibida por la API antes de crear el evento que viajará por Kafka.

La solicitud contiene los datos mínimos necesarios para representar un movimiento:

- placa;
- tipo de movimiento.

El contrato compartido se encarga de las validaciones y normalizaciones definidas para la entrada.

Entre ellas se encuentran acciones como:

- eliminar espacios innecesarios;
- convertir la placa a mayúsculas;
- validar la longitud;
- restringir caracteres no permitidos;
- comprobar que el tipo corresponda a un valor permitido.

Por ejemplo:

```text
Solicitud:
placa = " p123 "
tipo = "ENTRADA"

Normalización:
placa = "P123"
```

La finalidad es que los datos se encuentren normalizados antes de convertirse en un evento.

---

## `MovimientoEvento`

Después de validar la entrada, Control de Acceso construye un `MovimientoEvento`.

Este evento amplía la información recibida con datos que permiten identificar y rastrear el movimiento dentro del sistema.

Entre los elementos importantes se encuentra:

`evento_id`

El identificador permite distinguir cada movimiento de los demás.

El flujo puede representarse así:

```text
MovimientoEntrada
       ↓
validación
       ↓
MovimientoEvento
       ↓
evento_id
       ↓
publicación Kafka
```

El `evento_id` será utilizado posteriormente para mantener trazabilidad sobre el procesamiento realizado por Disponibilidad.

---

## `evento_id` y procesamiento asíncrono

El `evento_id` es especialmente importante porque el procesamiento no termina dentro de Control de Acceso.

Cuando el servicio devuelve una respuesta `202 Accepted`, el movimiento ya fue recibido y enviado al flujo de procesamiento, pero Disponibilidad puede todavía no haber aplicado sus reglas.

Conceptualmente:

```text
Cliente
   │
   │ POST /movimientos
   ▼
Acceso
   │
   │ crea evento_id = ABC
   ▼
Kafka
   │
   ▼
respuesta 202 + evento_id
   │
   │ procesamiento continúa
   ▼
Disponibilidad procesa ABC
```

Esto permite que posteriormente el resultado pueda relacionarse con el mismo evento.

---

## API HTTP

La aplicación se implementa utilizando FastAPI.

Los endpoints principales del microservicio son:

```text
GET  /health
POST /movimientos
```

FastAPI también proporciona documentación interactiva mediante Swagger.

Durante la ejecución, la documentación de la API puede consultarse mediante:

`/docs`

Esto facilita probar manualmente el servicio sin necesidad de construir primero una interfaz adicional.

---

## `GET /health`

El endpoint:

`GET /health`

se utiliza para comprobar que la aplicación se encuentra activa y puede responder solicitudes HTTP.

Su responsabilidad no es comprobar reglas de negocio ni procesar movimientos.

Conceptualmente:

```text
Cliente / Docker
      ↓
GET /health
      ↓
Control de Acceso
      ↓
servicio disponible
```

Este tipo de endpoint también resulta útil para healthchecks durante la ejecución con Docker.

---

## `POST /movimientos`

El endpoint:

`POST /movimientos`

es la entrada principal del microservicio.

Su flujo general es:

```text
POST /movimientos
        ↓
MovimientoEntrada
        ↓
validación Pydantic
        ↓
MovimientoEvento
        ↓
publicador.publicar(evento)
        ↓
Kafka
        ↓
respuesta HTTP
```

La lógica del endpoint se mantiene enfocada en recepción y publicación.

No modifica directamente la disponibilidad del estacionamiento.

---

## Por qué responde `202 Accepted`

Cuando la publicación es confirmada, el endpoint devuelve:

`202 Accepted`

Este código es adecuado porque la solicitud fue aceptada para procesamiento, pero el procesamiento completo del movimiento ocurre posteriormente en otro microservicio.

Es importante distinguir:

```text
202 Accepted
      ≠
movimiento aceptado por las reglas del estacionamiento
```

`202 Accepted` significa que:

- la solicitud HTTP fue válida;
- se creó el evento;
- el evento fue enviado correctamente al flujo de mensajería.

No significa que:

- la entrada del vehículo ya fue aprobada;
- la salida ya fue aplicada;
- el estacionamiento tenga espacio;
- la ocupación ya haya cambiado.

Estas decisiones corresponden a Disponibilidad.

---

## Ejemplo conceptual de `202 Accepted`

Supongamos que se envía:

```text
placa = "P123"
tipo = "ENTRADA"
```

Control de Acceso puede responder `202 Accepted` después de publicar el evento.

Sin embargo, posteriormente Disponibilidad podría determinar que:

- la placa ya se encuentra dentro; o
- el estacionamiento está lleno.

Por lo tanto:

```text
Acceso acepta el evento para procesamiento
                ↓
Disponibilidad decide el resultado del movimiento
```

Esta separación es necesaria para mantener responsabilidades independientes.

---

## Manejo de error `503 Service Unavailable`

Control de Acceso no debe responder éxito si Kafka no confirma correctamente la publicación.

Si ocurre un error durante la publicación, el endpoint responde:

`503 Service Unavailable`

El comportamiento conceptual es:

```text
Movimiento válido
      ↓
crear evento
      ↓
publicar en Kafka
      ↓
¿publicación confirmada?
    /       \
   Sí       No
   ↓         ↓
 202        503
```

De esta manera, el servicio no simula que el movimiento fue enviado cuando realmente no pudo publicarse.

---

## Diferencia entre error de validación y error de infraestructura

Existen dos categorías diferentes de fallos antes de que Disponibilidad procese un movimiento.

### Error de validación

Ocurre cuando la entrada no cumple el contrato esperado.

Por ejemplo:

- placa inválida;
- longitud no permitida;
- caracteres no válidos;
- tipo de movimiento no permitido.

En ese caso, la solicitud no llega a convertirse en un evento válido.

### Error de publicación

Ocurre cuando el contrato ya fue validado, pero el servicio no logra confirmar la publicación hacia Kafka.

En este escenario se utiliza:

`503 Service Unavailable`

La diferencia conceptual es:

```text
Dato inválido
    ↓
fallo de contrato

Dato válido
    ↓
Kafka no disponible / publicación fallida
    ↓
503
```

---

## Abstracción `PublicadorMovimientos`

El servicio no acopla directamente el endpoint HTTP al cliente Kafka.

En su lugar utiliza una abstracción llamada:

`PublicadorMovimientos`

La idea es que la lógica de `registrar_movimiento` dependa de algo capaz de publicar un `MovimientoEvento`, sin necesitar conocer los detalles internos de Kafka.

Conceptualmente:

```text
main.py
   │
   │ depende de
   ▼
PublicadorMovimientos
   ▲
   │ implementación
   │
PublicadorKafka
   │
   ▼
Kafka
```

Esta separación permite aplicar inversión de dependencias.

---

## Beneficio de la inversión de dependencias

Sin una abstracción, el endpoint tendría que conocer directamente el cliente Kafka.

Conceptualmente:

```text
Endpoint
   ↓
cliente Kafka concreto
```

Con la abstracción:

```text
Endpoint
   ↓
PublicadorMovimientos
   ↓
implementación intercambiable
```

Esto permite:

- desacoplar FastAPI de la implementación de Kafka;
- facilitar pruebas;
- inyectar un publicador falso;
- mantener el endpoint enfocado en su responsabilidad;
- sustituir la implementación sin reescribir la lógica HTTP.

La abstracción no se incorpora únicamente para “usar un patrón”, sino porque resuelve una necesidad concreta de diseño y testabilidad.

---

## `PublicadorKafka`

Durante la ejecución normal se utiliza una implementación real:

`PublicadorKafka`

Su responsabilidad es utilizar las utilidades compartidas de Kafka para enviar el `MovimientoEvento` al topic correspondiente.

Conceptualmente:

```text
MovimientoEvento
       ↓
PublicadorKafka
       ↓
utilidad compartida Kafka
       ↓
serialización JSON
       ↓
can-i-park.movimientos
```

Esto permite reutilizar la infraestructura implementada en:

`shared/canipark_shared/kafka.py`

Control de Acceso no necesita duplicar toda la configuración y lógica de publicación.

---

## Reutilización de la plataforma compartida

Control de Acceso aprovecha dos áreas importantes de reutilización:

### Contratos

Reutiliza los modelos definidos en:

`shared/canipark_shared/eventos.py`

### Kafka

Reutiliza las utilidades definidas en:

`shared/canipark_shared/kafka.py`

La relación general es:

```text
             shared
       ┌───────────────┐
       │ eventos.py    │
       │ kafka.py      │
       └───────┬───────┘
               │
               ▼
        Control de Acceso
               │
               ▼
             Kafka
```

Esto evita copiar contratos y lógica de infraestructura dentro del servicio.

---

## Configuración del servicio

El archivo:

`acceso_app/config.py`

concentra la configuración necesaria para que Control de Acceso pueda comunicarse con Kafka.

La configuración incluye elementos relacionados con:

- servidor o dirección de Kafka;
- topic utilizado para movimientos;
- habilitación o deshabilitación de la integración Kafka según el entorno.

La configuración se obtiene mediante variables de entorno cuando corresponde.

Esto evita dejar valores dependientes del entorno distribuidos directamente dentro de la lógica del endpoint.

Conceptualmente:

```text
variables de entorno
        ↓
     config.py
        ↓
 Control de Acceso
        ↓
     productor
```

---

## Topic de movimientos

El movimiento generado por Control de Acceso se publica en el topic:

`can-i-park.movimientos`

Este topic representa el canal lógico donde se transportan los eventos de entrada y salida.

La relación es:

```text
Control de Acceso
        │
        │ MovimientoEvento
        ▼
can-i-park.movimientos
        │
        ▼
Disponibilidad
```

Acceso actúa como productor de este topic.

Disponibilidad actúa posteriormente como consumidor.

---

## Comunicación asíncrona

Una de las decisiones principales del sistema es que Acceso no invoque directamente a Disponibilidad mediante HTTP para ejecutar las reglas del estacionamiento.

La comunicación de negocio utiliza Kafka:

```text
Acceso
   │
   ▼
Kafka
   │
   ▼
Disponibilidad
```

en lugar de:

```text
Acceso
   │
   │ llamada HTTP directa
   ▼
Disponibilidad
```

Esto permite desacoplar el momento de recepción del momento de procesamiento.

También permite que cada servicio tenga una responsabilidad independiente dentro del flujo.

---

## Flujo completo de un movimiento desde Acceso

El recorrido puede explicarse paso a paso:

```text
1. Cliente envía placa + tipo
             ↓
2. FastAPI recibe POST /movimientos
             ↓
3. MovimientoEntrada valida y normaliza
             ↓
4. Se crea MovimientoEvento
             ↓
5. Se genera evento_id
             ↓
6. PublicadorMovimientos recibe el evento
             ↓
7. PublicadorKafka lo serializa/publica
             ↓
8. Kafka confirma la publicación
             ↓
9. Acceso responde 202 Accepted
             ↓
10. Disponibilidad procesa posteriormente
```

Si falla la publicación:

```text
Kafka no confirma
      ↓
excepción de publicación
      ↓
503 Service Unavailable
```

---

## Qué ocurre después de Acceso

Una vez publicado el evento, Control de Acceso termina su responsabilidad.

Después:

```text
Kafka
  ↓
Disponibilidad
  ↓
reglas de dominio
  ↓
resultado del movimiento
```

Disponibilidad será responsable de determinar si:

- una entrada es válida;
- una salida es válida;
- una placa ya está dentro;
- el estacionamiento está lleno;
- el movimiento cambia la ocupación;
- cambia el estado general del estacionamiento.

Control de Acceso no duplica esas decisiones.

---

## Dockerfile del microservicio

Control de Acceso mantiene su propio:

`servicios/acceso/Dockerfile`

Esto permite que el servicio pueda construirse y ejecutarse de manera independiente.

El uso de un Dockerfile propio forma parte de la separación entre microservicios.

Conceptualmente:

```text
servicios/acceso/
      ↓
Dockerfile
      ↓
imagen del servicio
      ↓
contenedor Acceso
```

El servicio HTTP debe quedar disponible desde el contenedor para que otros componentes y el host puedan comunicarse con él.

Dentro de la ejecución Docker, la aplicación escucha de forma accesible para el entorno de contenedores en lugar de limitarse únicamente a `127.0.0.1`.

---

## Independencia del microservicio

Aunque Control de Acceso reutiliza `shared`, mantiene elementos propios:

- aplicación FastAPI;
- configuración;
- dependencias;
- publicador adaptado al servicio;
- Dockerfile;
- pruebas.

Esto permite que la arquitectura conserve una separación clara:

```text
shared = elementos reutilizables

acceso = recepción y publicación

disponibilidad = reglas y estado

notificaciones = reacción ante cambios
```

Reutilizar componentes no significa convertir todos los servicios en una sola aplicación.

---

## Pruebas automatizadas

El archivo:

`servicios/acceso/tests/test_api_acceso.py`

contiene las pruebas automatizadas correspondientes al microservicio.

El conjunto actual contempla **5 pruebas** relacionadas con el comportamiento de la API.

Las pruebas cubren aspectos como:

- recepción de movimientos;
- normalización de datos;
- validación del contrato;
- publicación mediante una dependencia sustituible;
- comportamiento cuando falla la publicación;
- respuesta `503` ante fallo de infraestructura.

Estas pruebas permiten verificar Control de Acceso sin depender obligatoriamente de un broker Kafka real.

---

## Publicador falso durante pruebas

La abstracción `PublicadorMovimientos` permite sustituir la implementación real de Kafka por un objeto controlado durante las pruebas.

Conceptualmente:

```text
Prueba
  ↓
FastAPI
  ↓
Publicador falso
```

en lugar de:

```text
Prueba
  ↓
FastAPI
  ↓
Kafka real
```

Esto permite comprobar:

- qué evento intentó publicar el endpoint;
- si la normalización fue aplicada;
- cómo responde la API cuando el publicador funciona;
- cómo responde la API cuando el publicador genera una excepción.

El objetivo no es reemplazar las pruebas E2E, sino complementar las pruebas del servicio con verificaciones rápidas y aisladas.

---

## Pruebas aisladas y pruebas E2E

Las pruebas de `test_api_acceso.py` verifican el comportamiento propio de Control de Acceso.

Más adelante, el flujo completo se valida mediante una prueba E2E que recorre:

```text
Acceso
  ↓
Kafka
  ↓
Disponibilidad
```

Estas pruebas tienen objetivos diferentes.

### Prueba aislada

Comprueba el contrato y comportamiento del microservicio de forma rápida.

### Prueba E2E

Comprueba que varios componentes reales puedan integrarse correctamente.

Por lo tanto:

```text
pruebas aisladas
       +
pruebas E2E
       =
mayor cobertura del flujo
```

---

## Swagger y demostración manual

FastAPI genera documentación interactiva mediante Swagger.

Esto permite probar:

`POST /movimientos`

sin depender de la interfaz visual final.

Durante una demostración técnica se puede utilizar Swagger para mostrar:

1. la estructura esperada del movimiento;
2. el envío de una placa;
3. el tipo `ENTRADA` o `SALIDA`;
4. la respuesta `202`;
5. el `evento_id` generado.

La interfaz final también puede iniciar este mismo flujo por HTTP.

---

## Relación con la interfaz

La interfaz puede utilizar Control de Acceso mediante HTTP.

El recorrido comienza de esta forma:

```text
Interfaz
    ↓ HTTP
Control de Acceso
    ↓ Kafka
Disponibilidad
```

La interfaz no publica mensajes directamente en Kafka.

Esto mantiene el broker fuera de la capa visual y conserva Control de Acceso como punto de entrada al flujo.

---

## Separación entre HTTP y Kafka

Dentro del sistema existen dos mecanismos de comunicación con propósitos diferentes.

### HTTP

Se utiliza para que clientes externos o la interfaz interactúen con las APIs.

Por ejemplo:

`POST /movimientos`

### Kafka

Se utiliza para transportar eventos entre microservicios.

Por ejemplo:

`can-i-park.movimientos`

La relación es:

```text
Cliente
   ↓ HTTP
Acceso
   ↓ Kafka
Disponibilidad
```

No deben confundirse un endpoint HTTP y un topic Kafka.

---

## Calidad y mantenibilidad

La organización de Control de Acceso busca mantener responsabilidades pequeñas y comprensibles.

El servicio separa:

```text
config.py
    ↓
configuración

productor.py
    ↓
abstracción/adaptador de publicación

main.py
    ↓
API HTTP

test_api_acceso.py
    ↓
validación automatizada
```

Esto facilita:

- lectura del código;
- mantenimiento;
- pruebas;
- reutilización;
- sustitución de dependencias;
- evolución independiente del servicio.

---

## Decisiones de diseño importantes

### Acceso no calcula disponibilidad

La disponibilidad depende del estado global del estacionamiento.

Ese estado pertenece a Disponibilidad.

Mantener esta regla fuera de Acceso evita duplicación.

---

### Acceso responde `202`

El movimiento se acepta para procesamiento asíncrono.

La respuesta no representa todavía la decisión del dominio.

---

### Acceso responde `503` si falla la publicación

El servicio no debe informar éxito cuando no logró entregar el evento al flujo de mensajería.

---

### El endpoint depende de una abstracción

`PublicadorMovimientos` desacopla la lógica HTTP de la implementación concreta de Kafka.

Esto mejora testabilidad y mantenibilidad.

---

### Los contratos se reutilizan desde `shared`

Control de Acceso no define una versión propia de `MovimientoEntrada` o `MovimientoEvento`.

Esto mantiene consistencia entre productores y consumidores.

---

## Lo que este microservicio no intenta resolver

Dentro del alcance académico actual, Control de Acceso no implementa:

- reservas;
- pagos;
- autenticación;
- reconocimiento de placas mediante cámaras;
- sensores físicos;
- persistencia en base de datos;
- reglas de múltiples estacionamientos.

Estas funcionalidades se encuentran fuera del objetivo principal del proyecto.

Can I Park? prioriza demostrar:

- microservicios;
- comunicación mediante Kafka;
- modularidad;
- reutilización;
- pruebas;
- Docker.

---

## Papel dentro de la arquitectura completa

El flujo principal puede resumirse así:

```text
Interfaz / Swagger
        ↓ HTTP
Control de Acceso
        ↓
MovimientoEvento
        ↓
Kafka
can-i-park.movimientos
        ↓
Disponibilidad
        ↓
EstadoEstacionamientoEvento
        ↓
Kafka
can-i-park.estados
        ↓
Notificaciones
```

Control de Acceso participa únicamente en la primera frontera del flujo:

```text
recibir
   ↓
validar
   ↓
crear evento
   ↓
publicar
```

Después de publicar correctamente, la responsabilidad pasa a los siguientes componentes.

---

## Puntos clave para defender el componente

Quien sea responsable de Control de Acceso debe poder explicar claramente:

### ¿Por qué `POST /movimientos` devuelve `202 Accepted`?

Porque el movimiento fue recibido y enviado para procesamiento asíncrono, pero las reglas de Disponibilidad todavía pueden no haberse ejecutado.

### ¿Qué significa un `202`?

Significa que el evento fue aceptado para procesamiento.

No significa que el vehículo ya haya sido aceptado físicamente dentro del estacionamiento.

### ¿Cuándo responde `503`?

Cuando no es posible confirmar correctamente la publicación del movimiento hacia Kafka.

### ¿Por qué Acceso no comprueba si el estacionamiento está lleno?

Porque esa regla depende del estado global y pertenece al microservicio de Disponibilidad.

### ¿Para qué sirve `evento_id`?

Permite identificar y rastrear de manera única el evento durante su procesamiento.

### ¿Por qué existe `PublicadorMovimientos`?

Para que el endpoint dependa de una abstracción de publicación y no directamente del cliente Kafka, facilitando desacoplamiento y pruebas.

### ¿Qué valida Pydantic antes de publicar?

El contrato de entrada aplica las restricciones y normalización definidas para los datos, incluyendo la placa y el tipo de movimiento.

### ¿Por qué se reutiliza `shared`?

Para que los servicios utilicen los mismos contratos y utilidades comunes sin duplicar implementaciones.

---

## Resumen del componente

Control de Acceso puede resumirse con la siguiente frase:

> **Acceso recibe y valida el movimiento, crea un evento identificable y lo publica; Disponibilidad es quien decide el efecto del movimiento sobre el estacionamiento.**

Su responsabilidad dentro del proyecto es pequeña pero fundamental:

```text
Entrada HTTP
    ↓
validación
    ↓
evento
    ↓
Kafka
```

Esta separación permite que Can I Park? mantenga una arquitectura modular, desacoplada, reutilizable y fácil de probar.

---

## Conclusión

El microservicio de Control de Acceso establece la primera frontera del sistema distribuido de Can I Park?.

Su diseño mantiene separadas la recepción HTTP, la validación del contrato, la creación del evento y la publicación hacia Kafka.

El uso de contratos compartidos evita inconsistencias entre servicios, mientras que la abstracción `PublicadorMovimientos` desacopla la API de la infraestructura concreta de mensajería.

Finalmente, el uso de `202 Accepted`, el manejo de `503 Service Unavailable` y las pruebas automatizadas permiten representar correctamente un flujo asíncrono donde recibir un movimiento no equivale a decidir su resultado de negocio.

Esta separación contribuye directamente a los objetivos de modularidad, reutilización, mantenibilidad y comunicación entre microservicios planteados para Can I Park?.
