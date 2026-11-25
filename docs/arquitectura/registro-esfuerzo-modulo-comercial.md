# Registro de esfuerzo del módulo comercial (línea base de M-17 y conteo de M-18)

**Corte 3 · EC-05 · Plantilla 8.3 del Anexo 1 (registro de análisis de impacto)**

- **Fecha de la línea base:** 2026-11-25 (aprobada por el equipo antes del primer commit de código).
- **Fuente de las estimaciones:** [análisis de impacto](analisis-impacto-modulo-comercial.md),
  sección 4 (borrador del equipo C2-AS2-E4, corregido el 14 de noviembre de 2026).
- **Línea base aprobada:** **79 h** (**91 h** con 15 % de contingencia). Método: descomposición por
  componentes y juicio del equipo (análisis, sección 4.4).
- **Fuera de la línea base:** RF-C08 (alertas, ADR-016), RF-C09 (carga masiva) y RF-C10 (aviso de
  precio regular inflado). Si se retoman, se suman **antes** de medir M-17.
- **Base del código para M-18:** `main` @ `99024d2` (punto de partida de `feat/modulo-comercial`). La
  etiqueta `nucleo-corte-2` prevista en el análisis no existe; se usa este commit en su lugar.
- **Cómo se llena:** las columnas *Tipo de cambio* y *Esfuerzo estimado* quedan fijas desde hoy. La
  de *Esfuerzo real* la llena cada integrante con las horas que registró en el tablero; la IA no
  inventa horas. *Observaciones* anota qué archivos se tocaron de cada componente.
- **Declaración de uso de IA:** este registro se preparó con apoyo de un asistente de IA (Claude,
  Anthropic) a partir del análisis de impacto aprobado. Las horas reales son del equipo.

## Decisiones del equipo que fijan la línea base (2026-11-25)

| ID | Decisión | Documento |
|---|---|---|
| DP-1 | **Opción B, puerto y registro de extensiones.** `comparacion` define un `Protocol` en su dominio, `core` guarda el registro y `comercios` se registra en `AppConfig.ready()`. `comparacion` nunca importa `comercios` y el contrato `comercios-no-adelantado` se conserva. La canasta (Corte 3) usará el mismo puerto | [ADR-012](../adr/0012-modulo-comercial-como-modulo-nuevo.md) |
| D-3 | **Conservar `es_promocion` y AGREGAR el arreglo `promociones`** (cambio aditivo en `/v1`) | [ADR-014](../adr/0014-promociones-como-estrategias.md) |
| Alcance | RF-C08, RF-C09 y RF-C10 quedan **fuera** de la línea base | Análisis, sección 4.4 |

## Tabla de componentes

Tipo de cambio: **Nuevo** (no existía), **Extensión** (comportamiento agregado en un punto previsto,
sin cambiar contratos existentes) o **Estructural** (cambia límites de módulo, contratos públicos o el
modelo de datos del núcleo). La meta de EC-05 es **0 estructurales** (M-18).

### Módulo nuevo `apps/comercios` (56 h)

