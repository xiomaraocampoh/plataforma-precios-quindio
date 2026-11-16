# ADR-012: Incorporar el módulo comercial como un módulo nuevo

- **Estado:** Propuesto (pendiente de la decisión DP-1 sobre el mecanismo de integración)
- **Fecha:** 2026-11-16
- **Autores:** Equipo (borrador C2-AS2-E4 del Drive, 14-nov-2026); adaptado al repositorio con apoyo de IA
- **Escenarios de calidad afectados:** EC-05, EC-06
- **Métricas que lo verifican:** M-17, M-18

## Contexto
La guía introduce el módulo comercial como un cambio de alcance sobre un núcleo ya construido. El
cambio debe incorporarse sin rediseñar el núcleo y de forma medible (EC-05). En el código de `main`,
`apps/comercios` es una carpeta reservada (comentada en `LOCAL_APPS`) y el contrato
`comercios-no-adelantado` de `import-linter` prohíbe que el núcleo la importe.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| A. Módulo nuevo dentro del monolito | Impacto acotado y medible; reutiliza BD, caché y autenticación | Comparte despliegue con el núcleo |
| B. Servicio independiente con su propia API | Aislamiento total | Costo operativo y de red desproporcionado para tres personas; consistencia distribuida |
| C. Extender los módulos `precios` y `comparacion` | Menos archivos nuevos | Mezcla responsabilidades; el cambio tocaría todo el núcleo y arruinaría EC-05 |

## Decisión
Se adopta **A**: un módulo nuevo `apps/comercios` con las mismas capas que el resto. El núcleo no
importa el módulo comercial.

**Mecanismo de integración (pendiente, DP-1).** El borrador del Drive decía que «el núcleo conoce el
selector comercial, consumido desde el selector de comparación». Eso exigiría relajar el contrato
`comercios-no-adelantado`. Se recomienda en su lugar un **puerto** definido por `comparacion` y un
registro de extensiones en `core`, de modo que `comercios` se registre al arrancar y `comparacion`
nunca lo importe. Detalle y costo en el [análisis de impacto](../arquitectura/analisis-impacto-modulo-comercial.md#5-decisión-dp-1-cómo-consulta-la-comparación-al-módulo-comercial).

## Consecuencias
- (+) El impacto es acotado y medible: M-17 y M-18 se calculan sobre un módulo nuevo y unos pocos puntos de extensión.
- (+) Con el puerto, el contrato se conserva y M-18 puede mantenerse en 0.
- (−) Con importación directa, el selector de comparación pasa a depender de un módulo más y el cambio de contrato debe contarse como estructural.
- Evidencia que haría revisar esta decisión: que el puerto resulte más costoso que las 3 h estimadas, o que el módulo necesite tocar tablas del núcleo.
