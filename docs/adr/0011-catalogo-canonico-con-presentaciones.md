# ADR-0011: Usar un catálogo canónico con presentaciones y precio por unidad

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27)
- **Fecha:** 2026-11-06 (registro del Corte 1, C1-AS2-E2); archivado en el repositorio el 2026-11-27
- **Autores:** Equipo; redactado con apoyo de IA
- **Escenarios de calidad afectados:** EC-06 (pregunta de diseño 4)
- **Métricas que lo verifican:** M-02, M-05, D-05

## Contexto
Un producto aparece con nombres y presentaciones distintas («Arroz Diana 500 g», «arroz diana x 1
kg»). Comparar precios absolutos entre presentaciones engaña al consumidor.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| **A. Producto canónico con presentaciones; el reportante elige de una lista** | Comparación por unidad correcta, probada con TDD | Un producto nuevo debe crearse en el catálogo antes de reportarlo |
| B. Texto libre con agrupación automática | Más flexible para el usuario | Más errores (M-02) y duplicados (D-05) |

## Decisión
Alternativa A. `Producto` (nombre, marca, categoría, nombre normalizado) con varias `Presentacion`
(cantidad, unidad, código de barras opcional). La comparación usa el precio por unidad base ($/kg,
$/L, $/und) y solo compara presentaciones de la misma magnitud. Los posibles duplicados se detectan
por similitud de nombre normalizado para revisión del moderador.

## Consecuencias
- (+) La comparación por unidad es correcta y está probada con TDD.
- (−) Un producto nuevo requiere crearse en el catálogo antes de reportarlo.
- Según la encuesta, el 90 % de los consumidores compara por precio total o por marca: la interfaz
  muestra primero el precio total y la presentación, y el precio por unidad como dato secundario.
  El orden no cambia.

## Evidencia en el código
- `apps/catalogo/models.py`: `Producto`, `Presentacion` (restricción `presentacion_unica`) y
  `Marca` como entidad ([ADR-0019](0019-panel-de-administracion-y-roles.md)).
- `apps/catalogo/domain/normalizacion.py`, `duplicados.py` y `codigo_barras.py`, con TDD.
