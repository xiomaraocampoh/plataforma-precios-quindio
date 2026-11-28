# ADR-0002: Usar Django y DRF con renderizado en el servidor e HTMX

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27)
- **Fecha:** 2026-11-06 (registro del Corte 1, C1-AS2-E2); archivado en el repositorio el 2026-11-27
- **Autores:** Equipo; redactado con apoyo de IA
- **Escenarios de calidad afectados:** EC-01, EC-05
- **Métricas que lo verifican:** M-01, M-03, M-13

## Contexto
El equipo definió Python con Django, HTMX y una API REST. El uso es sobre todo desde el celular, a
menudo con red limitada, y la guía exige una API documentada.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| **A. Django + HTMX + DRF** | Páginas livianas; poco JavaScript; una sola base de código; OpenAPI con drf-spectacular | Menos interactividad que una SPA; modo sin conexión limitado |
| B. API en Django + SPA (React o Vue) | Interfaz rica; modo sin conexión con *service worker* | Dos bases de código; paquete inicial pesado en 3G; más esfuerzo |

## Decisión
Alternativa A. Las vistas de Django devuelven la página completa o solo el fragmento según la
cabecera de HTMX, y htmx se sirve desde archivos estáticos propios, sin CDN. La API REST v1 con DRF
atiende a clientes externos y a las pruebas de contrato.

## Consecuencias
- (+) Menos bytes por interacción, favorable a EC-01.
- (+) La misma capa de servicios atiende las vistas HTMX y la API.
- (−) La cola sin conexión requiere un script pequeño propio ([ADR-0009](0009-registro-tolerante-a-conectividad-limitada.md)).

## Evidencia en el código
- `static/vendor/htmx.min.js` (htmx versionado en el repositorio).
- `drf_spectacular` en `config/settings/base.py`; esquema en `/api/schema/` y documentación en
  `/api/docs/`, que respondieron 200 en la prueba de humo local y en Render.
