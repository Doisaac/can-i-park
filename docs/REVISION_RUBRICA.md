# Revisión contra la rúbrica

Este documento relaciona los criterios de evaluación de la actividad con las evidencias implementadas y verificadas en **Can I Park?**.

La revisión se organiza según los cuatro criterios establecidos en la rúbrica.

---

## 1. Implementación de los ejercicios — 30 %

El proyecto cumple el flujo requerido para el Tema 6 mediante microservicios independientes comunicados a través de Apache Kafka.

Elementos implementados:

- Control de Acceso recibe los movimientos de entrada y salida.
- Disponibilidad consume y procesa los movimientos.
- Notificaciones consume los cambios de estado del estacionamiento.
- Kafka permite la comunicación asíncrona entre servicios.
- Cada microservicio posee su propio Dockerfile.
- Docker Compose orquesta todos los componentes.
- Se implementaron healthchecks.
- Se manejan errores de publicación.
- Disponibilidad implementa idempotencia por `evento_id`.
- Los consumidores realizan commit manual de offsets después del procesamiento.
- Se incluyen pruebas E2E utilizando Kafka real.
- Se incluye una interfaz web para demostrar el funcionamiento completo.

### Validación realizada

La validación final ejecutó correctamente las pruebas automatizadas:

```text
26 passed
```

También se verificaron correctamente los flujos:

```text
Acceso -> Kafka -> Disponibilidad
```

y:

```text
Disponibilidad -> Kafka -> Notificaciones
```

La interfaz respondió correctamente y la validación terminó con:

```text
VALIDACION COMPLETA: OK
```

---

## 2. Calidad del código — 30 %

La solución mantiene responsabilidades separadas y utiliza una estructura organizada por componentes.

Elementos presentes:

- nombres descriptivos;
- lógica de dominio separada de las rutas HTTP;
- configuración mediante variables de entorno;
- validación de contratos con Pydantic;
- logging en puntos relevantes;
- manejo de fallos de publicación;
- workers Kafka independientes;
- reconexión básica de consumidores;
- comentarios únicamente en decisiones no evidentes;
- pruebas automatizadas;
- separación entre API, dominio y comunicación Kafka.

La lógica principal de Disponibilidad se encuentra en `GestorDisponibilidad`, lo que permite probar las reglas del estacionamiento sin depender directamente de FastAPI ni Kafka.

---

## 3. Reutilización y modularidad — 30 %

El proyecto utiliza componentes compartidos para evitar duplicación y mantener contratos consistentes entre microservicios.

Elementos presentes:

- paquete reutilizable `canipark_shared`;
- contratos de eventos compartidos;
- enumeraciones comunes;
- utilidades reutilizables para productores y consumidores Kafka;
- serialización JSON centralizada;
- `Protocol` para sustituir el publicador durante pruebas;
- inyección de dependencias;
- microservicios sin imports del código interno de otros servicios;
- contenedores independientes.

La comunicación de negocio entre servicios se realiza mediante eventos Kafka, permitiendo mantener bajo acoplamiento y responsabilidades independientes.

Los patrones y principios aplicados se encuentran documentados en:

```text
docs/DECISIONES.md
```

---

## 4. Documentación y presentación — 10 %

El proyecto incluye documentación técnica y material de apoyo para ejecución, validación y presentación.

Elementos presentes:

- README con descripción, arquitectura, ejecución y pruebas;
- explicación de reutilización y modularidad;
- patrones y principios utilizados;
- documentación de arquitectura;
- decisiones de diseño;
- estrategia de pruebas;
- resultados reales de validación;
- documentación individual de cada componente;
- scripts de demostración y validación;
- evidencias visuales;
- interfaz web;
- Swagger para las tres APIs.

La interfaz está disponible en:

```text
http://localhost:8080
```

Swagger:

```text
Control de Acceso: http://localhost:8001/docs
Disponibilidad:    http://localhost:8002/docs
Notificaciones:    http://localhost:8003/docs
```

---

## Evidencias de validación

La validación completa confirmó:

- 26 pruebas automatizadas aprobadas.
- E2E Acceso -> Kafka -> Disponibilidad aprobado.
- E2E Disponibilidad -> Kafka -> Notificaciones aprobado.
- Interfaz web verificada.
- Configuración normal restaurada a capacidad 100 y umbral 10.
- Todos los componentes principales en estado `healthy`.

Las evidencias detalladas se encuentran en:

```text
docs/RESULTADO_PRUEBAS.md
docs/evidencias/
```

---

## Checklist final del equipo

- [x] Docker disponible y operativo.
- [x] Pruebas automatizadas ejecutadas.
- [x] Validación completa ejecutada con Docker.
- [x] Flujo Acceso -> Kafka -> Disponibilidad validado.
- [x] Flujo Disponibilidad -> Kafka -> Notificaciones validado.
- [x] Evidencias E2E generadas.
- [x] Interfaz verificada manualmente.
- [x] Estado de los contenedores revisado.
- [x] Configuración normal restaurada.
- [x] Documentación técnica completada.
- [x] Reutilización mediante `canipark_shared` documentada.
- [x] Repositorio organizado para la entrega.

---

## Resultado de la revisión

Con las validaciones realizadas, el proyecto presenta evidencia para los cuatro criterios de la rúbrica:

```text
Implementación                  -> Cumplido
Calidad del código              -> Cumplido
Reutilización y modularidad     -> Cumplido
Documentación y presentación    -> Cumplido
```

La entrega queda preparada para la revisión final del equipo y posterior integración a `main`.
