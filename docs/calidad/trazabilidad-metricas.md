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
| M-15 | Confidencialidad (RF-C02, ADR-0034) | Los PDF de evidencia del comercio no aparecen en respuestas públicas; solo moderación los descarga y los bytes se borran al decidir | `tests/integration/comercios/test_documentos_pdf.py` (`# M-13`, `# M-15`); reglas del PDF en `tests/unit/comercios/test_documentos.py` |
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

## Ampliación A1: canasta comparada (Corte 3, Anexo 1)

*Planificado:* nada de esta sección está implementado ni medido todavía. Requisitos en el
[análisis de impacto](../arquitectura/analisis-impacto-canasta.md#2-requerimiento-del-cambio);
escenarios en [escenarios-ampliacion-a1.md](escenarios-ampliacion-a1.md). EC-07 se usa en el sentido
del Anexo 1 (decisión D-A1-1 del 2026-11-25); EC-14 es propio del equipo. Privacidad es **EC-15** y
registro sin conexión es **EC-16** (antes EC-07 y EC-08).

### Métricas nuevas (propuestas)

| ID | Subcaracterística | Medida | Umbral | Instrumento |
|---|---|---|---|---|
| M-23 | Comportamiento temporal y capacidad (canasta) | p95 y tasa de error con 200 VU y canastas de 20 productos | p95 ≤ 3000 ms; errores < 1 % | `tests/load/k6/canasta.js` |
| M-24 | Corrección funcional (canasta) | % de productos sin precio vigente señalados y no sumados al total | 100 % | Pruebas `# EC-07` |
| M-25 | Corrección e integridad (asistente) | Respuestas del asistente con cifras no derivadas del dominio que llegan a la persona | 0 | Pruebas `# EC-14` con cliente falso |

M-17 y M-18 se miden por segunda vez para EC-05 con la línea base de la sección 4 del análisis de
impacto (mínimo, extensión y plus por aparte).

### Matriz requisito → escenario → métrica → prueba prevista

| Requisito | Escenario | Métrica | Prueba prevista |
|---|---|---|---|
| RF-A1-01 Canasta sin cuenta (máx. 20) | EC-07 | M-05, M-02 | `tests/unit/canasta/test_items.py` (vacía, 21 productos, cantidad 0 y negativa); `tests/integration/canasta/test_canasta_sesion.py` |
| RF-A1-02 Guardar con cuenta | EC-07 | M-02 | `tests/integration/canasta/test_canasta_guardada.py` (UNIQUE y CHECK de posición 1–20 en la BD) |
| RF-A1-03 Total normalizado | EC-07 | M-05 | `tests/unit/canasta/test_calculo.py` (g frente a kg, ml frente a L, presentación usada, redondeo) |
| RF-A1-04 Sin precio no suma cero; cobertura | EC-07 | M-24 | `tests/unit/canasta/test_calculo.py` (`# EC-07`: ninguna tienda completa, todas sin un producto, precios vencidos); prueba de integración HTML y API |
| RF-A1-05 Orden por criterio declarado | EC-07, EC-06 | M-06 | `tests/unit/canasta/test_orden.py` (criterios, empates); `tests/integration/canasta/test_neutralidad.py` (`# EC-06`) |
| RF-A1-06 Filtro municipio y barrio | EC-06 | M-06 | `tests/integration/canasta/test_filtros_canasta.py` (solo reduce) |
| RF-A1-07 Detalle y enlace a la comparación | EC-07 | — | `tests/integration/canasta/test_vista_canasta.py` |
| RF-A1-08 API de cálculo | EC-07, EC-15 | M-23, M-15 | `tests/integration/canasta/test_api_canasta.py` (sin autor, `# M-15`; *throttle*; sin N+1 con `django_assert_num_queries`) |
| RF-A1-09 Ahorro por «pague X lleve Y» | EC-06 | M-06 | `tests/unit/canasta/test_promociones.py` (puerto falso; el orden no cambia) |
| RF-A1-10 Combinación de dos tiendas (extensión) | EC-07 | M-05 | `tests/unit/canasta/test_combinacion.py` |
| RF-A1-11 Asistente con IA (plus) | EC-14 | M-25, M-15 | `tests/unit/asistente/test_validacion_salida.py`; `tests/integration/asistente/` (cifra inventada, inyección, tope, privacidad) |
| RF-A1-12 Ambigüedad e inexistencia (plus) | EC-14 | — | `tests/integration/asistente/test_ambiguedad.py` |
| Rendimiento de la canasta | EC-07 | M-23 | `tests/load/k6/canasta.js` (200 VU, 20 productos) |
| Esfuerzo y modularidad de la ampliación | EC-05 | M-17, M-18 | Horas reales en el análisis de impacto; `lint-imports`; `git diff --stat` |
