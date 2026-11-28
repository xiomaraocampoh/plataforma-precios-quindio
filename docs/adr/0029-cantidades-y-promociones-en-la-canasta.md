# ADR-0029: Cantidades, presentaciones y promociones «pague X lleve Y» en la canasta

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27); las cantidades están implementadas y el ahorro por promociones «pague X lleve Y» en la canasta está pendiente (no existe `canasta/domain/promociones.py`)
- **Fecha:** 2026-11-24
- **Autores:** Equipo; borrador con apoyo de IA, pendiente de revisión humana
- **Escenarios relacionados:** EC-07 (Anexo 1), EC-06
- **Métricas que lo verifican:** M-24, M-05, M-06, M-02
- **Plantilla:** 8.1 del Anexo 1 (adaptada de Nygard, 2011)

## Contexto
La persona pide cantidades («2 kg de arroz», «3 leches de 1 L»), pero las tiendas venden
presentaciones (500 g, 1 kg, 5 kg) y una misma tienda puede tener varias. El Anexo exige un total
«con precios normalizados por unidad de medida» y pregunta cómo se aplican las promociones «pague X
lleve Y» a las cantidades.

Hechos (*verificados*): `catalogo/domain/normalizacion.py` ya ofrece `a_unidad_base`,
`precio_por_unidad` (a $/kg, $/L o $/und, redondeo a centavos) y `exigir_comparables` (g con kg, ml
con L; nunca kg con L). El ADR-014 decide que las promociones se modelan como estrategias
(`PagueXLleveY`, entre otras) y **nunca participan en el orden**. El módulo comercial que las
implementa **no está construido** en `main`.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| **A. Total normalizado: cantidad pedida en unidad base × precio por unidad de la presentación más conveniente; los empaques se informan** | Cumple literalmente «normalizado por unidad»; compara tiendas con tamaños distintos; simple de probar | El total es una estimación: la persona compra empaques enteros |
| B. Comprar empaques enteros: ⌈cantidad / tamaño⌉ de la presentación más barata por unidad | Costo real de la góndola | Penaliza a la tienda que solo tiene el empaque grande; mezcla «cuánto cuesta» con «cuánto sobra» |
| C. Combinación exacta de presentaciones de menor costo (tipo mochila) | El costo más realista | Complejidad desproporcionada para el plazo de dos semanas; difícil de explicar a la persona |
| Promociones dentro del total | Refleja el ahorro | Haría que un atributo comercial cambie el orden (contradice ADR-014 y EC-06) |

## Decisión
**A**, con las promociones como información aparte.

1. **Validación de la cantidad.** `ItemCanasta(producto, cantidad, unidad)` exige `cantidad > 0`
   (`Decimal`) y que la unidad sea compatible con las presentaciones del producto
   (`exigir_comparables`); si no, error de validación (M-02). La cantidad se convierte con
   `a_unidad_base` (2 kg → 2 kg; 500 g → 0,5 kg; 3 und → 3 und).
2. **Presentación usada por establecimiento.** Entre las presentaciones del producto con precio
   vigente en ese establecimiento, la de **menor precio por unidad** (`precio_por_unidad`); empate:
   la de menor tamaño y luego el menor id.
3. **Costo del producto** = cantidad en unidad base × precio por unidad de esa presentación,
   redondeado a centavos (`ROUND_HALF_UP`) **por producto**; el total es la suma de esos costos. Se
   muestran la presentación usada y los **empaques sugeridos** (⌈cantidad / tamaño⌉), sin sumar el
   sobrante.
4. **Promociones «pague X lleve Y».** Con los empaques sugeridos `n` de la presentación usada y una
   promoción vigente para ella, el ahorro posible es `⌊n / Y⌋ × (Y − X) × precio del empaque`. Se
   muestra como «Ahorro posible con promoción» junto a la opción; **no cambia el total comparado ni el
   orden** (ADR-014, ADR-0028). Si `n < Y`, se informa «Lleva Y y paga X» sin ahorro calculado.
5. **De dónde vienen las promociones.** `canasta.domain` define un puerto (`Protocol`)
   `PromocionesVigentes`; el módulo comercial lo implementará y se registrará al arrancar (opción B de
   DP-1, análisis del módulo comercial). Mientras `comercios` no exista, el adaptador por defecto no
   devuelve promociones y la canasta funciona igual. La canasta **nunca importa** `apps.comercios`.

## Consecuencias
- (+) El total compara precios, no tamaños de empaque: es neutral entre una tienda de barrio con
  empaques pequeños y un supermercado con empaques grandes.
- (+) Reutiliza `precio_por_unidad` (CLAUDE.md: nunca a mano) y las estrategias de promoción del
  ADR-014.
- (+) La canasta no depende del calendario del módulo comercial.
- (−) El total es una estimación; la interfaz lo dice («Total estimado según el precio por unidad») y
  muestra los empaques sugeridos.
- (−) Un ahorro por promoción visible pero fuera del total puede parecer contradictorio; se acepta por
  neutralidad y se explica en la etiqueta.
- **Riesgo:** si el módulo comercial no se fusiona en el corte, RF-A1-09 queda sin datos reales; se
  demuestra con pruebas de dominio con promociones falsas.
- **Evidencia que haría revisar la decisión:** pruebas con usuarios en las que el total estimado se
  aleje mucho de lo que la persona pagaría (por ejemplo, productos que solo se venden en empaques
  grandes).

## Verificación
1. **M-05:** pruebas unitarias de conversión (g frente a kg, ml frente a L, und), cantidad 0 y
   negativa (rechazo), unidad incompatible (rechazo, M-02) y redondeo.
2. **Presentación usada:** pruebas con varias presentaciones en la misma tienda, empates de precio por
   unidad y presentación vencida (no cuenta).
3. **Promociones:** pruebas de `pague 2 lleve 3` con `n = 2` (sin ahorro), `n = 3` y `n = 7`, con un
   adaptador falso del puerto.
4. **M-06:** el orden de la canasta es idéntico con y sin promociones (prueba compartida con
   ADR-0028).
5. **Dependencias:** contrato de `import-linter` que prohíbe `apps.canasta → apps.comercios`.