| Componente | Tipo de cambio | Esfuerzo estimado (h) | Esfuerzo real (h) | Observaciones |
|---|---|---|---|---|
| Modelos y migración `0001` | Nuevo | 6 | | `comercios/models.py`, `migrations/0001_initial.py`: 4 modelos con 9 `CHECK`/`UNIQUE` y 5 índices; FK `PROTECT` |
| Dominio de promociones (TDD) | Nuevo | 8 | | `comercios/domain/promociones.py` (estrategias, `Vigencia`, `aplicar_a_cantidad`, `precio_efectivo_por_unidad`); 51 pruebas en `tests/unit/comercios/`; commits en rojo y verde |
| Servicios | Nuevo | 8 | | `comercios/services.py` (RF-C01 a C04, C06, C07, tope de 60 escrituras/h) y `comercios/permisos.py` |
| Selector comercial | Nuevo | 4 | | `comercios/selectors.py`: portal, bandeja y `ExtensionComercial` (2 queries para la comparación) |
| Portal de comercios (HTMX) | Nuevo | 12 | | `comercios/views.py`, `forms.py`, `urls.py` y 9 plantillas en `templates/comercios/` |
| API de comercios + OpenAPI | Nuevo | 6 | | `comercios/api/` (5 rutas, serializers en lista blanca); `ENUM_NAME_OVERRIDES` en `base.py` |
| Verificación de comercios | Nuevo | 4 | | `/comercios/verificacion/` y `verificar_perfil`/`resolver_correccion`; correos `perfil_verificado` y `correccion_resuelta` (`notificaciones`) |
| Pruebas de integración | Nuevo | 8 | | `tests/integration/comercios/` (72 pruebas) y `e2e/test_comercio_navegador.py` |
| **Subtotal** | | **56** | | |

### Puntos de extensión en el núcleo (10,5 h)

| Componente | Tipo de cambio | Esfuerzo estimado (h) | Esfuerzo real (h) | Observaciones |
|---|---|---|---|---|
| Selector de comparación (oficial frente a reportado, promociones) | Extensión | 6 | | `comparacion/selectors.py`: `_datos_comerciales`, `_oficiales_vigentes`, `_filas_oficiales`; `_ultimos_por_par` devuelve también los (precio, fecha) del par; `comparacion/domain/oficial.py` (discrepancia, TDD) |
| Estructura del resultado (`FilaComparacion`) | Extensión | 1 | | Campos opcionales `es_oficial`, `usuarios_reportan`, `promociones` y la propiedad `ancla`; claves de caché `v3` (`core/cache.py`) |
| Plantilla y serializer público (campos aditivos en `/v1`) | Extensión | 3 | | `_tarjeta_precio.html` (etiqueta «Oficial», aviso y promociones), `_resultados.html` y `_productos.html` (`fila.ancla`), `app.css`; `comparacion/api/` con `usuarios_reportan` y `promociones`; se ajustó la lista blanca esperada en `test_tarjetas.py` |
| Configuración y rutas | Extensión | 0,5 | | `LOCAL_APPS`, scope `comercios`, ajuste `COMERCIOS` y rutas en `config/urls.py` |
| **Subtotal** | | **10,5** | | |

### Documentación, despliegue y regresión (12,5 h)

| Componente | Tipo de cambio | Esfuerzo estimado (h) | Esfuerzo real (h) | Observaciones |
|---|---|---|---|---|
| Documentación (arquitectura v2, C4, ADR) | Nuevo | 4 | | ADR-012 y ADR-014 aceptados; este registro; `c4/v2-modulo-comercial.md`; `nucleo/requisitos-y-rutas.md`; `operacion/arranque-local-equipo.md` |
| Despliegue y pruebas de regresión | Nuevo | 8,5 | | Semilla `comercios.0002` (ADR-0023); suite completa; el despliegue lo verifica el job «imagen» del CI |
| **Subtotal** | | **12,5** | | |

| **Total de la línea base** | | **79** (91 con contingencia) | | |
|---|---|---|---|---|

### Componentes hallados en la lectura del código (no están en las 79 h)

El análisis (sección 4.3) los marcó como necesarios y les dio una estimación **orientativa, no
validada**. Se registran aparte para que M-17 sea transparente: sus horas reales **sí** cuentan en el
esfuerzo real, así que son una fuente conocida de desviación (≈ 6,5 h, un 8 % de la línea base).

