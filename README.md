# 🚗 Can I Park?

**Actividad Evaluada 2: Proyecto**<br>
**Desarrollo y Reutilización de Software**<br>
**Tema 6: Sistema de Microservicios con Kafka para el Procesamiento de Datos en Tiempo Real**

**Can I Park?** es un sistema distribuido que registra entradas y salidas de vehículos y mantiene actualizada la disponibilidad de un estacionamiento.

Como equipo decidimos separar el procesamiento en varios microservicios para que cada componente tuviera una responsabilidad clara. **Control de Acceso** recibe los movimientos, **Disponibilidad** aplica las reglas del estacionamiento y **Notificaciones** reacciona cuando ocurre un cambio importante de estado. La comunicación entre estos servicios se realiza de forma asíncrona mediante **Apache Kafka**.

> 🐍 El proyecto fue desarrollado en **Python 3.12**, lenguaje autorizado para la implementación de la actividad.

---

## 📘 Documento técnico del proyecto

La explicación completa del desarrollo de **Can I Park?**, incluyendo las decisiones tomadas por el equipo, la arquitectura, la reutilización de componentes, los patrones aplicados, las pruebas y los resultados obtenidos, se encuentra en:

📄 [Documento Técnico del Proyecto - Can I Park?](docs/Can_I_Park_Documento_Tecnico_Proyecto.pdf)

---

## Tabla de contenidos

