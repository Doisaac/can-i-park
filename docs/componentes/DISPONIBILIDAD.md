# Microservicio de Disponibilidad

## Propósito

El microservicio de **Disponibilidad** concentra las reglas de negocio del estacionamiento en **Can I Park?**.

Su función es consumir los movimientos publicados por Control de Acceso, decidir si una `ENTRADA` o `SALIDA` es válida, actualizar el estado del estacionamiento y publicar un cambio de estado cuando corresponde.

Flujo general:

```text
Control de Acceso
        ↓
Kafka - can-i-park.movimientos
        ↓
Disponibilidad
        ↓
Reglas del estacionamiento
        ↓
ResultadoMovimiento
        ↓
Kafka - can-i-park.estados
        ↓
Notificaciones
```

---

## Estructura

```text
servicios/disponibilidad/
├── Dockerfile
├── requirements.txt
├── disponibilidad_app/
│   ├── __init__.py
│   ├── config.py
│   ├── dominio.py
│   ├── kafka_worker.py
│   └── main.py
└── tests/
    ├── test_api_disponibilidad.py
    └── test_dominio.py

tests/
└── test_flujo_integrado.py
```

### Responsabilidad de los archivos

- `config.py`: capacidad, umbral, topics y configuración Kafka.
- `dominio.py`: reglas de entrada/salida, estados e idempotencia.
- `kafka_worker.py`: consume movimientos y publica cambios de estado.
- `main.py`: expone los endpoints HTTP.
- `test_dominio.py`: prueba reglas de negocio.
- `test_api_disponibilidad.py`: prueba los endpoints.
- `test_flujo_integrado.py`: valida integración entre Acceso y Disponibilidad sin Kafka real.

---

## GestorDisponibilidad

`GestorDisponibilidad` es la clase principal del dominio.

Mantiene el estado utilizando:

- `set`: placas actualmente dentro.
- `dict`: resultados procesados por `evento_id`.
- `deque`: retención limitada de resultados recientes.
- `RLock`: protección ante accesos concurrentes.

La cantidad de ocupados se obtiene mediante:

```text
len(_vehiculos_dentro)
```

y los disponibles se calculan con:

```text
disponibles = capacidad - ocupados
```

---

## Reglas de entrada

Cuando llega una `ENTRADA`:

```text
¿la placa ya está dentro?
   ├── Sí → rechazar
   └── No
        ↓
¿el estacionamiento está lleno?
   ├── Sí → rechazar
   └── No → agregar placa
```

Una entrada válida aumenta la ocupación.

Una entrada duplicada o una entrada con el estacionamiento lleno no modifica el estado.

---

## Reglas de salida

Cuando llega una `SALIDA`:

```text
¿la placa está dentro?
   ├── No → rechazar
   └── Sí → eliminar placa
```

Una salida válida reduce la ocupación.

Una salida de una placa inexistente se rechaza sin modificar el estado.

---

## Estados del estacionamiento

El microservicio calcula tres estados:

### `DISPONIBLE`

```text
disponibles > umbral
```

### `POCOS_ESPACIOS`

```text
0 < disponibles <= umbral
```

### `LLENO`

```text
disponibles == 0
```

Ejemplo con capacidad 3 y umbral 1:

```text
3 disponibles → DISPONIBLE
2 disponibles → DISPONIBLE
1 disponible  → POCOS_ESPACIOS
0 disponibles → LLENO
```

---

## Idempotencia

Cada movimiento posee un `evento_id`.

Si el mismo evento se recibe nuevamente, Disponibilidad detecta que ya fue procesado y devuelve el resultado anterior sin repetir el efecto.

```text
evento ABC
    ↓
procesado
    ↓
resultado guardado

evento ABC nuevamente
    ↓
resultado anterior
    ↓
sin repetir operación
```

La idempotencia de evento es diferente a una entrada duplicada de la misma placa.

---

## Worker Kafka

`kafka_worker.py` conecta Kafka con el dominio.

Su flujo es:

