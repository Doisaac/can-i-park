# Plataforma compartida y comunicación Kafka

## Propósito

La plataforma compartida de **Can I Park?** centraliza los contratos de eventos y las utilidades de comunicación con **Apache Kafka** utilizadas por los diferentes microservicios del sistema.

Su objetivo principal es evitar que cada servicio implemente de forma independiente los mismos modelos, enumeraciones y operaciones relacionadas con Producer y Consumer.

La implementación se encuentra principalmente en el paquete:

`shared/canipark_shared`

Este paquete funciona como un componente reutilizable que puede ser utilizado por los microservicios sin necesidad de duplicar código.

---

## Estructura del componente

La plataforma compartida está organizada de la siguiente manera:

```text
shared/
├── pyproject.toml
└── canipark_shared/
    ├── __init__.py
    ├── eventos.py
    └── kafka.py
```

Cada archivo tiene una responsabilidad específica:

- `pyproject.toml`: define el paquete compartido y sus dependencias.
- `__init__.py`: expone los elementos principales del paquete.
- `eventos.py`: contiene los contratos y modelos utilizados por los servicios.
- `kafka.py`: contiene las utilidades reutilizables para producir y consumir mensajes mediante Kafka.

Esta separación permite mantener responsabilidades claras y facilita la reutilización del código.

---

## Contratos compartidos

El archivo `eventos.py` define los modelos utilizados para mantener un contrato común entre los diferentes componentes del sistema.

Estos contratos permiten que productores y consumidores conozcan exactamente la estructura de los datos que intercambian.

Entre los principales elementos se encuentran:

### `TipoMovimiento`

Representa los tipos de movimiento permitidos dentro del estacionamiento:

- `ENTRADA`
- `SALIDA`

El uso de una enumeración evita utilizar valores arbitrarios o inconsistentes entre servicios.

---

### `EstadoEstacionamiento`

Representa los posibles estados generales del estacionamiento:

- `DISPONIBLE`
- `POCOS_ESPACIOS`
- `LLENO`

De esta manera, todos los servicios utilizan los mismos valores para representar el estado del estacionamiento.

---

### `MovimientoEntrada`

Representa la información recibida inicialmente cuando se registra un movimiento.

Contiene principalmente:

- placa del vehículo;
- tipo de movimiento.

Este modelo también participa en la validación y normalización de los datos antes de que sean convertidos en un evento.

---

### `MovimientoEvento`

Representa el evento que será publicado en Kafka después de recibir y validar un movimiento.

Además de los datos originales, incorpora información que permite identificar y rastrear el evento, como:

- `evento_id`;
- fecha y hora del evento.

El identificador utiliza UUID para que cada evento tenga una identidad única dentro del sistema.

---

### `ResultadoMovimiento`

Representa el resultado obtenido después de que el microservicio de Disponibilidad procesa un movimiento.

Este resultado permite conservar información como:

- evento procesado;
- placa;
- tipo de movimiento;
- aceptación o rechazo;
- motivo;
- capacidad;
- espacios ocupados;
- espacios disponibles;
- estado del estacionamiento.

También permite conservar trazabilidad sobre los eventos que ya fueron procesados.

---

### `EstadoEstacionamientoEvento`

Representa un cambio en el estado general del estacionamiento.

Este evento no representa directamente una entrada o salida, sino una transición del estado global, por ejemplo:

```text
DISPONIBLE
     ↓
POCOS_ESPACIOS
     ↓
LLENO
```

Este tipo de evento es utilizado posteriormente por el microservicio de Notificaciones.

---

## Normalización y validación de placas

La información de la placa es normalizada antes de que sea procesada por los demás componentes.

El proceso contempla acciones como:

- eliminar espacios innecesarios;
- convertir el valor a mayúsculas;
- restringir caracteres no permitidos;
- validar la longitud definida por el contrato.

Por ejemplo:

```text
Entrada recibida:
" p123 "

Resultado normalizado:
"P123"
```

La ventaja de realizar esta validación dentro del contrato compartido es que los diferentes microservicios no necesitan implementar nuevamente las mismas reglas básicas de entrada.

Esto favorece la consistencia y reduce la duplicación de código.