- [Descripción general](#-descripción-general)
- [Cómo funciona](#-cómo-funciona)
- [Reutilización y decisiones principales](#-reutilización-y-decisiones-principales)
- [Tecnologías utilizadas](#-tecnologías-utilizadas)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Ejecución del proyecto](#-ejecución-del-proyecto)
- [Acceso a los servicios](#-acceso-a-los-servicios)
- [Modo de demostración](#-modo-de-demostración)
- [Pruebas y validación](#-pruebas-y-validación)
- [Documentación técnica](#-documentación-técnica)
- [Detener el proyecto](#-detener-el-proyecto)
- [Integrantes del equipo](#-integrantes-del-equipo)

---

## 📘 Descripción general

El funcionamiento parte de una acción sencilla: un vehículo entra o sale del estacionamiento.

La solicitud es recibida por **Control de Acceso**, que valida los datos y publica el movimiento en Kafka. Después, **Disponibilidad** consume ese evento, aplica las reglas del estacionamiento y actualiza la ocupación. Cuando el estado general cambia, se publica un nuevo evento que es procesado por **Notificaciones**.

La interfaz web permite observar este recorrido de una forma más clara y consultar información como capacidad, espacios ocupados, espacios disponibles, vehículos registrados y alertas.

La configuración normal del proyecto utiliza:

```text
Capacidad: 100
Umbral de pocos espacios: 10
```

Los estados posibles del estacionamiento son:

```text
DISPONIBLE
POCOS_ESPACIOS
LLENO
```

---

## 🏗️ Cómo funciona

El flujo principal puede resumirse así:

```text
Usuario / Interfaz
       │
       │ HTTP
       ▼
Control de Acceso
       │
       │ MovimientoEvento
       ▼
     Kafka
       │
       ▼
Disponibilidad
       │
       │ EstadoEstacionamientoEvento
       ▼
     Kafka
       │
       ▼
Notificaciones
```

La interfaz utiliza HTTP para registrar movimientos y consultar información. La comunicación principal entre los microservicios se realiza mediante Kafka, por lo que los servicios no necesitan llamarse directamente entre sí para completar el flujo de negocio.

### Control de Acceso

Recibe movimientos de **ENTRADA** y **SALIDA**, normaliza y valida la información y publica un evento en:

```text
can-i-park.movimientos
```

Cuando Kafka confirma la publicación, la API responde con `202 Accepted`, ya que el procesamiento continúa de forma asíncrona.

### Disponibilidad

Consume los movimientos, mantiene el estado actual del estacionamiento y aplica las reglas de entrada y salida.

Entre otras validaciones, evita entradas duplicadas, salidas de vehículos inexistentes y nuevas entradas cuando la capacidad ya fue alcanzada.

Cuando el estado general cambia, publica un evento en:

```text
can-i-park.estados
```

### Notificaciones

Consume los cambios de estado generados por Disponibilidad y registra alertas cuando el estacionamiento llega a condiciones relevantes, como `POCOS_ESPACIOS` o `LLENO`.

### Interfaz

La interfaz permite registrar movimientos y observar el resultado del procesamiento sin tener que trabajar directamente con varias terminales o herramientas.

**Nginx** sirve los archivos de la interfaz y actúa como proxy hacia las APIs del sistema.

---

## ♻️ Reutilización y decisiones principales

Para evitar duplicar contratos y configuraciones comunes decidimos crear:

```text
shared/canipark_shared/
```

Este paquete contiene los modelos de eventos y utilidades de Kafka que necesitan varios servicios.

Las reglas propias de cada microservicio permanecen dentro de su dominio. Por ejemplo, la lógica que decide si una entrada es válida pertenece a Disponibilidad y no al paquete compartido.

También se tomaron decisiones orientadas a mantener el sistema consistente durante el procesamiento asíncrono:

- Cada movimiento recibe un `evento_id`.
- Disponibilidad evita procesar dos veces el mismo evento.
- Los consumidores utilizan commit manual de offsets.
- La capacidad y el umbral se obtienen mediante variables de entorno.
- Los cambios de estado se publican solamente cuando ocurre una transición relevante.

La solución utiliza principalmente los modelos **Producer/Consumer** y **Publish/Subscribe** mediante Kafka. También se aplican principios de alta cohesión, bajo acoplamiento e inversión de dependencias en los puntos donde aportan claridad al diseño.

La explicación y justificación completa de estas decisiones se encuentra en el [documento técnico](docs/Can_I_Park_Documento_Tecnico_Proyecto.pdf).

---

## 🛠️ Tecnologías utilizadas

El proyecto utiliza:

- **Python 3.12**
- **FastAPI**
- **Pydantic**
- **Apache Kafka**
- **confluent-kafka**
- **Docker**
- **Docker Compose**
- **Nginx**
- **Pytest**
- **HTML, CSS y JavaScript**

---

## 📂 Estructura del proyecto

```text
can-i-park/
├── servicios/
│   ├── acceso/
│   ├── disponibilidad/
│   └── notificaciones/
├── shared/
│   └── canipark_shared/
├── interfaz/
├── tests/
├── scripts/
├── docs/
├── docker-compose.yml
├── requirements-dev.txt
├── pytest.ini
└── README.md
```

La carpeta `docs/` contiene la documentación técnica, documentación por componente y evidencias de validación.

---

# 🚀 Ejecución del proyecto

## Requisitos

Es necesario tener instalados y en ejecución:

- **Docker**
- **Docker Compose**

Se puede verificar con:

```bash
docker --version
docker compose version
```

## Clonar el repositorio

```bash
git clone https://github.com/Doisaac/can-i-park.git
cd can-i-park
```

## Construir y levantar el sistema

```bash
docker compose up -d --build
```

Docker Compose levantará los componentes principales del proyecto:

```text
Apache Kafka
Control de Acceso
Disponibilidad
Notificaciones
Interfaz
```

## Verificar el estado

```bash
docker compose ps
```

Después de completar el arranque, los componentes principales deben aparecer en estado:

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

La interfaz permite realizar la demostración principal. Los Swagger pueden utilizarse para revisar y probar directamente las APIs.

---

# 🎬 Modo de demostración

La configuración normal utiliza una capacidad de **100 espacios** y un umbral de **10**.

Para una demostración más rápida en PowerShell puede utilizarse temporalmente una capacidad menor:

```powershell
$env:CAPACIDAD_ESTACIONAMIENTO="10"
$env:UMBRAL_POCOS_ESPACIOS="2"

docker compose up -d --force-recreate disponibilidad
```

Esto permite alcanzar con menos movimientos los estados:

```text
DISPONIBLE
POCOS_ESPACIOS
LLENO
```

Al finalizar la demostración se debe restaurar la configuración normal:

```powershell
Remove-Item Env:CAPACIDAD_ESTACIONAMIENTO
Remove-Item Env:UMBRAL_POCOS_ESPACIOS

docker compose up -d --force-recreate disponibilidad
```

---

# 🧪 Pruebas y validación

El proyecto incluye pruebas automatizadas y escenarios de extremo a extremo que permiten comprobar tanto las reglas internas como la comunicación real mediante Kafka.

## Validación completa en Windows

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\validar_entrega.ps1
```

## Validación completa en Linux o Bash

```bash
bash scripts/validar_entrega.sh
```

La validación final obtuvo:

```text
26 passed
```

También se comprobaron los siguientes recorridos E2E:

```text
Control de Acceso → Kafka → Disponibilidad
Disponibilidad → Kafka → Notificaciones
```

El procedimiento verificó además la interfaz, restauró la configuración normal y finalizó con:

```text
VALIDACION COMPLETA: OK
```

La evidencia detallada se encuentra en:

```text
docs/RESULTADO_PRUEBAS.md
```

---

## 📚 Documentación técnica

El documento principal de la entrega es:

📄 [Documento Técnico del Proyecto - Can I Park?](docs/Can_I_Park_Documento_Tecnico_Proyecto.pdf)

También se mantiene documentación complementaria dentro del repositorio:

| Documento | Contenido |
| --- | --- |
| [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) | Arquitectura e interacción del sistema |
| [`docs/DECISIONES.md`](docs/DECISIONES.md) | Decisiones técnicas tomadas durante el desarrollo |
| [`docs/PRUEBAS.md`](docs/PRUEBAS.md) | Estrategia y procedimientos de prueba |
| [`docs/RESULTADO_PRUEBAS.md`](docs/RESULTADO_PRUEBAS.md) | Resultados de la validación final |
| [`docs/REVISION_RUBRICA.md`](docs/REVISION_RUBRICA.md) | Revisión interna de requisitos y evidencias |

La documentación específica de cada componente se encuentra en:

```text
docs/componentes/PLATAFORMA_KAFKA.md
docs/componentes/CONTROL_ACCESO.md
docs/componentes/DISPONIBILIDAD.md
docs/componentes/NOTIFICACIONES.md
docs/componentes/INTERFAZ_DEMO.md
```

Las capturas utilizadas como evidencia se encuentran en:

```text
docs/evidencias/
```

---

## ⏹️ Detener el proyecto

Para detener todos los componentes:

```bash
docker compose down
```

---

# 👥 Integrantes del equipo

| Nombre | Carnet |
| --- | --- |
| Douglas Isaac Barrera Magaña | `BM22025` |
| Ricardo Enrique Heredia Ramos | `HR21024` |
| Gabriel Omar Calderón Calderón | `CC22060` |
| Douglas Enrique Sigüenza Quele | `SQ22005` |
| Fernando José Barraza Álvarez | `BA22025` |

---

## 🎓 Universidad de El Salvador

**Facultad Multidisciplinaria de Occidente**<br>
**Ingeniería en Desarrollo de Software**<br>
**Desarrollo y Reutilización de Software**<br>
**Ciclo II/2026**