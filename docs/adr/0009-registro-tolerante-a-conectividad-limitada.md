# ADR-0009: Hacer el registro tolerante a la conectividad limitada

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27)
- **Fecha:** 2026-11-06 (registro del Corte 1, C1-AS2-E2); archivado en el repositorio el 2026-11-27
- **Autores:** Equipo; redactado con apoyo de IA
- **Escenarios de calidad afectados:** EC-01, EC-08
- **Métricas que lo verifican:** M-01, M-22

## Contexto
El reportante suele estar dentro del establecimiento, con mala señal. Un reintento no debe duplicar
el registro.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| **A. Identificador generado en el cliente (UUID) + cola local + reenvío** | Idempotente; simple en el servidor; funciona con HTMX | Requiere un script de cola en el navegador |
| B. PWA completa con *service worker* y sincronización en segundo plano | Experiencia sin conexión completa | Esfuerzo alto; soporte desigual entre navegadores |

## Decisión
Alternativa A. El formulario genera un `id_cliente` único. Si el envío falla, el registro se guarda
en el almacenamiento local y se reenvía al recuperar la conexión. El servidor tiene una restricción
única sobre `id_cliente` y devuelve el registro existente ante un reenvío.

## Consecuencias
- (+) M-22 es verificable simulando la pérdida de red.
- (−) La fecha del reporte es la de observación, no la de llegada.

## Evidencia en el código
- `ReportePrecio.id_cliente` (`UUIDField`, único) y `apps/precios/services.py`.
- `static/js/cola-registros.js`.
- `tests/integration/test_registro_sin_conexion.py` y
  `tests/integration/e2e/test_navegador_sin_conexion.py`.
