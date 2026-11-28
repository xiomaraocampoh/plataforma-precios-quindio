# ADR-0006: Defender la confiabilidad del dato colaborativo en capas

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27)
- **Fecha:** 2026-11-06 (registro del Corte 1, C1-AS2-E2); archivado en el repositorio el 2026-11-27
- **Autores:** Equipo; redactado con apoyo de IA
- **Escenarios de calidad afectados:** EC-03 (pregunta de diseño 3)
- **Métricas que lo verifican:** M-11, M-12, M-16, D-03

## Contexto
Competidores o grupos coordinados pueden registrar precios falsos. Castigar reportes legítimos
desmotiva a la comunidad.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| **A. Defensa en capas:** límite de uso + mediana + nivel de confianza + moderación | Explicable; probable con TDD; cada capa cubre un tipo de abuso | Heurística simple; un ataque sofisticado puede pasar |
| B. Reputación de usuarios con puntajes | Premia a los reportantes confiables | Requiere historial; arranque en frío; riesgo de sesgo |
| C. Moderación manual de todo reporte | Máxima precisión | No escala; retrasa la actualidad (EC-02) |

## Decisión
Alternativa A:
1. Máximo 30 registros por hora por usuario.
2. Un precio que se aleja más de 50 % de la mediana de los últimos 7 días (con al menos 3 muestras)
   queda en revisión.
3. Cada resultado muestra un nivel de confianza: alta (confirmado por 2 o más reportes o fuente
   oficial), media (reporte aislado) o baja (anómalo, con advertencia).
4. Denuncias de usuarios y bandeja de moderación.

## Consecuencias
- (+) Los datos no confiables no se muestran como vigentes sin advertencia (EC-03).
- (−) Un cambio de precio real y brusco tarda en publicarse hasta que se confirma.
- La tolerancia se calibra con el conjunto sembrado de reportes falsos (M-11, M-12). La reputación
  queda como mejora futura.

## Ajuste al cierre del Corte 2: límite de lectura por IP
Se agregó un límite de lectura: 120 consultas por minuto por IP para visitantes anónimos y 240 para
usuarios autenticados (`LIMITE_ANONIMO`, `LIMITE_USUARIO`). Como se cuenta por IP, en la primera
prueba de carga contra Render k6 recibió HTTP 429 en el 71,5 % de las peticiones, y por la misma
razón usuarios de redes móviles que comparten IP (CGNAT) podrían ser frenados en horas pico. Para
las pruebas de carga el límite se eleva temporalmente por variable de entorno, sin cambiar el código.

## Evidencia en el código
- `apps/precios/domain/confianza.py`: `MIN_MUESTRAS_PARA_ANOMALIA = 3`, tolerancia 0,5 sobre la
  mediana y niveles alta, media y baja.
- `DEFAULT_THROTTLE_RATES` en `config/settings/base.py`: `reportes` 30/hour, `denuncias` 20/hour,
  `anon` y `user` por variable de entorno.
- El servicio de registro aplica el límite también al formulario HTMX (`apps/precios/services.py`).