---

## Comunicación mediante Kafka

Kafka se utiliza como broker de eventos para permitir que los microservicios puedan comunicarse sin depender directamente unos de otros.

El flujo general del sistema se puede representar de la siguiente forma:

```text
Control de Acceso
        │
        │ publica MovimientoEvento
        ▼
Apache Kafka
        │
        │ can-i-park.movimientos
        ▼
Disponibilidad
        │
        │ procesa reglas del dominio
        │
        │ si cambia el estado
        ▼
Apache Kafka
        │
        │ can-i-park.estados
        ▼
Notificaciones
```

La plataforma compartida proporciona las utilidades necesarias para publicar y consumir estos mensajes.

---

## Producer Kafka

El archivo `kafka.py` proporciona una función reutilizable para crear productores Kafka.

Entre las configuraciones utilizadas se encuentran:

```text
enable.idempotence=True
acks="all"
```

### `enable.idempotence=True`

Esta configuración ayuda a reducir duplicados que puedan producirse durante reintentos de publicación.

Su objetivo es mejorar la confiabilidad del Producer cuando ocurre algún problema temporal durante el envío.

### `acks="all"`

Indica que el Producer debe esperar la confirmación correspondiente del broker antes de considerar el mensaje como entregado.

Esto permite tener una confirmación más fuerte que simplemente enviar el mensaje y continuar.

---

## Publicación de mensajes JSON

La utilidad compartida permite convertir los datos del evento a JSON antes de publicarlos en Kafka.

El flujo puede resumirse así:

```text
Objeto Python
      ↓
serialización
      ↓
JSON
      ↓
publicación en Kafka
      ↓
confirmación de entrega
```

La publicación no se considera exitosa únicamente por ejecutar `produce()`.

Después de publicar, se utiliza `flush()` con un tiempo límite para verificar que los mensajes hayan sido enviados correctamente.

Si existen mensajes pendientes o Kafka informa un error mediante el callback de entrega, la utilidad genera una excepción.

De esta manera se evita reportar éxito cuando el broker no confirmó correctamente la publicación.

---

## Consumer Kafka

La plataforma compartida también proporciona una configuración reutilizable para crear consumidores Kafka.

Entre las configuraciones principales se encuentran:

```text
group.id
auto.offset.reset="earliest"
enable.auto.commit=False
```

---

### `group.id`

Identifica al grupo de consumidores al que pertenece una instancia.

Los consumidores pertenecientes al mismo grupo pueden distribuir el procesamiento de las particiones de un topic.

---

### `auto.offset.reset="earliest"`

Indica que, cuando un grupo de consumidores no posee una posición previa registrada, debe comenzar desde el mensaje más antiguo disponible.

---

### `enable.auto.commit=False`

El commit automático se desactiva para tener control sobre el momento exacto en que Kafka considera un mensaje como procesado.

Esto es importante porque recibir un mensaje no significa necesariamente que la lógica asociada haya terminado correctamente.

---

## Commit manual de offsets

El flujo de consumo utilizado por la plataforma compartida es:

```text
Kafka entrega mensaje
        ↓
deserialización JSON
        ↓
procesamiento del payload
        ↓
¿procesamiento exitoso?
        │
        ├── Sí
        │    ↓
        │ commit manual del offset
        │
        └── No
             ↓
          no se confirma
          el offset
```

El commit se realiza únicamente después de que el procesamiento termina correctamente.

Si la lógica genera una excepción, el offset no se confirma en esa ejecución.

Esta decisión ayuda a evitar que Kafka considere completado un trabajo que realmente falló durante su procesamiento.

---

## Idempotencia

Dentro de Can I Park? existen dos conceptos diferentes de idempotencia que no deben confundirse.

### Idempotencia del Producer

La configuración:

`enable.idempotence=True`

ayuda a reducir duplicados relacionados con reintentos durante la publicación de mensajes en Kafka.

Esta idempotencia pertenece a la infraestructura de mensajería.

---

### Idempotencia del dominio

El microservicio de Disponibilidad utiliza `evento_id` para reconocer eventos que ya fueron procesados.

