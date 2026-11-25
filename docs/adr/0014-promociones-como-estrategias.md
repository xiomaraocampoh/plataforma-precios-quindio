# ADR-014: Modelar las promociones como estrategias, fuera del criterio de orden

- **Estado:** Aceptado por el equipo el 2026-11-25 (D-3 = conservar `es_promocion` y agregar `promociones`)
- **Fecha:** 2026-11-16
- **Autores:** Equipo (borrador C2-AS2-E4 del Drive, 14-nov-2026); adaptado al repositorio con apoyo de IA
- **Escenarios de calidad afectados:** EC-06
- **Métricas que lo verifican:** M-06

## Contexto
La guía exige que el orden de la comparación responda solo a los criterios declarados y que todo
contenido promocional se distinga del resultado en el 100 % de los casos (EC-06; pregunta de diseño
7; guía §12.1). La Ley 1480 de 2011 regula la información de precios y promociones.

En `main`, `ResultadoComparacion.es_promocion` ya existe en el dominio, el serializer público y la
plantilla, pero **nadie lo asigna** (siempre es `False`). La única función que ordena es
`_clave_neutral`, que no usa atributos comerciales.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| Estrategias que calculan el precio efectivo; el orden usa el precio regular y la promoción es etiqueta | Verificable con pruebas; agregar un tipo es una clase nueva; imposible alterar el orden sin tocar `_clave_neutral` | El consumidor debe mirar la etiqueta para ver el ahorro |
| Ordenar por precio con promoción | Muestra el ahorro de inmediato | Mezcla condiciones de compra con el precio y puede favorecer a quien más promociones publica |
| Sección de «destacados» pagos | Modelo de ingresos | Riesgo ético y legal; percepción de parcialidad |

## Decisión
Cada tipo de promoción implementa una interfaz común (patrón *Strategy*: `DescuentoPorcentual`,
`PrecioEspecial`, `PagueXLleveY`) que calcula el precio efectivo por unidad y valida su vigencia. El
orden sigue usando el precio regular por unidad. La promoción se muestra como etiqueta con su precio
efectivo y condiciones. «Pague X lleve Y» nunca participa en el orden porque exige comprar varias
unidades.

**D-3 (decidido el 2026-11-25).** Se **conserva** `es_promocion` en cada resultado (la etiqueta) y se
**agrega** un arreglo `promociones` en la respuesta de la comparación, como cambio aditivo en `/v1`
(ningún campo existente cambia ni desaparece). El arreglo es la fuente de las condiciones: tipo,
precio efectivo, vigencia, motivo y condiciones. Es coherente con la referencia SIPSA, que ya se
muestra aparte. Ver el [análisis de impacto](../arquitectura/analisis-impacto-modulo-comercial.md#61-decisión-d-3-cómo-viajan-las-promociones-hacia-el-cliente).

Las estrategias viven en `comercios/domain/promociones.py` y llegan a la comparación por el puerto del
ADR-012. La función `aplicar_a_cantidad(promocion, cantidad)` queda disponible para la canasta
(ADR-0029).

## Consecuencias
- (+) M-06 = 100 % verificable con una prueba que compara el orden con y sin promociones.
- (+) Agregar un tipo de promoción es una clase nueva, sin tocar las demás.
- (−) El consumidor debe mirar la etiqueta para ver el ahorro.
- Las condiciones y fechas deben verse junto al precio (hallazgo de la encuesta: desconfianza ante precios inflados antes de una promoción, poca duración y fecha de caducidad).
