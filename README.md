# 🚗 Can I Park?

**Actividad Evaluada 2: Proyecto**<br>
**Desarrollo y Reutilización de Software**<br>
**Tema 6: Sistema de Microservicios con Kafka para el Procesamiento de Datos en Tiempo Real**

---

## Tabla de contenidos

- [Ejecución del proyecto](#-ejecución-del-proyecto)
- [Modo de demostración](#-modo-de-demostración)
- [Pruebas y validación](#-pruebas-y-validación)
- [Integrantes del equipo](#-integrantes-del-equipo)

## 📘 Descripción del proyecto

**Can I Park?** es un sistema distribuido que mantiene actualizada la disponibilidad de espacios de un estacionamiento a partir de movimientos de **entrada** y **salida** de vehículos.

La solución está dividida en microservicios independientes que se comunican de forma asíncrona mediante **Apache Kafka**, evitando dependencias directas entre los servicios y permitiendo que cada componente tenga una responsabilidad específica.

> 🐍 **Nota académica:** El proyecto fue desarrollado en **Python**, lenguaje autorizado por la docente para la implementación del Tema 6. Se utiliza **FastAPI** para las APIs y `confluent-kafka` para la comunicación con Apache Kafka.

---

## 🎯 Objetivo

Demostrar una arquitectura basada en microservicios en la que un servicio recibe movimientos de vehículos, Kafka transporta los eventos y otros servicios procesan la información para actualizar la disponibilidad del estacionamiento y generar notificaciones cuando cambia su estado.

---

## 🏗️ Arquitectura del sistema

El flujo principal del sistema es:

```text
                       HTTP
                         │
                         ▼
                  Control de Acceso
                         │
                         │ MovimientoEvento
                         ▼
              can-i-park.movimientos
                         │
                         ▼
                    Apache Kafka
                         │
                         ▼
                   Disponibilidad
                         │
                         │ EstadoEstacionamientoEvento
                         ▼
                can-i-park.estados
                         │
                         ▼
                    Apache Kafka
                         │
                         ▼
                   Notificaciones
```

La interfaz web utiliza HTTP para consultar y mostrar información de los microservicios. La comunicación de negocio entre los servicios se realiza mediante **Kafka**, no mediante llamadas HTTP directas entre ellos.

---

## 🧩 Componentes principales

### 🔐 Control de Acceso

Recibe los movimientos de **ENTRADA** y **SALIDA**, valida los datos recibidos y publica un evento en Kafka.

Topic utilizado:

```text
can-i-park.movimientos
```

---

### 🅿️ Disponibilidad

Consume los movimientos publicados por Control de Acceso y aplica las reglas de negocio del estacionamiento.

Entre sus responsabilidades se encuentran:

- Registrar vehículos dentro del estacionamiento.
- Evitar entradas duplicadas.
- Rechazar salidas de vehículos inexistentes.
- Impedir nuevas entradas cuando el estacionamiento está lleno.
- Mantener la cantidad de espacios ocupados y disponibles.
- Evitar procesar dos veces el mismo evento mediante idempotencia.
- Determinar los estados `DISPONIBLE`, `POCOS_ESPACIOS` y `LLENO`.

Cuando cambia el estado general del estacionamiento publica un nuevo evento en:

```text
can-i-park.estados
```

---

### 🔔 Notificaciones

Consume los cambios de estado publicados por Disponibilidad y genera alertas cuando el estacionamiento llega a condiciones relevantes, como:

- `POCOS_ESPACIOS`
- `LLENO`

Los cambios que mantienen el estado `DISPONIBLE` no generan alertas innecesarias.

---

### 🖥️ Interfaz

La interfaz permite demostrar visualmente el recorrido completo de un movimiento.

Desde ella se puede:

- Registrar entradas.
- Registrar salidas.
- Consultar capacidad.
- Consultar espacios ocupados.
- Consultar espacios disponibles.
- Visualizar el estado del estacionamiento.
- Consultar los vehículos dentro.
- Observar el recorrido del evento.
- Visualizar las alertas generadas por Notificaciones.

La interfaz utiliza **Nginx** como servidor web y proxy inverso.

---

## ✅ Características principales

- ✅ Arquitectura de microservicios.
- ✅ Comunicación asíncrona mediante Apache Kafka.
- ✅ Procesamiento de entradas y salidas.
- ✅ Disponibilidad actualizada en tiempo real.
- ✅ Validación de reglas de negocio.
- ✅ Idempotencia mediante `evento_id`.
- ✅ Manejo seguro de concurrencia.
- ✅ Notificaciones por cambios de estado.
- ✅ Contratos y utilidades Kafka reutilizables.
- ✅ APIs documentadas mediante Swagger.
- ✅ Interfaz web de demostración.
- ✅ Contenerización con Docker.
- ✅ Orquestación con Docker Compose.
- ✅ Pruebas unitarias, de integración y E2E.
- ✅ Entorno reproducible de pruebas.

---

## ♻️ Reutilización y modularidad

Uno de los objetivos principales del proyecto es aplicar principios de **reutilización de software**.

Para evitar duplicación se creó el paquete:

```text
shared/canipark_shared/
```

Este paquete contiene contratos y utilidades que pueden ser utilizados por distintos microservicios.

Entre los elementos reutilizados se encuentran:

```text
MovimientoEntrada
MovimientoEvento
ResultadoMovimiento
EstadoEstacionamientoEvento
TipoMovimiento
EstadoEstacionamiento
```

También se centralizan utilidades para:

- Crear productores Kafka.
- Crear consumidores Kafka.
- Publicar mensajes JSON.
- Consumir eventos.
- Gestionar confirmaciones de entrega.
- Realizar commit manual de offsets.

De esta manera, cada microservicio reutiliza una misma implementación para los elementos compartidos sin duplicar lógica.

---

## 🧠 Patrones y principios aplicados

### 📨 Publish / Subscribe

Apache Kafka funciona como intermediario entre productores y consumidores.

Un servicio publica eventos sin necesitar conocer directamente qué servicio los consumirá.

Esto permite reducir el acoplamiento entre los componentes.

---

### 🔄 Producer / Consumer

El sistema implementa dos flujos principales:

```text
Control de Acceso
      │
   Producer
      ▼
    Kafka
      │
   Consumer
      ▼
Disponibilidad
```

y:

```text
Disponibilidad
      │
   Producer
      ▼
    Kafka
      │
   Consumer
      ▼
Notificaciones
```

---

### 💉 Inyección de dependencias

Control de Acceso utiliza una abstracción para la publicación de movimientos.

Esto permite sustituir la implementación real de Kafka durante las pruebas sin modificar la lógica principal del endpoint.

---

### 🔗 Bajo acoplamiento

Los microservicios no importan directamente el código interno de otros microservicios.

La comunicación de negocio se realiza mediante contratos compartidos y eventos publicados en Kafka.

---

### 🎯 Alta cohesión

Cada componente posee una responsabilidad concreta:

| Componente | Responsabilidad |
| --- | --- |
| Control de Acceso | Recibir movimientos |
| Disponibilidad | Aplicar reglas del estacionamiento |
| Notificaciones | Reaccionar a cambios de estado |
| Kafka | Transportar eventos |
| Interfaz | Presentar y demostrar el funcionamiento |

---

## 🛠️ Tecnologías utilizadas

- 🐍 **Python 3.12**
- ⚡ **FastAPI**
- 📨 **Apache Kafka 3.9**
- 🐳 **Docker**
- 🐳 **Docker Compose**
- 🌐 **Nginx**
- 🧪 **Pytest**
- 📦 **Pydantic**
- 🔌 **confluent-kafka**
- 🌐 **HTML, CSS y JavaScript**

---

## 📂 Estructura del proyecto

```text
can-i-park/
│
├── shared/
│   └── canipark_shared/
│       ├── eventos.py
│       └── kafka.py
│
├── servicios/
│   ├── acceso/
│   ├── disponibilidad/
│   └── notificaciones/
│
├── interfaz/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   ├── nginx.conf
│   └── Dockerfile
│
├── tests/
│
├── scripts/
│
├── docs/
│   ├── componentes/
│   ├── evidencias/
│   ├── ARQUITECTURA.md
│   ├── DECISIONES.md
│   ├── PRUEBAS.md
│   ├── RESULTADO_PRUEBAS.md
│   └── REVISION_RUBRICA.md
│
├── docker-compose.yml
├── requirements-dev.txt
├── pytest.ini
└── README.md
```

---

# 🚀 Ejecución del proyecto

## 📥 Paso 1: Clonar el repositorio

```bash
git clone https://github.com/Doisaac/can-i-park.git
cd can-i-park
```

---

## 🐳 Paso 2: Verificar Docker

Es necesario tener instalado y ejecutándose:

- Docker
- Docker Compose

Se puede verificar mediante:

```bash
docker --version
docker compose version
```

---

## ▶️ Paso 3: Construir y levantar el sistema

Ejecutar:

```bash
docker compose up -d --build
```

Docker Compose levantará:

- Apache Kafka.
- Control de Acceso.
- Disponibilidad.
- Notificaciones.
- Interfaz.

---

## 🔎 Paso 4: Verificar los contenedores

```bash
docker compose ps
```

Los componentes principales deben aparecer en estado:

```text
healthy
```

---

## 🌐 Acceso a los servicios

| Servicio | Dirección |
| --- | --- |
| 🚗 Interfaz | `http://localhost:8080` |
| 🔐 Swagger - Control de Acceso | `http://localhost:8001/docs` |
| 🅿️ Swagger - Disponibilidad | `http://localhost:8002/docs` |
| 🔔 Swagger - Notificaciones | `http://localhost:8003/docs` |
| 📨 Kafka | `localhost:9092` |

---

# 🎬 Modo de demostración

La configuración normal del proyecto utiliza:

```text
Capacidad: 100
Umbral de pocos espacios: 10
```

Para realizar una demostración visual más rápida en **PowerShell**, se puede utilizar temporalmente una capacidad menor:

```powershell
$env:CAPACIDAD_ESTACIONAMIENTO="10"
$env:UMBRAL_POCOS_ESPACIOS="2"

docker compose up -d --force-recreate disponibilidad
```

Esto permite demostrar fácilmente los estados:

```text
DISPONIBLE
POCOS_ESPACIOS
LLENO
```

Al finalizar la demostración se puede restaurar la configuración normal mediante:

```powershell
Remove-Item Env:CAPACIDAD_ESTACIONAMIENTO
Remove-Item Env:UMBRAL_POCOS_ESPACIOS

docker compose up -d --force-recreate disponibilidad
```

---

# 🧪 Pruebas y validación

El proyecto contiene pruebas:

- Unitarias.
- De API.
- De dominio.
- De integración.
- E2E con Kafka real.
- De configuración.
- De interfaz.

La validación completa puede ejecutarse en Windows mediante:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\validar_entrega.ps1
```

En Linux o sistemas compatibles con Bash:

```bash
bash scripts/validar_entrega.sh
```

---

## ✅ Resultado de la validación final

La validación realizada sobre el sistema obtuvo:

```text
26 passed
```

Los flujos E2E verificados fueron:

```text
Acceso → Kafka → Disponibilidad
```

y:

```text
Disponibilidad → Kafka → Notificaciones
```

El resultado general fue:

```text
VALIDACION COMPLETA: OK
```

Después de la validación, los cinco componentes principales quedaron en estado saludable.

La evidencia detallada se encuentra en:

```text
docs/RESULTADO_PRUEBAS.md
```

---

## 📚 Documentación técnica

El proyecto incluye documentación específica para cada componente:

```text
docs/componentes/PLATAFORMA_KAFKA.md
docs/componentes/CONTROL_ACCESO.md
docs/componentes/DISPONIBILIDAD.md
docs/componentes/NOTIFICACIONES.md
docs/componentes/INTERFAZ_DEMO.md
```

También se incluyen documentos transversales:

| Documento | Contenido |
| --- | --- |
| `docs/ARQUITECTURA.md` | Arquitectura completa del sistema |
| `docs/DECISIONES.md` | Decisiones técnicas y trade-offs |
| `docs/PRUEBAS.md` | Estrategia de pruebas |
| `docs/RESULTADO_PRUEBAS.md` | Resultados reales de validación |
| `docs/REVISION_RUBRICA.md` | Relación entre requisitos y evidencias |

---

## ⚠️ Limitaciones conocidas

El estado actual del estacionamiento se mantiene en memoria. Si el microservicio de Disponibilidad se reinicia, el estado registrado durante esa ejecución se pierde.

Para el alcance académico se priorizó demostrar microservicios, comunicación asíncrona con Kafka, modularidad, reutilización, pruebas y contenerización con Docker.

Una versión orientada a producción podría incorporar persistencia de datos, observabilidad más completa y una estrategia para mensajes que no puedan procesarse correctamente, como una Dead Letter Queue (DLQ).

---
## ⏹️ Detener el proyecto

Para detener todos los componentes:

```bash
docker compose down
```

---

# 👥 Integrantes del equipo

| **Nombre** | **Carnet** |
| --- | --- |
| **Douglas Isaac Barrera Magaña** | `BM22025` |
| **Ricardo Enrique Heredia Ramos** | `HR21024` |
| **Gabriel Omar Calderón Calderón** | `CC22060` |
| **Douglas Enrique Sigüenza Quele** | `SQ22005` |
| **Fernando José Barraza Álvarez** | `BA22025` |

---

## 🎓 Universidad de El Salvador

**Facultad Multidisciplinaria de Occidente**<br>
**Ingeniería en Desarrollo de Software**<br>
**Desarrollo y Reutilización de Software**<br>
**Ciclo II/2026**

---
