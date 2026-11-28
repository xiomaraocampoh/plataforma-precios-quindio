# ADR-0027: Calcular la canasta en cada consulta sobre la caché de la comparación

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27)
- **Fecha:** 2026-11-24
- **Autores:** Equipo; borrador con apoyo de IA, pendiente de revisión humana
- **Escenarios relacionados:** EC-07 (Anexo 1), EC-02, EC-04
- **Métricas que lo verifican:** M-23, D-01
- **Plantilla:** 8.1 del Anexo 1 (adaptada de Nygard, 2011)

## Contexto
El Anexo 1 pregunta si el total de la canasta se calcula en cada consulta o se precalcula, y qué
implica cada opción frente a EC-02 (un precio cambiado deja de mostrarse como vigente en ≤ 1 min,
mínimo 5 min) y EC-07 (200 usuarios con canastas de 20 productos, p95 ≤ 3 s).

Fuerzas y hechos (*verificados* en `main`):

- La comparación ya tiene caché *cache-aside* por producto (TTL 60 s) con invalidación en
  `transaction.on_commit` al registrar o confirmar un precio (ADR-0004, `core/cache.py`).
- `comparacion.selectors._calcular_filas_de(producto_ids)` calcula las filas vigentes de varios
  productos con un número constante de consultas, y `primeras_filas` ya combina `cache.get_many` con
  el cálculo en lote de las claves que faltan.
- La canasta sin cuenta vive en la sesión: no hay fila en la BD a la que asociar un precálculo.
- Una canasta tiene como máximo 20 productos; el cálculo en Python sobre las filas es pequeño
  (20 productos × los establecimientos con precio).

## Alternativas consideradas
| Alternativa | A favor | En contra (frente a los escenarios) |
|---|---|---|
| **A. Calcular en cada consulta sobre la caché por producto de la comparación** | EC-02 se cumple sin código nuevo: la canasta lee lo mismo que la comparación y hereda su invalidación. Sirve igual con y sin cuenta. Sin tablas nuevas | Cada consulta repite el cálculo en Python; si la caché está fría, la primera consulta paga el lote completo (riesgo para EC-07 en picos) |
| B. Precalcular el total de cada canasta guardada | Lectura inmediata | Cada precio nuevo obliga a invalidar todas las canastas que contienen el producto (dependencia N:M); las canastas sin cuenta no se pueden precalcular; riesgo directo para EC-02 |
| C. Caché del resultado completo por canasta (clave = hash de los productos y cantidades) | Evita repetir el cálculo para canastas idénticas | Las canastas casi nunca se repiten exactas; invalidar exige saber qué claves contienen cada producto; agrega una segunda fuente de verdad |
| D. Vista materializada «último precio vigente por presentación y establecimiento» | Consultas muy rápidas | Infraestructura nueva y refresco programado; ya está prevista en ADR-0004 como plan de escalamiento del núcleo, no como diseño de la canasta |

## Decisión
**A.** El selector de la canasta pide a `comparacion.selectors` las filas vigentes de los productos de
la canasta mediante una función pública nueva, `filas_vigentes_de(producto_ids)`, que hace
`cache.get_many` de las claves por producto y calcula en un solo lote las que faltan (el patrón que
ya usa `primeras_filas`). Sobre esas filas, `canasta.domain.calcular_canasta` arma las opciones en
memoria. No se guarda ningún total.

**Razón principal:** es la única opción que cumple EC-02 sin agregar invalidaciones, porque la
canasta no tiene estado de precios propio.

## Consecuencias
- (+) EC-02 se cumple por construcción: un precio nuevo invalida la clave del producto y la siguiente
  canasta que lo contenga ya lo ve.
- (+) Un solo camino de lectura para la comparación y la canasta: el precio oficial (ADR-018) y la
  vigencia (ADR-0005) llegan iguales a ambas.
- (+) `comparacion/selectors.py` recibe solo un cambio aditivo (M-18 = 0 cambios estructurales).
- (−) El primer cálculo con la caché fría trae los 20 productos en un lote; es la consulta más pesada
  del sistema. Se mide en k6 con caché fría y caliente.
- (−) La canasta queda acoplada al formato de `FilaComparacion`. Se acepta: es un contrato interno del
  mismo monolito y está cubierto por pruebas.
- **Riesgo aceptado:** con 20 claves distintas, la tasa de aciertos de la caché baja si muchas
  personas arman canastas muy diferentes. Si k6 no alcanza el umbral, el paso siguiente es D
  (ADR-0004), no B.
- **Evidencia que haría revisar la decisión:** p95 > 3 s en k6 con caché caliente, o un número de
  consultas que crezca con el tamaño de la canasta.

## Verificación
1. **EC-07 / M-23:** `tests/load/k6/canasta.js` con 200 VU y canastas de 20 productos; umbrales
   `p(95)<3000` y `http_req_failed<0.01`. Evidencia en `docs/calidad/evidencias/<fecha>/`.
2. **Sin N+1:** prueba de integración con `django_assert_num_queries` que compara una canasta de 1 y
   una de 20 productos (mismo número de consultas).
3. **EC-02 / D-01:** prueba de integración: se calcula una canasta, se registra un precio nuevo de uno
   de sus productos y el siguiente cálculo muestra el precio nuevo.
4. **M-18:** `git diff --stat` del PR: fuera de `apps/canasta`, solo cambios aditivos en
   `comparacion/selectors.py` y configuración.
