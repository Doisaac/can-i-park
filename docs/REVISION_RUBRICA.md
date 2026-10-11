# Revisión contra la rúbrica

La revisión se organizó con los cuatro criterios de la actividad.

## 1. Implementación de los ejercicios — 30 %

Elementos presentes:

- dos microservicios principales independientes;
- Kafka entre recepción y procesamiento;
- tercer microservicio de Notificaciones integrado en el arranque por defecto;
- Dockerfile por servicio;
- Docker Compose;
- healthchecks;
- manejo de errores de publicación;
- idempotencia;
- commit de offsets después del procesamiento;
- scripts E2E contra Kafka real ejecutables desde un entorno Docker reproducible;
- interfaz de demostración.

Para cerrar este criterio antes de entregar se debe ejecutar `scripts/validar_entrega.ps1` o su equivalente `.sh` y conservar los archivos de evidencia generados.

## 2. Calidad del código — 30 %

Elementos presentes:

- responsabilidades separadas;
- nombres descriptivos;
- dominio fuera de las rutas HTTP;
- configuración por variables de entorno;
- logging en puntos relevantes;
- validación Pydantic;
- manejo de fallos de publicación;
- workers con reconexión básica;
- comentarios breves solo en decisiones no obvias;
- pruebas automatizadas.

## 3. Reutilización y modularidad — 30 %

Elementos presentes:

- paquete instalable `canipark_shared`;
- contratos únicos para productor y consumidores;
- utilidades Kafka reutilizables;
- `Protocol` para sustituir el publicador durante pruebas;
- microservicios sin imports del código interno de otros servicios;
- contenedores independientes.

## 4. Documentación y presentación — 10 %

Elementos presentes:

- README con instalación, ejecución, endpoints y pruebas;
- arquitectura;
- decisiones de diseño;
- estrategia de pruebas;
- resultado de pruebas locales;
- scripts de demo y validación;
- interfaz en `http://localhost:8080`;
- Swagger de cada API.

## Checklist final del equipo

Antes de entregar:

- [ ] Confirmar que Docker Desktop/Docker Engine esté disponible.
- [ ] Ejecutar `python -m pytest`.
- [ ] Ejecutar la validación completa con Docker.
- [ ] Confirmar que se generaron `EVIDENCIA_E2E.txt` y `EVIDENCIA_NOTIFICACIONES_E2E.txt`.
- [ ] Abrir la interfaz y realizar una entrada/salida manual.
- [ ] Revisar `docker compose  ps`.
- [ ] Practicar la explicación Acceso -> Kafka -> Disponibilidad.
- [ ] Cada integrante debe poder explicar qué reutiliza `shared`.
- [ ] Mantener el repositorio público y organizado.

La validación final del cumplimiento de la rúbrica se realizará después de ejecutar las pruebas completas y revisar las evidencias generadas.
