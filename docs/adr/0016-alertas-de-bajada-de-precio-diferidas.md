# ADR-016: Diferir las alertas de bajada de precio

- **Estado:** Propuesto
- **Fecha:** 2026-11-16
- **Autores:** Equipo (borrador C2-AS2-E4 del Drive, 14-nov-2026); adaptado al repositorio con apoyo de IA
- **Escenarios de calidad afectados:** EC-05
- **Métricas que lo verifican:** M-17

## Contexto
La guía deja las alertas de bajada de precio (RF-C08) como funcionalidad opcional «a decisión del
equipo». Exigen notificaciones y una tarea programada nueva, y sumarían esfuerzo a la línea base de
M-17 (≈ 12 h según el borrador).

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| Diferir (no implementar en el Corte 3) | Prioriza los requisitos obligatorios y la evaluación | El consumidor no recibe avisos |
| Implementar en el Corte 3 | Más completo | Suma ≈ 12 h y un ADR; arriesga la medición de EC-05 |

## Decisión
No se implementan en el Corte 3. Si se retoman, se usará una tarea programada que compare el último
precio con el anterior y envíe un correo, **sin cambiar el núcleo**.

## Consecuencias
- (+) No altera la línea base de 79 h ni el calendario del Corte 3.
- (−) Una funcionalidad opcional queda fuera del producto entregado.
