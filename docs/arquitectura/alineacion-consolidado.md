# Alineación del repositorio con el «Consolidado entregables corte 1 y 2»

- **Fecha:** 2026-11-15
- **Rama:** `feat/esqueleto-i0` (sobre `develop` @ `0070e2e`)
- **Fuentes comparadas:** el repositorio en `develop`; el documento *Consolidado entregables
  corte 1 y 2* (Google Docs, 2026-11-07); y los entregables de Modelos de Calidad que están en
  `docs/Entrgables Corte 1y 2/`.
- **Elaborado con apoyo de IA generativa.** Las decisiones marcadas «Decisión del equipo» no se
  cambiaron en el código: quedan propuestas hasta que el equipo las revise.

## 1. Lo que ya coincide con el diseño

| Elemento del Consolidado | Dónde está en el repositorio | Estado |
|---|---|---|
| ADR-001 monolito modular multicapa (7 módulos + `comercios` reservado) | `apps/*`, `config/settings/base.py` | Implementado |
| ADR-002 Django 5.2 + DRF + HTMX, vistas que sirven página o fragmento | `apps/*/views.py`, `templates/` | Implementado |
| ADR-003 PostgreSQL con `CHECK`/`UNIQUE` e índice compuesto del último precio | `apps/*/models.py`, migraciones `0001` | Implementado |
| ADR-004 CQRS ligero: servicios/selectores, cache-aside con TTL de 60 s e invalidación en `on_commit` | `precios/services.py`, `comparacion/selectors.py`, `core/cache.py` | Implementado y probado (D-01) |
| ADR-005 vigencia de 7, 3 y 30 días parametrizada (RN-03) | `precios/domain/vigencia.py`, `settings.PRECIOS` | Implementado con TDD |
| ADR-006 anomalía con más del 50 % de diferencia sobre la mediana y mínimo 3 muestras (RN-05) | `precios/domain/confianza.py` | Implementado con TDD |
| ADR-008 serialización pública con lista blanca y sin autor (EC-07, M-15) | `comparacion/api/serializers.py` | Implementado y probado |
| ADR-009 idempotencia por `id_cliente` (RN-07, M-22) | `ReportePrecio.id_cliente` único, servicio | Implementado y probado |
| ADR-010 puerto `FuentePreciosExterna` y adaptador SIPSA con tiempo de espera | `integraciones/clients/sipsa.py` | Solo la interfaz; el adaptador está pendiente (I4) |
| ADR-011 catálogo canónico y precio por unidad base con `Decimal` (RN-01, RN-02) | `catalogo/domain/normalizacion.py` | Implementado con TDD |
| ADR-012 REST v1 con OpenAPI (drf-spectacular) | `/api/v1/`, `/api/docs/` | Parcial (ver D-4) |
| ADR-014 Docker, compose y CI | `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml` | Parcial (ver sección 2) |

## 2. Lo que agrega esta rama (iteración I0 y correcciones)

Cada cambio sigue el ciclo TDD con commits separados `test:` (rojo) → `feat:`/`fix:` (verde) →
`refactor:`, como pide la sección 17.3 del Consolidado.

| Commit | Qué resuelve | Referencia |
|---|---|---|
| `ci(arquitectura)` | Contratos de import-linter (`.importlinter`): dominio sin Django ni DRF, capas por módulo, interfaces privadas entre módulos y núcleo independiente de `comercios`. Se agregó el paso `lint-imports` en CI. | ADR-001, secc. 16.2, M-18 |
| `test`/`fix(precios)` RN-08 | **Defecto:** un reporte con el reloj del celular adelantado (dentro de la tolerancia de 5 min) hacía que la comparación respondiera **500**. Ahora la fecha se ajusta a «ahora» y se rechazan las fechas anteriores a la ventana de vigencia. | RN-08, ADR-009, EC-01, M-21 |
| `test`/`feat(precios)` RN-10 | El límite de 30 registros por hora solo existía como *throttle* de DRF, así que **el formulario HTMX no lo aplicaba**. Ahora lo verifica el servicio (la API responde 429 y la vista muestra el error). Un reenvío idempotente no consume cupo. | RN-10, ADR-006, CLAUDE.md §2.3, M-16 |
| `test`/`feat(core)` | `/healthz/` comprueba PostgreSQL **y** la caché, y responde 503 indicando cuál falló. | secc. 18.1, M-21 |
| `chore(infra)` | Redis con *healthcheck* en compose; `web` recibe `REDIS_URL`; en desarrollo se usa RedisCache cuando la variable existe. | ADR-004, ADR-014 |
| `chore(static)` | htmx 2.0.4 versionado en `static/vendor/` (sin CDN y sin descarga manual). | ADR-002, RNF-07 |

Resultado: **46 pruebas en verde** (antes 34), Ruff limpio, 6 contratos de arquitectura
cumplidos y migraciones al día.

## 3. Discrepancias que debe decidir el equipo

No se modificaron. Hay que resolverlas antes de cerrar el Corte II, porque el Consolidado y el
repositorio dicen cosas distintas.