| Componente | Tipo de cambio | Estimación orientativa (h) | Esfuerzo real (h) | Observaciones |
|---|---|---|---|---|
| Asignar el rol «comercio» (`cuentas.services.asegurar_comercio`) | Extensión | 1,5 | | `cuentas/services/basicos.py` y `__init__.py`; texto de `comercio_prueba` en `cuentas/domain/cuentas_prueba.py` |
| Contratos de arquitectura (`.importlinter`) | Extensión | 1 | | `comercios.domain` en los dos contratos de dominio puro, `comercios.semilla` en el de la siembra; ningún contrato relajado (8 *kept*) |
| *Scopes* de limitación de tasa | Extensión | 0,5 | | `comercios` en `DEFAULT_THROTTLE_RATES` (`COMERCIO_ESCRITURAS_POR_HORA`, 60) |
| Navegación (`templates/base.html`) | Extensión | 0,5 | | «Mi comercio» / «¿Tienes un comercio?» y «Verificar comercios» en el menú de la cuenta |
| Puerto y registro de extensiones (DP-1, opción B) | Extensión | 3 | | `comparacion/domain/extensiones.py` (Protocol y datos), `core/extensiones.py` (registro), `ComerciosConfig.ready()`; pruebas unitarias en rojo y verde |
| **Subtotal orientativo** | | **6,5** | | |

## Conteo de cambios estructurales al núcleo (M-18)

Medido el 2026-11-25 con `git diff --stat 99024d2..HEAD` sobre las carpetas del núcleo (`apps/` sin
`comercios`, `core`, `config`, `templates`, `static`, `.importlinter`): 27 archivos, +505/−21 líneas.

| Archivo o grupo del núcleo | Clasificación | Por qué |
|---|---|---|
| `comparacion/domain/ranking.py` (`_clave_neutral`) | **Sin cambio** | El orden sigue siendo precio por unidad → nombre → id (EC-06) |
| `comparacion/domain/extensiones.py`, `oficial.py` | Extensión | Archivos nuevos: el puerto y la regla del ADR-018 |
| `comparacion/selectors.py` | Extensión | Funciones privadas nuevas y campos opcionales de `FilaComparacion`; las firmas públicas no cambian |
| `comparacion/api/` | Extensión | Campos **aditivos** en `/v1`; ninguno cambia ni desaparece |
| Plantillas de `comparacion`, `app.css`, `base.html` | Extensión | Presentación de la etiqueta, el aviso y las promociones; enlace en el menú |
| `cuentas/services` (`asegurar_comercio`) | Extensión | Servicio nuevo previsto en el análisis (sección 4.3) |
| `cuentas/domain/cuentas_prueba.py` | Extensión | Solo el texto de ayuda de `comercio_prueba` |
| `core/extensiones.py`, `core/cache.py` (`v3`) | Extensión | Registro nuevo; nueva versión de claves (regla de CLAUDE.md) |
| `config/settings/base.py`, `config/urls.py` | Extensión | Activar la app, su *scope* y sus rutas |
| `.importlinter` | Extensión | Se agregan módulos a contratos; ninguno se relaja |
| `notificaciones` (tipos, plantillas, ejemplos) | Extensión | Dos correos informativos con la cola existente |
| `notificaciones/migrations/0002_tipos_del_modulo_comercial.py` | **Por decidir** | `AlterField` de *choices* sobre una tabla existente. `sqlmigrate` da `-- (no-op)`: no cambia el esquema. Si el equipo lo cuenta como estructural, M-18 = 1 |
| Modelos y migraciones del resto del núcleo | Sin cambio | Ninguna migración sobre `cuentas`, `catalogo`, `establecimientos`, `precios`, `moderacion`, `integraciones` ni `administracion` |

**M-18 = 0 cambios estructurales** (meta 0), con un caso pendiente de decisión del equipo:
`notificaciones.0002`. Alternativa si el equipo no la acepta: quitar los dos correos del módulo (y la
migración) y avisar solo en el portal.

## Cálculo de M-17

M-17 = (esfuerzo real − 79) / 79. Mínimo aceptable ±30 %; se analizan las desviaciones mayores a
±20 %. *Pendiente:* se calcula cuando el equipo llene la columna de esfuerzo real.
