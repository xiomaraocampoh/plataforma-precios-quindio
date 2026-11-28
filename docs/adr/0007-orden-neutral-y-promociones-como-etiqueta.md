# ADR-0007: Ordenar con un criterio neutral único y mostrar las promociones como etiqueta

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27)
- **Fecha:** 2026-11-06 (registro del Corte 1, C1-AS2-E2); archivado en el repositorio el 2026-11-27
- **Autores:** Equipo; redactado con apoyo de IA
- **Escenarios de calidad afectados:** EC-06 (pregunta de diseño 7)
- **Métricas que lo verifican:** M-06

## Contexto
La guía exige que el orden responda solo a criterios declarados y que el contenido promocional se
distinga en el 100 % de los casos. La Ley 1480 de 2011 regula la información de precios y
promociones.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| **A. Una sola función de orden en el dominio; la promoción como atributo aparte** | Verificable con pruebas; imposible de alterar sin tocar una función identificada | Se renuncia a monetizar posiciones destacadas |
| B. Sección separada de «destacados» pagos | Modelo de ingresos | Riesgo ético y legal; percepción de parcialidad |

## Decisión
Alternativa A. El orden es el menor precio por unidad de medida y, en empate, el nombre del
establecimiento. El criterio se muestra sobre los resultados. Las promociones llevan una etiqueta
visible y no participan del orden ([ADR-0014](0014-promociones-como-estrategias.md)).

## Consecuencias
- (+) M-06 = 100 %, probado con una prueba que compara el orden con y sin promociones.
- (+) Equidad entre comercios grandes y pequeños.

## Cambio en la implementación
El desempate se amplió para que el orden sea siempre determinista: precio por unidad, luego nombre
del establecimiento sin distinguir mayúsculas y, por último, su identificador. El criterio sigue
siendo único y declarado. La propuesta del consolidado de desempatar por confianza y fecha
(decisión D-2) no se adoptó.

## Evidencia en el código
- `apps/comparacion/domain/ranking.py`: `_clave_neutral` y `ordenar_neutral`.
- `tests/unit/comparacion/test_ranking.py`: la promoción no altera el orden.
