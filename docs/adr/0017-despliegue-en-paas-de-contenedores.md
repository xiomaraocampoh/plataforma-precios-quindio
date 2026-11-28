# ADR-0017: Desplegar en un PaaS de contenedores (Render)

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27); proveedor elegido: Render (decisión D-11)
- **Fecha:** 2026-11-16
- **Autores:** Equipo (borrador C2-AS2-E4 del Drive, 14-nov-2026); adaptado al repositorio con apoyo de IA
- **Escenarios de calidad afectados:** EC-04, M-21
- **Métricas que lo verifican:** M-08, M-09, M-10, M-21

## Contexto
La guía exige un despliegue reproducible del sistema y que el equipo decida el proveedor, el modelo de
servicio y las herramientas, documentando la decisión en un ADR (Fase 3). El núcleo ya tiene un
`Dockerfile`, `docker-compose.yml` de desarrollo y un CI en GitHub Actions con PostgreSQL 16 que
pasa en verde. **No existe todavía** un `docker-compose` de producción ni un despliegue en la nube.

Se comparan servicios equivalentes de los tres grandes proveedores con el marco *Well-Architected*
(rendimiento, confiabilidad, seguridad, costos, excelencia operativa).

## Alternativas consideradas
| Componente | Azure | AWS | Google Cloud |
|---|---|---|---|
| Aplicación (contenedor) | App Service for Containers | App Runner | Cloud Run |
| Base de datos | Azure Database for PostgreSQL (Flexible Server) | Amazon RDS for PostgreSQL | Cloud SQL for PostgreSQL |
| Caché | Azure Cache for Redis | ElastiCache for Redis | Memorystore for Redis |
| Tareas programadas | WebJobs / Container Apps Jobs | EventBridge Scheduler | Cloud Scheduler + Cloud Run Jobs |

Criterios para elegir: costo en créditos educativos, PostgreSQL y Redis gestionados, despliegue
directo de la imagen, réplicas para 500 usuarios, latencia desde Colombia, observabilidad y
aprendizaje del equipo. Modelos descartados: IaaS (más operación) y *serverless* puro (Django + HTMX
encaja mal con funciones efímeras; ver el documento de arquitectura v1).

## Decisión
**PaaS de contenedores sobre IaaS**, con menos operación para el equipo y escalado horizontal en
quincena. **El proveedor, el plan, la región y la URL están pendientes** y se registrarán aquí cuando
el equipo los decida y haya un despliegue verificado. La imagen Docker y la configuración por
variables de entorno hacen la elección reversible.

## Consecuencias
- (+) Despliegue reproducible desde el CI.
- (−) Dependencia de los servicios gestionados del proveedor elegido.
- Evidencia que falta (*planificado*): construcción de la imagen de producción, despliegue, `/healthz/` en verde y la prueba de carga con k6 contra la URL desplegada (EC-04; umbral p95 < 2 s, error < 1 %). Ninguna de estas mediciones existe aún.
