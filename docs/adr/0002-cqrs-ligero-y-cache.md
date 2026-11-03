# ADR-0002: Separar lectura y escritura (CQRS ligero) con caché cache-aside

- **Estado:** Propuesto
- **Escenarios afectados:** EC-02, EC-04
- **Métricas:** M-08, M-09, M-10, D-01

## Contexto
Las consultas superan con creces a los registros. D-01 admite consistencia eventual corta
(objetivo ≤ 1 min, mínimo ≤ 5 min): los precios cambian por días, no por segundos.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| **A. Selectores + caché por producto (TTL 60 s) + invalidación al escribir** | Simple, sin infraestructura nueva en dev; cumple D-01 | Riesgo de "estampida" al expirar claves populares |
| B. CQRS completo con BD de lectura y eventos | Escala lecturas al máximo | Complejidad y consistencia eventual más difícil de probar |
| C. Sin caché, solo índices | Lo más simple | Riesgo de no cumplir p95 ≤ 2 s en pico |

## Decisión
A. Si la prueba k6 (Corte III) no alcanza el umbral, escalar a una vista materializada de
"último precio vigente por presentación y establecimiento" refrescada por los servicios.

## Consecuencias
- (+) D-01 garantizado por invalidación explícita; el TTL es la red de seguridad.
- (−) Las vistas deben pasar siempre por `comparacion.selectors` (no consultar el ORM directo).
