# Trazabilidad métrica → evidencia en el repositorio

Fuente de métricas y umbrales: documento *Modelo Proyecto nuclear* (pasos 4 y 5).

| ID | Subcaracterística | Evidencia automatizada | Dónde |
|---|---|---|---|
| M-02 | Protección contra errores | Validación de precio/cantidad | `tests/integration/test_api_reportes.py`, `tests/unit/catalogo/` |
| M-05 | Corrección funcional | Reglas de dominio con TDD | `tests/unit/**` |
| M-06 | Neutralidad | Orden independiente de promociones | `tests/unit/comparacion/test_ranking.py` |
| M-08/M-09 | Comportamiento temporal / capacidad | k6 con umbrales p95 < 2 s, error < 1 %. **Ejecutado el 2026-11-16 (local, no en la nube): p95 = 5,26 ms, 0 % de errores con 500 usuarios** | `tests/load/k6/comparacion.js`; evidencia en `docs/calidad/evidencias/2026-11-16/carga-k6/` |
| M-11/M-12 | Integridad (anómalos / falsos positivos) | Heurística de mediana + dataset sembrado | `apps/precios/domain/confianza.py` (+ dataset pendiente) |
| M-13 | Autenticidad | Escritura exige autenticación | `test_registrar_exige_autenticacion` |
| M-14 | Responsabilidad | Autor y fecha en cada reporte | `test_reportante_registra_precio` |
| M-15 | Confidencialidad | Respuesta pública sin autor | `test_respuesta_publica_no_expone_al_reportante` |
| M-16 | Resistencia | Throttling `reportes`, ZAP, SonarQube. **SonarQube ejecutado el 2026-11-16** (ZAP sigue pendiente) | `config/settings/base.py`, CI; evidencia en `docs/calidad/evidencias/2026-11-16/sonarqube/` |
| M-16 | Resistencia (RN-10) | Límite de registros por hora en el servicio (HTMX y API) | `tests/integration/test_limite_registros.py` |
| M-17 | Modificabilidad | Línea base de esfuerzo del módulo comercial: 79 h (91 con 15 % de contingencia), por componente. *Planificado:* se mide en el Corte 3 con horas reales | `docs/arquitectura/analisis-impacto-modulo-comercial.md` (secciones 4 y 8) |
| M-18 | Modularidad | Contratos de capas y módulos en CI + diff del Corte III limitado a `apps/comercios` | `.importlinter` (`lint-imports`), `git diff --stat` del PR del módulo comercial |
| M-19 | Testabilidad | `pytest --cov` (CI falla < 70 %) | `.github/workflows/ci.yml` |
| M-21 | Disponibilidad | `/healthz/` comprueba PostgreSQL y caché (503 si falla) | `core/views.py`, `tests/integration/test_healthz.py` |
| M-22 | Tolerancia a fallos | Idempotencia por `id_cliente` y cola sin conexión en el navegador | `test_reenvio_offline_con_mismo_id_cliente_no_duplica` (API), `test_reenvio_del_formulario_con_mismo_id_cliente_no_duplica` (formulario), `tests/integration/e2e/test_navegador_sin_conexion.py` (Playwright, pérdida de red simulada) |
| D-01 | Actualidad | Invalidación de caché al registrar | `test_nuevo_reporte_invalida_la_cache` |
| D-02 | Actualidad (ventana) | Reglas de vigencia; RN-08 rechaza fechas futuras o fuera de ventana | `tests/unit/precios/test_vigencia.py`, `tests/unit/precios/test_validaciones.py` |
| D-03 | Credibilidad | Nivel de confianza en cada resultado | `apps/precios/domain/confianza.py` |