Si el mismo evento vuelve a llegar, el dominio puede identificarlo y evitar repetir su efecto sobre el estacionamiento.

Por ejemplo:

```text
Evento ABC
Entrada P123
        ↓
procesado correctamente
        ↓
Evento ABC vuelve a llegar
        ↓
se reconoce como ya procesado
        ↓
no se repite la entrada
```

Por lo tanto:

```text
Idempotencia del Producer
        ≠
Idempotencia del dominio
```

La primera protege la publicación en Kafka.

La segunda protege el efecto de negocio producido por el evento.

---

## Reutilización del componente

El paquete `shared` constituye uno de los principales componentes reutilizables del proyecto.

Los diferentes microservicios pueden importar los mismos contratos y utilidades sin duplicar implementaciones.

Conceptualmente:

```text
                 shared
          ┌─────────────────┐
          │ eventos.py      │
          │ kafka.py        │
          └────────┬────────┘
                   │
        ┌──────────┼───────────┐
        ▼          ▼           ▼
     Acceso   Disponibilidad  Notificaciones
```

Esta separación proporciona varios beneficios:

- reutilización de código;
- reducción de duplicación;
- consistencia entre servicios;
- mantenibilidad;
- testabilidad;
- contratos centralizados;
- menor riesgo de incompatibilidades.

---

## Separación de responsabilidades

La plataforma compartida no contiene reglas específicas del estacionamiento.

Su responsabilidad es proporcionar:

- contratos comunes;
- enumeraciones;
- modelos de eventos;
- serialización;
- utilidades de Producer;
- utilidades de Consumer;
- control de commits de Kafka.

Las reglas relacionadas con:

- capacidad del estacionamiento;
- entrada duplicada;
- salida inexistente;
- cálculo de espacios disponibles;
- estado `DISPONIBLE`;
- estado `POCOS_ESPACIOS`;
- estado `LLENO`;

pertenecen al microservicio de Disponibilidad.

Esta separación permite mantener una arquitectura modular donde cada componente posee una responsabilidad clara.

---

## Pruebas de la infraestructura compartida

La infraestructura Kafka compartida se valida principalmente mediante:

`tests/test_kafka_shared.py`

Las pruebas verifican escenarios relacionados con:

- serialización y publicación de mensajes;
- entrega exitosa;
- mensajes pendientes después de `flush`;
- errores informados mediante el callback de Kafka;
- commit después de un procesamiento correcto;
- ausencia de commit cuando el procesamiento falla.

Estas pruebas permiten validar la infraestructura común sin necesidad de levantar todo el sistema.

---

## Entorno de ejecución de pruebas

Las pruebas de la plataforma compartida se ejecutan utilizando **Python 3.12 dentro de Docker**.

Esto permite mantener un entorno reproducible independientemente de la versión de Python instalada localmente en cada computadora.

El principio utilizado es:

```text
Código del proyecto
        ↓
contenedor Docker
        ↓
Python 3.12
        ↓
dependencias del proyecto
        ↓
pytest
```

De esta manera, todos los integrantes pueden validar el componente utilizando el mismo entorno.

---

## Papel dentro de Can I Park?

La plataforma compartida funciona como la base técnica que permite que los diferentes microservicios utilicen los mismos contratos y mecanismos de comunicación.

Dentro del flujo general:

```text
Interfaz / Swagger
        ↓
Control de Acceso
        ↓
Kafka - movimientos
        ↓
Disponibilidad
        ↓
Kafka - estados
        ↓
Notificaciones
```

`shared` proporciona los elementos comunes necesarios para que productores y consumidores mantengan una comunicación consistente.

Su principal aporte dentro de la arquitectura es permitir que los servicios sean independientes sin perder compatibilidad entre ellos.

---

## Conclusión

La plataforma compartida de Can I Park? permite centralizar los contratos y las utilidades relacionadas con Kafka en un componente reutilizable.

Esta decisión evita duplicación de código, mantiene consistencia entre productores y consumidores y facilita las pruebas de los componentes.

La combinación de contratos compartidos, publicación confiable, commit manual de offsets y separación de responsabilidades contribuye directamente a los objetivos de modularidad, reutilización y mantenibilidad del proyecto.