| ID | Tema | Consolidado | Repositorio / entregables de Calidad | Recomendación |
|---|---|---|---|---|
| **D-1** | Numeración de ADR | ADR-001 a ADR-014 | `docs/adr/0001` a `0003`, con otra numeración: el **0002 del repositorio es el ADR-004** y el **0003 es el ADR-005** | Adoptar la numeración del Consolidado en `docs/adr/` (renombrar 0002→0004 y 0003→0005, y crear los faltantes). Es el documento que se entrega. |
| **D-2** | Desempate del orden neutral (RN-06) | ADR-007 actualizado: precio/unidad → **mayor confianza → observación más reciente** → nombre. Advierte que desempatar solo por nombre favorece a los nombres que empiezan por A. | `_clave_neutral` = precio/unidad → nombre → id. RF-17 de la Especificación dice lo mismo. | Decisión del equipo (el Consolidado, tabla 48, pide aprobarla). Si se aprueba, es un cambio de `_clave_neutral` que se hace con TDD y requiere actualizar CLAUDE.md §2.1 y RF-17. |
| **D-3** | Cómo viaja la promoción | ADR-007: **arreglo `promociones` separado** de los resultados. La alternativa del indicador dentro de cada resultado fue **descartada**. | Bandera `es_promocion` dentro de cada resultado (CLAUDE.md §2.1, `apps/comercios/README.md`). | Decisión del equipo antes del Corte III. El ADR-007 se mide con M-06 y el cambio afecta el contrato público de la API. |
| **D-4** | Contrato de la API | `GET /api/v1/comparaciones/?producto=&municipio=` (respuesta con `producto`, `resultados`, `referencias` y `promociones`), además de `catalogo/`, `establecimientos/`, `moderacion/` y `cuentas/` | `GET /api/v1/comparacion/<id>/`; solo están implementados `precios/reportes/` y la comparación | Alinear con la tabla 19 del Consolidado **ahora**, mientras solo hay un cliente. Después, en `/v1` solo se admiten cambios aditivos. |
| **D-5** | Confianza «alta» (RN-04) | Dos o más reportes **concordantes** (diferencia ≤ 5 %); «media» o «baja» según la mitad de la ventana. | Hacen falta **3 reportes con precio idéntico** (`confirmaciones >= 2` y comparación exacta). **Un mismo usuario puede autoconfirmarse**, porque no se distinguen autores. | Decisión del equipo sobre los umbrales. El punto de la autoconfirmación es un riesgo para EC-03: se recomienda contar solo autores distintos. |
| **D-6** | Numeración de requisitos | RF-01 a RF-19 | RF-01 a RF-22 en la Especificación. **RF-19 está duplicado**, **RF-10 no existe** y la matriz de trazabilidad usa números desplazados (por ejemplo, RF-11 para el registro, que es RF-12). | Elegir una sola numeración y conciliar ambos documentos (el Consolidado ya lo señala en la nota de la tabla 6). |
| **D-7** | Mínimo de M-06 | 100 % (guía y Consolidado) | 90 % en el Plan de aseguramiento (tabla de métricas) | Corregir el Plan a 100 %. EC-06 de la guía exige el 100 % de los casos. |
| **D-8** | Regla de dependencias entre módulos | Secc. 16.2: un módulo solo importa `services` y `selectors` de otro, **nunca sus `models`** | CLAUDE.md §3 permite importar `models` de otro módulo, y `comparacion.selectors` consulta `ReportePrecio` directamente | Mantener la regla de CLAUDE.md (es la que está construida) y ajustar la secc. 16.2 del documento, o exponer un selector de lectura en `precios`. Los contratos actuales codifican la regla de CLAUDE.md. |
| **D-9** | Nombres de carpetas y rutas | `dominio/`, `compose.yaml`, `/salud/`, `.github/workflows/ci.yml` | `domain/`, `docker-compose.yml`, `/healthz/` | Conservar los del repositorio (ya construidos) y actualizar la secc. 16.1 del documento. |
| **D-10** | Integrantes | Cuatro integrantes en la portada (incluye a Derly Elena Quejada) | README y CLAUDE.md §1 listan tres | Confirmar y actualizar el README y CLAUDE.md. |

## 4. Lo que falta por iteración (plan de la tabla 41)

| Iteración | Pendiente en el repositorio |
|---|---|
| **I0 Esqueleto** | ✅ Esta rama. Queda pendiente decidir el proveedor de nube (ADR-014) y el primer despliegue. |
| **I1 Registro** | ✅ Cola sin conexión `static/js/cola-registros.js` (ADR-009, M-22). Pendiente: comando de carga del catálogo semilla y de los establecimientos piloto, y endpoints `catalogo/` y `establecimientos/` (RF-01, RF-02, RF-05). |
| **I2 Comparación** | Filtro por municipio y barrio (RF-11 del Consolidado; RF-19 de la Especificación), ETag y `Cache-Control: max-age=30`, criterio de orden según D-2, arreglos `referencias` y `promociones` según D-3, y la primera medición con k6 sobre el esqueleto. |
| **I3 Confiabilidad** | Niveles de confianza según D-5 y advertencia en los resultados de confianza «baja», denuncias por API, bandeja de moderación con servicio de aprobar o rechazar, entidad de **Auditoría** (solo inserción, M-14) y conjunto sembrado para M-11 y M-12. |
| **I4 Cierre** | Registro de cuentas con autorización de datos y recuperación de contraseña (RF-17, RF-18), adaptador SIPSA real, detección de duplicados (RF-04, D-05), revisión WCAG 2.2 AA, SonarQube y la prueba de carga completa. |

## 5. Actualizaciones que este cambio exige en otros documentos

- **Consolidado, tabla 47:** pasar a «Implementado» la estructura de módulos y capas (con la
  evidencia `lint-imports`), RN-08 y RN-10 (con los commits de esta rama), la verificación de
  salud y la parte de compose del despliegue.
- **`docs/calidad/trazabilidad-metricas.md`:** se agregaron las filas de M-18 (`lint-imports`),
  RN-08, RN-10 y M-21.
