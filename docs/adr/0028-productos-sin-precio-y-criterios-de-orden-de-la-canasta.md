# ADR-0028: Productos sin precio vigente y criterios de orden declarados en la canasta

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27)
- **Fecha:** 2026-11-24
- **Autores:** Equipo; borrador con apoyo de IA, pendiente de revisión humana
- **Escenarios relacionados:** EC-07 (Anexo 1), EC-06
- **Métricas que lo verifican:** M-24, M-06
- **Plantilla:** 8.1 del Anexo 1 (adaptada de Nygard, 2011)

## Contexto
En Armenia casi ninguna tienda de barrio tiene precio vigente para todos los productos de una canasta
de 20. Si un producto sin precio se suma como cero, la tienda más incompleta parece la más barata:
es el error que EC-07 pide evitar en el 100 % de los casos. El Anexo exige además ordenar los
establecimientos «según criterios declarados al usuario» y la guía (§12) exige neutralidad: el orden
no puede depender de atributos comerciales.

El orden de la comparación por producto (`ranking.py::_clave_neutral`, ADR-007 del Drive) **no se
modifica**: la canasta ordena otra cosa (establecimientos con varios productos) y necesita su propia
regla, también declarada.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| Sumar los productos sin precio como cero | Trivial | Prohibido por el Anexo; engaña a la persona |
| Imputar un precio (mediana de la ciudad, SIPSA) a los faltantes | Totales siempre completos | Inventa un precio que la tienda no tiene; viola la credibilidad del dato (ISO/IEC 25012) |
| Mostrar solo las tiendas con todos los productos | Totales comparables | Con datos colaborativos, a menudo ninguna tienda queda; la persona no recibe respuesta |
| **Total parcial + lista explícita de faltantes + cobertura, con orden por cobertura y luego total** | Respuesta útil siempre; nada se inventa; el criterio es simple de explicar | Un total parcial puede leerse como completo si la interfaz no lo aclara |

## Decisión
1. **Modelo del resultado.** Para cada establecimiento, `calcular_canasta` produce: el total de los
   productos **con** precio vigente, la lista explícita de productos **sin** precio vigente, la
   cobertura como `n de m` y el detalle por producto. «Sin precio» es un estado distinto en el tipo de
   dato, no un precio cero: el total nunca lo recibe.
2. **Criterios de orden declarados** (`ordenar_opciones(resultados, criterio)`):

   | Criterio | Clave de orden | Texto que se muestra |
   |---|---|---|
   | `cobertura` (**por defecto**) | más productos disponibles → menor total → nombre del establecimiento (sin mayúsculas ni tildes) → id | «Ordenado por: más productos disponibles y luego menor total» |
   | `total` | menor total → más productos disponibles → nombre → id | «Ordenado por: menor total (los totales de tiendas incompletas no incluyen los productos que faltan)» |

   El id solo desempata para que el orden sea determinista. Ningún criterio usa promociones, perfil
   verificado, patrocinio ni ningún atributo comercial.
3. **Siempre visible.** La interfaz y la API devuelven el criterio usado («Ordenado por: …»); la
   persona puede cambiarlo. Cada opción incompleta muestra «Faltan k productos» y cada faltante lleva
   la marca «Sin precio vigente».
4. **Filtros** (municipio, barrio) solo reducen las opciones; no cambian la clave.

## Consecuencias
- (+) EC-07 (100 % sin sumar cero) queda en una regla de dominio verificable con TDD.
- (+) El criterio por defecto evita que una tienda con 3 de 20 productos encabece la lista.
- (+) EC-06: el orden es reproducible y explicable en una frase.
- (−) Con el criterio `total`, una tienda incompleta puede quedar primera; por eso el texto del
  criterio lo advierte y la cobertura se muestra junto al total.
- (−) Dos tiendas con la misma cobertura pero faltantes distintos se comparan por total aunque no
  cubran los mismos productos. Se acepta en el mínimo; la extensión (combinación de dos
  establecimientos) ayuda a la persona a completar la compra.
- **Evidencia que haría revisar la decisión:** pruebas con usuarios en las que la persona interprete
  el total parcial como completo.

## Verificación
1. **M-24 (EC-07):** pruebas unitarias en `tests/unit/canasta/` marcadas `# EC-07`: un producto sin
   precio nunca cambia el total; ninguna tienda tiene todos los productos; todas sin precio para un
   producto; precios vencidos que no cuentan.
2. **Orden:** pruebas de `ordenar_opciones` por criterio, con empates en cobertura, en total y en
   nombre.
3. **M-06 (EC-06):** prueba de integración que calcula la misma canasta con y sin promociones y con y
   sin perfil verificado, y compara el orden (debe ser idéntico).
4. **Interfaz:** prueba de integración que comprueba que «Ordenado por:» y «Sin precio vigente»
   aparecen en la respuesta HTML y que la API devuelve el campo del criterio.
