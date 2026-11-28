# ADR-0008: Proteger la privacidad del reportante por diseño

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27)
- **Fecha:** 2026-11-06 (registro del Corte 1, C1-AS2-E2); archivado en el repositorio el 2026-11-27
- **Autores:** Equipo; redactado con apoyo de IA
- **Escenarios de calidad afectados:** EC-15 (confidencialidad; antes EC-07, renumerado en D-A1-1)
- **Métricas que lo verifican:** M-14, M-15

## Contexto
La ubicación y la actividad del reportante son datos personales (Ley 1581 de 2012). A la vez, la
moderación necesita saber quién reportó cada precio.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| **A. Autor guardado solo para auditoría y moderación, nunca expuesto** | Responsabilidad sin exponer a nadie | La comunidad no ve quién reporta |
| B. Reportes anónimos sin cuenta | Elimina la fricción | Impide la responsabilidad y facilita el abuso (EC-03) |

## Decisión
Alternativa A:
1. El autor de cada reporte se guarda solo para auditoría y moderación; nunca se expone en
   respuestas públicas.
2. No se almacena la geolocalización del reportante: el reporte se asocia al establecimiento elegido.
3. Serializers públicos con lista blanca de campos.
4. Autorización expresa de tratamiento de datos al crear la cuenta, con fecha de aceptación.
5. Política de tratamiento y procedimiento de consulta y reclamo publicados.

## Consecuencias
- (+) M-15 = 0 exposiciones, verificable con pruebas de API.
- (−) La comunidad no ve quién reporta, lo que limita una reputación pública.

## Evidencia en el código
- `apps/comparacion/api/serializers.py`: campos declarados uno por uno.
- `ReportePrecio` no tiene campos de ubicación.
- La política se publica sin iniciar sesión (`apps/cuentas/views/basicas.py`,
  `tests/integration/test_politica_datos.py`).
- La prueba de humo en Render confirmó que `/api/v1/comparacion/` no expone autor ni correo.
