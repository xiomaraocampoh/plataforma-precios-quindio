# Cuestionario SUS (System Usability Scale)

Escala de usabilidad de John Brooke (1996), de uso libre. Versión en español del equipo. Se responde
**al terminar todas las tareas**, sin ayuda del moderador.

**Participante:** P__  **Fecha:** ____________

Marca un número por afirmación: **1 = totalmente en desacuerdo**, **5 = totalmente de acuerdo**.
Responde rápido, con tu primera impresión. Si no sabes qué responder, marca 3.

| # | Afirmación | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| 1 | Creo que me gustaría usar esta plataforma con frecuencia. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 2 | Encontré la plataforma innecesariamente compleja. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 3 | Pensé que la plataforma era fácil de usar. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 4 | Creo que necesitaría el apoyo de una persona experta para poder usar esta plataforma. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 5 | Encontré que las distintas funciones de la plataforma estaban bien integradas. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 6 | Pensé que había demasiadas inconsistencias en la plataforma. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 7 | Imagino que la mayoría de las personas aprendería a usar esta plataforma muy rápido. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 8 | Encontré la plataforma muy engorrosa de usar. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 9 | Me sentí con mucha confianza al usar la plataforma. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 10 | Necesité aprender muchas cosas antes de poder usar esta plataforma. | ☐ | ☐ | ☐ | ☐ | ☐ |

## Cálculo del puntaje

Para cada participante, con las respuestas *r₁ … r₁₀* (de 1 a 5):

- Ítems **impares** (1, 3, 5, 7, 9), de tono positivo: aportan *rᵢ − 1*.
- Ítems **pares** (2, 4, 6, 8, 10), de tono negativo: aportan *5 − rᵢ*.

```
SUS = 2,5 × [ (r₁ − 1) + (5 − r₂) + (r₃ − 1) + (5 − r₄) + (r₅ − 1)
            + (5 − r₆) + (r₇ − 1) + (5 − r₈) + (r₉ − 1) + (5 − r₁₀) ]
```

El resultado va de 0 a 100. No es un porcentaje. El puntaje del producto es el **promedio** de los
participantes.

**Ejemplo de cálculo con respuestas hipotéticas** (no es un resultado de la prueba): 4, 2, 4, 1, 4,
2, 5, 2, 4, 2 → impares (3 + 3 + 3 + 4 + 3) = 16; pares (3 + 4 + 3 + 3 + 3) = 16; SUS = 2,5 × 32 = **80**.

**Interpretación habitual:** 68 es el promedio de referencia. Por debajo de 68 hay problemas de
usabilidad que atender; 80 o más es bueno.

Las respuestas se pasan a [`sus.csv`](sus.csv): una fila por participante, columnas `p1` a `p10`.
`scripts/calcular_usabilidad.py` calcula cada puntaje y el promedio.
