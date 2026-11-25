# ADR-012: Incorporar el módulo comercial como un módulo nuevo

- **Estado:** Aceptado por el equipo el 2026-11-25 (DP-1 = opción B, puerto y registro de extensiones)
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

**Mecanismo de integración (DP-1, decidido el 2026-11-25): opción B, puerto y registro de
extensiones.** El borrador del Drive decía que «el núcleo conoce el selector comercial, consumido
desde el selector de comparación», lo que exigiría relajar el contrato `comercios-no-adelantado`. El
equipo eligió en su lugar:

- `comparacion` define el **puerto**: un `Protocol` en su dominio (`comparacion/domain/extensiones.py`)
  con los datos que una extensión puede aportar (precio oficial y promociones por establecimiento y
  presentación). Es Python puro.
- `core` guarda el **registro de extensiones** (`core/extensiones.py`): registrar y listar por nombre
  de punto, sin conocer a nadie.
- `comercios` **se registra al arrancar**, en `ComerciosConfig.ready()`.
- `comparacion` **nunca importa** `comercios`. La dependencia es comercios → comparacion (permitida) y
  el contrato `comercios-no-adelantado` se conserva en *kept*.
- La **canasta** (Corte 3, ADR-0029) usará este mismo puerto para las promociones.

Detalle y costo en el [análisis de impacto](../arquitectura/analisis-impacto-modulo-comercial.md#5-decisión-dp-1-cómo-consulta-la-comparación-al-módulo-comercial)
y la línea base en el [registro de esfuerzo](../arquitectura/registro-esfuerzo-modulo-comercial.md).

## Consecuencias
- (+) El impacto es acotado y medible: M-17 y M-18 se calculan sobre un módulo nuevo y unos pocos puntos de extensión.
- (+) Con el puerto, el contrato se conserva y M-18 puede mantenerse en 0.
- (−) Una abstracción nueva (puerto y registro) que el equipo debe entender; su costo orientativo es de 3 h, fuera de las 79 h de la línea base.
- (−) Si el módulo comercial no está instalado, la comparación funciona igual, pero sin datos oficiales: el puerto vacío es un caso que hay que probar.
- Evidencia que haría revisar esta decisión: que el puerto resulte más costoso que las 3 h estimadas, o que el módulo necesite tocar tablas del núcleo.
