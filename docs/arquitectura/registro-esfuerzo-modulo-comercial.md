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
| Modelos y migración `0001` | Nuevo | 6 | | |
| Dominio de promociones (TDD) | Nuevo | 8 | | |
| Servicios | Nuevo | 8 | | |
| Selector comercial | Nuevo | 4 | | |
| Portal de comercios (HTMX) | Nuevo | 12 | | |
| API de comercios + OpenAPI | Nuevo | 6 | | |
| Verificación de comercios | Nuevo | 4 | | |
| Pruebas de integración | Nuevo | 8 | | |
| **Subtotal** | | **56** | | |

### Puntos de extensión en el núcleo (10,5 h)

| Componente | Tipo de cambio | Esfuerzo estimado (h) | Esfuerzo real (h) | Observaciones |
|---|---|---|---|---|
| Selector de comparación (oficial frente a reportado, promociones) | Extensión | 6 | | |
| Estructura del resultado (`FilaComparacion`) | Extensión | 1 | | |
| Plantilla y serializer público (campos aditivos en `/v1`) | Extensión | 3 | | |
| Configuración y rutas | Extensión | 0,5 | | |
| **Subtotal** | | **10,5** | | |

### Documentación, despliegue y regresión (12,5 h)

| Componente | Tipo de cambio | Esfuerzo estimado (h) | Esfuerzo real (h) | Observaciones |
|---|---|---|---|---|
| Documentación (arquitectura v2, C4, ADR) | Nuevo | 4 | | |
| Despliegue y pruebas de regresión | Nuevo | 8,5 | | |
| **Subtotal** | | **12,5** | | |

| **Total de la línea base** | | **79** (91 con contingencia) | | |
|---|---|---|---|---|

### Componentes hallados en la lectura del código (no están en las 79 h)

El análisis (sección 4.3) los marcó como necesarios y les dio una estimación **orientativa, no
validada**. Se registran aparte para que M-17 sea transparente: sus horas reales **sí** cuentan en el
esfuerzo real, así que son una fuente conocida de desviación (≈ 6,5 h, un 8 % de la línea base).

| Componente | Tipo de cambio | Estimación orientativa (h) | Esfuerzo real (h) | Observaciones |
|---|---|---|---|---|
| Asignar el rol «comercio» (`cuentas.services.asegurar_comercio`) | Extensión | 1,5 | | |
| Contratos de arquitectura (`.importlinter`) | Extensión | 1 | | |
| *Scopes* de limitación de tasa | Extensión | 0,5 | | |
| Navegación (`templates/base.html`) | Extensión | 0,5 | | |
| Puerto y registro de extensiones (DP-1, opción B) | Extensión | 3 | | |
| **Subtotal orientativo** | | **6,5** | | |

## Conteo de cambios estructurales al núcleo (M-18)

*Se llena al cerrar la implementación*, con `git diff --stat 99024d2..HEAD` sobre las carpetas del
núcleo, clasificando cada archivo tocado.

## Cálculo de M-17

M-17 = (esfuerzo real − 79) / 79. Mínimo aceptable ±30 %; se analizan las desviaciones mayores a
±20 %. *Pendiente:* se calcula cuando el equipo llene la columna de esfuerzo real.
