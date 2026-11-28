# ADR-0003: Usar PostgreSQL como base de datos única

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27) · Ampliado por [ADR-0035](0035-persistencia-relacional-frente-a-no-relacional.md)
- **Fecha:** 2026-11-06 (registro del Corte 1, C1-AS2-E2); archivado en el repositorio el 2026-11-27
- **Autores:** Equipo; redactado con apoyo de IA
- **Escenarios de calidad afectados:** EC-03, EC-04
- **Métricas que lo verifican:** M-14, D-05, D-06

## Contexto
Los datos están fuertemente relacionados (producto, presentación, establecimiento, reporte), hay
reglas de integridad que deben cumplirse siempre y las comparaciones cruzan esas entidades.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| **A. PostgreSQL** | Transacciones, restricciones `CHECK` y `UNIQUE`, índices compuestos, búsqueda por similitud, vistas materializadas | Escalado de escritura vertical (suficiente para la carga esperada) |
| B. Base documental (MongoDB) | Esquema flexible | Integridad referencial débil; comparaciones con agregaciones complejas |

## Decisión
Alternativa A: PostgreSQL 16 gestionado. La integridad se garantiza también en la base de datos
(precio > 0, cantidad > 0, presentación única por producto, una denuncia por usuario y reporte).

## Consecuencias
- (+) La completitud y la consistencia de los datos (D-05, D-06) se refuerzan en la base.
- (−) El sistema queda atado a SQL relacional, lo que es coherente con el stack elegido.

## Evidencia en el código
- `DATABASE_URL` hacia PostgreSQL 16 en el CI (servicio de GitHub Actions) y en Render.
- Restricciones `CheckConstraint` y `UniqueConstraint` en los `models.py` de cada módulo.