```text
can-i-park.movimientos
        ↓
MovimientoEvento
        ↓
GestorDisponibilidad
        ↓
ResultadoMovimiento
        ↓
¿cambió el estado?
        ↓
can-i-park.estados
```

El worker funciona en segundo plano para que FastAPI pueda atender consultas HTTP al mismo tiempo.

Si existe un fallo temporal de conexión, registra el error y vuelve a intentar.

---

## Publicación de cambios de estado

Disponibilidad no publica un evento de estado en cada movimiento.

Solo publica cuando cambia la categoría.

Ejemplo:

```text
DISPONIBLE → DISPONIBLE
```

No publica.

```text
DISPONIBLE → POCOS_ESPACIOS
```

Sí publica.

```text
POCOS_ESPACIOS → LLENO
```

Sí publica.

Esto evita generar eventos innecesarios.

---

## API HTTP

El servicio expone:

```text
GET /health
GET /disponibilidad
GET /vehiculos
GET /movimientos/{evento_id}
```

### `/health`

Comprueba que el servicio esté activo.

### `/disponibilidad`

Devuelve:

- capacidad;
- ocupados;
- disponibles;
- estado.

### `/vehiculos`

Devuelve las placas actualmente dentro.

### `/movimientos/{evento_id}`

Devuelve el `ResultadoMovimiento` asociado a un evento.

Un `404` inmediatamente después de enviar un movimiento puede significar que todavía no ha sido procesado, debido a la comunicación asíncrona mediante Kafka.

---

## Reutilización

Disponibilidad reutiliza contratos y utilidades de:

`shared/canipark_shared`

Entre ellos:

- `MovimientoEvento`;
- `ResultadoMovimiento`;
- `EstadoEstacionamiento`;
- `EstadoEstacionamientoEvento`;
- utilidades Kafka.

Esto evita duplicar código y mantiene consistencia entre los microservicios.

---

## Pruebas

Las pruebas cubren:

- entrada válida;
- entrada duplicada;
- salida válida;
- salida inexistente;
- estacionamiento lleno;
- cálculo de estados;
- idempotencia;
- endpoints HTTP;
- flujo integrado Acceso → Disponibilidad.

Las pruebas de dominio pueden ejecutarse sin levantar Kafka real, lo que facilita validar las reglas de forma aislada.

---

## Separación de responsabilidades

Disponibilidad sí decide:

- si una entrada o salida se acepta;
- ocupación;
- espacios disponibles;
- estado del estacionamiento;
- cambios de categoría.

Disponibilidad no se encarga de:

- recibir originalmente el movimiento del usuario;
- mostrar la interfaz;
- generar alertas visuales.

La idea central es:

```text
Acceso recibe
Kafka transporta
Disponibilidad decide
Notificaciones reacciona
```

---

## Limitación actual

El estado se mantiene en memoria.

Por esta razón, reiniciar el servicio elimina:

- placas dentro;
- resultados procesados.

Una mejora futura sería incorporar persistencia mediante una base de datos.

---

## Puntos clave para defender

Debes poder explicar:

- por qué se utiliza un `set` para las placas;
- cómo se rechaza una entrada duplicada;
- cómo se rechaza una salida inexistente;
- qué ocurre cuando el estacionamiento está lleno;
- cómo funciona la idempotencia con `evento_id`;
- por qué se utiliza `RLock`;
- cómo se calculan `DISPONIBLE`, `POCOS_ESPACIOS` y `LLENO`;
- por qué `can-i-park.estados` se publica solo cuando cambia la categoría;
- por qué el dominio está separado de FastAPI y Kafka.

---

## Conclusión

Disponibilidad es el núcleo de reglas de negocio de **Can I Park?**.

Consume movimientos, aplica las reglas del estacionamiento, mantiene el estado e informa únicamente los cambios importantes de categoría.

La separación entre dominio, worker Kafka, API y pruebas mejora la modularidad, reutilización, mantenibilidad y testabilidad del proyecto.