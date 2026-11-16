# Análisis de impacto del módulo comercial y arquitectura v2

**Entregable AS-II 4 · Corte 2 · Arquitectura de Software II**

- **Fecha:** 2026-11-16
- **Base analizada:** `main` @ `ccc0c8c` (núcleo del Corte 2; 213 pruebas, 6 contratos de `import-linter`)
- **Fuentes:** guía del proyecto (§4.2, §4.4, §4.5); borrador del equipo «C2-AS2-E4» del Drive
  (versión corregida del 14 de noviembre de 2026), de donde provienen las **estimaciones de esfuerzo**;
  y lectura del código del repositorio, de donde provienen los **hechos verificados**.
- **Declaración de uso de IA:** este documento se adaptó al repositorio con apoyo de un asistente de
  IA generativa (Claude, Anthropic). El equipo debe revisarlo y poder defender cada afirmación.

**Marcas de estado.** *Verificado* = comprobado en el código o con un comando en esta fecha.
*Propuesto* = decisión o estimación pendiente de aprobación del equipo. *Planificado* = se medirá en
el Corte 3. Nada de lo que aquí figura como medición se ha medido todavía.

---

## 1. Resumen

El módulo comercial puede entrar como **un módulo nuevo** (`apps/comercios`) sin modificar el modelo
de datos ni el orden neutral del núcleo. La lectura del código confirma el enfoque del borrador, pero
agrega **tres hallazgos** que el equipo debe decidir antes de fijar la línea base de M-17:

1. **El borrador contradice un contrato vigente.** El ADR-012 del Drive dice que el selector de
   comparación consulta al selector comercial. El contrato `comercios-no-adelantado` de
   `.importlinter` **prohíbe** que el núcleo importe `apps.comercios` (*verificado*). Hay dos caminos
   (sección 5): relajar el contrato o invertir la dependencia con un puerto. Se recomienda el puerto.
2. **Hay un punto de extensión mejor que el previsto.** `FilaComparacion` (capa de selectores) ya
   envuelve cada resultado con datos que *nunca* entran en el orden. Lo comercial puede viajar ahí y
   `comparacion/domain/ranking.py` queda **sin una sola línea modificada** (*propuesto*).
3. **Faltan componentes en la lista del borrador.** No existe ninguna función para asignar el rol
   «comercio» a un usuario (`cuentas.services`), hay que registrar nuevos *scopes* de limitación de
   tasa y hay que ajustar contratos de `import-linter` (sección 4.3).

**Esfuerzo (línea base del equipo): 79 h; 91 h con 15 % de contingencia.** El método y sus límites
están en la sección 4.4. Esta cifra será la base de M-17 en el Corte 3.

---

## 2. Requerimiento del cambio

La guía (§4.2) introduce el módulo comercial como un cambio de alcance sobre un núcleo ya construido,
con: perfil voluntario de comercio; publicación de precios oficiales; promociones con reglas
(descuento porcentual, precio especial, «pague X lleve Y», vigencia); integración de la información
oficial con la reportada por usuarios; y, opcionalmente, alertas de bajada de precio.

El equipo lo desglosó así (prioridad MoSCoW del borrador; M debe, S debería, C podría):

| ID | Requisito | Prioridad |
|---|---|---|
| RF-C01 | Un comercio crea un perfil voluntario vinculado a un establecimiento del directorio | M |
| RF-C02 | Un moderador verifica que quien gestiona el perfil es el dueño o encargado | M |
| RF-C03 | El comercio verificado publica y actualiza precios oficiales | M |
| RF-C04 | Promociones con reglas (descuento %, precio especial, pague X lleve Y), inicio y fin; origen y motivo; fecha de vencimiento si es por producto próximo a vencer | M |
| RF-C05 | La comparación integra la información oficial con la reportada | M |
| RF-C06 | El comercio solicita corrección de información errónea sobre su negocio | S |
| RF-C07 | Un comercio pequeño confirma con un toque que sus precios siguen vigentes | S |
| RF-C08 | Alertas de bajada de precio (opcional) | C |
| RF-C09 | Carga masiva de precios oficiales desde CSV o Excel | C |
| RF-C10 | Advertir si el precio regular de una promoción supera en más de 10 % la mediana de 30 días | C |

> Este análisis no incorpora aclaraciones hechas en clase por el docente, porque no se aportaron al
> repositorio. Si las hubo, deben revisarse contra esta tabla.

---

## 3. Punto de partida: el núcleo de hoy (*verificado*)

| Aspecto | Estado en `main` |
|---|---|
| Módulos activos | `cuentas`, `catalogo`, `establecimientos`, `precios`, `comparacion`, `moderacion`, `integraciones`; `comercios` comentado en `LOCAL_APPS` («Corte III») |
| Orden neutral | `comparacion/domain/ranking.py::_clave_neutral` = precio por unidad → nombre → id |
| Composición del resultado | `comparacion/selectors.py::FilaComparacion` envuelve un `ResultadoComparacion` y datos extra de interfaz que *no entran en el orden* |
| Promoción hoy | `ResultadoComparacion.es_promocion` existe (dominio, serializer público y plantilla) pero **nadie lo asigna**: siempre es `False` |
| Precedente de bloque aparte | La referencia mayorista SIPSA se muestra en un bloque separado, fuera de la lista ordenada |
| Caché | Cache-aside por producto (TTL 60 s); `core.cache.invalidar_comparacion` se llama al escribir |
| Rol «comercio» | Existe en `cuentas.Usuario.Rol` desde el Corte 1; no hay servicio que lo asigne |
| Escritura autenticada | Cada vista de la API que escribe exige autenticación (`IsAuthenticated` o rol moderador) y un `throttle_scope` |
| Contratos | 6 contratos; `comercios-no-adelantado` prohíbe que 8 módulos del núcleo importen `apps.comercios` |

---

## 4. Componentes afectados

Clasificación: **Nuevo** (no existía), **Extensión** (se agrega comportamiento en un punto previsto sin
cambiar contratos existentes), **Estructural** (cambia límites de módulo, contratos públicos o el
modelo de datos del núcleo) y **Sin cambio**. EC-05 pide **0 cambios estructurales** (M-18).

### 4.1 Módulo nuevo `apps/comercios`

| Componente | Ruta prevista | Detalle | Req. | Est. (h) |
|---|---|---|---|---|
| Modelos y migración `0001` | `comercios/models.py` | `PerfilComercio`, `PrecioOficial`, `Promocion`, `SolicitudCorreccion`; restricciones `CHECK`/`UNIQUE` en BD | C01–C06 | 6 |
| Dominio de promociones (TDD) | `comercios/domain/promociones.py` | Estrategias intercambiables; vigencia; precio efectivo por unidad | C04 | 8 |
| Servicios | `comercios/services.py` | Crear perfil, verificar, publicar precio oficial y promoción, invalidar caché | C01–C04, C07 | 8 |
| Selector comercial | `comercios/selectors.py` | Precios oficiales y promociones vigentes por producto | C05 | 4 |
| Portal de comercios (HTMX) | `comercios/views.py` + plantillas | Perfil, precios, promociones y correcciones | C01, C03, C04, C06, C07 | 12 |
| API de comercios + OpenAPI | `comercios/api/` | Endpoints autenticados con rol comercio | C03, C04 | 6 |
| Verificación de comercios | dentro del módulo (admin/bandeja) | Un moderador confirma al titular | C02 | 4 |
| Pruebas de integración | `tests/integration/` | Permisos por rol, integración con la comparación, neutralidad con promociones | C01–C07 | 8 |
| **Subtotal módulo nuevo** | | | | **56** |

*Nota de diseño:* la verificación vive en el propio módulo (`PerfilComercio.verificado_por` y
`fecha`). Registrarla en `moderacion.DecisionModeracion` obligaría a ampliar las opciones de un
modelo existente y generaría una migración en el núcleo; se evita a propósito.

### 4.2 Puntos de extensión en el núcleo (estimación del borrador)

| Componente | Ruta real | Tipo | Qué cambia | Est. (h) |
|---|---|---|---|---|
| Selector de comparación | `comparacion/selectors.py` | Extensión | Combinar precio oficial/reportado según ADR-018 y adjuntar promociones, **dentro de `FilaComparacion`** | 6 |
| Estructura del resultado | `FilaComparacion` (propuesto) o `ResultadoComparacion` | Extensión | Campos opcionales: precio con promoción y advertencia de discrepancia | 1 |
| Plantilla y serializer público | `_resultados.html`, `comparacion/api/serializers.py` | Extensión | Etiquetas «Oficial» y «Promoción», advertencia de discrepancia; campos *aditivos* en `/v1` | 3 |
| Configuración y rutas | `config/settings/base.py`, `config/urls.py` | Extensión | Activar la app y registrar sus URL | 0,5 |
| **Subtotal extensiones (borrador)** | | | | **10,5** |

### 4.3 Componentes que el borrador no listaba (hallazgos de la lectura del código)

Son **extensiones** de bajo costo, pero deben contarse para que M-17 compare lo mismo. *No están en
las 79 h*; la columna de horas es una **estimación orientativa de esta revisión, no validada por el
equipo** (*propuesto*).

| Componente | Ruta real | Por qué hace falta | Est. orientativa (h) |
|---|---|---|---|
| Asignar el rol «comercio» | `cuentas/services.py` | Hoy solo existe `asegurar_moderador`; al verificar un perfil hay que asignar el rol por un servicio (no por el ORM desde otro módulo) | 1,5 |
| Contratos de arquitectura | `.importlinter` | Agregar `apps.comercios.domain` a los contratos `dominio-puro` y `dominio-sin-capas-superiores`; y, según la decisión DP-1, relajar o conservar `comercios-no-adelantado` | 1 |
| *Scopes* de limitación de tasa | `config/settings/base.py` (`DEFAULT_THROTTLE_RATES`) | Cada endpoint de escritura del portal necesita un `throttle_scope` (regla 3 de CLAUDE.md) | 0,5 |
| Navegación | `templates/base.html` | Enlace al portal de comercios | 0,5 |
| Puerto y registro de extensiones (solo si se elige la opción B de DP-1) | `comparacion/domain/` y `core/` | Ver sección 5 | 3 |
| **Subtotal orientativo** | | | **3,5 (6,5 con la opción B)** |

### 4.4 Total y método de estimación

| Concepto | Horas |
|---|---|
| Módulo nuevo | 56 |
| Extensiones del núcleo (borrador) | 10,5 |
| Documentación (arquitectura v2, C4, ADR) | 4 |
| Despliegue y pruebas de regresión | 8,5 |
| **Total sin contingencia** | **79** |
| **Total con 15 % de contingencia** | **91** |

**Método.** Estimación por descomposición en componentes y juicio del equipo, con 15 % de
contingencia. El borrador del Drive no documenta una técnica adicional (por ejemplo, estimación por
analogía con datos históricos o *planning poker*), y este análisis no la inventa: **el equipo debe
confirmar el método y registrar la línea base en el tablero antes de escribir código del módulo**
(plan de medición, sección 8). Quedan fuera de la línea base RF-C08 (≈ 12 h y un ADR), RF-C09
(≈ 10 h) y RF-C10 (≈ 4 h); si el equipo los incluye, se suman antes de medir M-17.

### 4.5 Núcleo sin cambio (*verificado* por lectura)

`comparacion/domain/ranking.py` (orden neutral), `precios` (registro, vigencia, confianza),
`catalogo`, `establecimientos`, `moderacion`, `integraciones` y los modelos existentes de `cuentas`.
**El módulo comercial no requiere ninguna migración sobre tablas existentes**; solo la migración
inicial de `comercios`.

---

## 5. Decisión DP-1: cómo consulta la comparación al módulo comercial

El contrato `comercios-no-adelantado` fue escrito para que el núcleo no dependa del módulo comercial
(su encabezado dice que, si el Corte 3 obliga a relajarlo, se registre como evidencia de M-18).

| Opción | Cómo funciona | Efecto en M-18 / EC-05 | Costo |
|---|---|---|---|
| **A. Importación directa** | `comparacion.selectors` importa `comercios.selectors`; se relaja el contrato | La dependencia núcleo → comercios queda *declarada*; es un cambio de límites de módulo y debe contarse como **estructural** | Bajo (≈ 0) |
| **B. Puerto y registro (recomendada)** | `comparacion` define un puerto (un `Protocol` en su dominio) y un registro de extensiones en `core`; `comercios` se registra al arrancar (`AppConfig.ready`). `comparacion` nunca importa `comercios` | El contrato se **conserva**; la dependencia es comercios → comparacion (permitida). Mantiene **M-18 = 0** | ≈ 3 h extra (sección 4.3) |

**Recomendación: B.** Protege el indicador que la guía pide medir (EC-05) y deja el núcleo ignorante
del módulo comercial, lo que es coherente con el contrato ya construido. El precio es una pequeña
abstracción nueva y 3 h de esfuerzo adicional. **La decisión es del equipo** y debe tomarse antes de
registrar la línea base.

---

## 6. Respuestas propuestas a las preguntas de diseño de la guía

| Pregunta | Propuesta | ADR |
|---|---|---|
| **1.** Si el comercio publica un precio oficial y los usuarios reportan otro, ¿cuál se muestra? | Con comercio verificado y precio oficial vigente (confirmado en 30 días), el oficial es el principal y los reportes discrepantes (≥ 2 en 7 días, > 10 %) van como advertencia («Usuarios reportan $X»); si no, el reporte vigente más reciente. Respaldo: 60 % de la encuesta (n = 10) prefiere el precio de la tienda. Pasa a *Aceptado* solo con una muestra mayor. | ADR-018 (reemplaza al ADR-013) |
| **6.** ¿Cómo participa un comercio pequeño sin punto de venta? | Existe en el directorio por los reportes de usuarios; con perfil puede confirmar precios con un toque (RF-C07); carga masiva opcional (RF-C09). La tienda entrevistada sí tiene sistema de ventas y dedica unas 3 h diarias a precios. | Sección 4 y ADR-018 |
| **7.** ¿Cómo se garantiza que las promociones no alteran la neutralidad? | Orden único declarado; la promoción es una etiqueta con su precio efectivo y condiciones, y nunca participa en el orden. «Pague X lleve Y» jamás ordena porque exige comprar varias unidades. | ADR-014 |

### 6.1 Decisión D-3: cómo viajan las promociones hacia el cliente

Hoy el contrato público trae `es_promocion` por fila (siempre `False`). El Consolidado del 7 de
noviembre proponía un arreglo `promociones` aparte. Ambas opciones respetan el orden si `ranking.py`
no cambia; se diferencian en el contrato y en la interfaz.

| Opción | A favor | En contra |
|---|---|---|
| **Bandera por fila** (código actual) | Ya existe; cambio mínimo | Mezcla lo promocional con el resultado ordenado; cada fila arrastra condiciones |
| **Arreglo `promociones` aparte** | Coherente con la referencia SIPSA (que ya va aparte); separa visualmente lo comercial (guía §12.1) | Cambia el contrato; hay que sincronizar fila y promoción |
| **Ambas (aditiva)** | Compatible con `/v1` (solo se agrega) | Dos formas de lo mismo durante la transición |

**Recomendación:** conservar `es_promocion` y **agregar** `promociones` (cambio aditivo, permitido en
`/v1`), usando el arreglo como fuente de las condiciones. **Decisión del equipo antes del Corte 3**;
el ADR-014 la deja registrada como pendiente.

---

## 7. Arquitectura v2 y diagramas

Los diagramas C4 v2 (contexto, contenedores y componentes del módulo comercial) están en
[`c4/v2-modulo-comercial.md`](c4/v2-modulo-comercial.md), con una tabla de lo que cambia frente a la
versión 1. **No cambian los contenedores**: el portal de comercios es parte de la misma aplicación
Django y usa la misma base de datos y caché. Se descarta un *Backend for Frontend* separado porque el
portal y la interfaz del consumidor comparten tecnología y autenticación (ADR-012).

---

## 8. Riesgos y plan de medición de M-17 y M-18 (Corte 3)

| Riesgo | Escenario | Mitigación |
|---|---|---|
| Una promoción altera el orden | EC-06 | `ranking.py` sin cambios; prueba que compara el orden con y sin promociones (M-06 = 100 %) |
| El precio oficial desplaza al reportado y favorece a quien se verifica | EC-06 (equidad, guía §12.3) | Advertencia de discrepancia visible, vencimiento a 30 días, y verificación abierta a cualquier comercio; revisar con la muestra ampliada |
| Un comercio publica un precio oficial falso | EC-03 | Verificación previa, contraste con reportes y advertencia (ADR-018) |
| Suplantación de un comercio | Seguridad (autenticidad) | Verificación por moderador (ADR-015) |
| Más consultas por comparación degradan el p95 | EC-04 | El selector comercial entra en la misma caché por producto; invalidación al publicar |
| Erosión de límites de módulo | EC-05 | Contratos de `import-linter` en CI; decisión DP-1 |
| Condiciones de promoción poco claras | Legal (Ley 1480) | Campos obligatorios de vigencia y condiciones, visibles junto al precio |

**Plan de medición (Corte 3).**

1. Registrar la línea base (sección 4.4) en el tablero **antes** de escribir código del módulo.
2. Registrar horas reales por tarea en las mismas filas.
3. Etiquetar los commits: `feat(comercios)` para el módulo y `feat(comparacion)` para las extensiones.
4. Crear una etiqueta de Git al cerrar el Corte 2 (por ejemplo `nucleo-corte-2`; *aún no existe*) y, al
   integrar, ejecutar `git diff --stat nucleo-corte-2..HEAD` sobre las carpetas del núcleo, clasificando
   cada cambio como extensión o estructural (**M-18**).
5. Calcular **M-17 = (real − 79) / 79** y analizar desviaciones mayores a ±20 % (mínimo aceptable ±30 %).

---

## 9. Pendientes de decisión del equipo

1. **DP-1:** puerto y registro (recomendado) frente a importación directa.
2. **D-3:** forma de viajar de las promociones.
3. Aprobar o ajustar las estimaciones y el método; decidir si RF-C08, C09 y C10 entran a la línea base.
4. Ratificar el ADR-018 con una muestra mayor (30 consumidores y dos tiendas de barrio sin sistema de
   ventas, según la propia especificación).
5. Crear la etiqueta `nucleo-corte-2` al cerrar el Corte 2.

---

## Referencias (APA 7)

Bass, L., Clements, P., & Kazman, R. (2021). *Software architecture in practice* (4.ª ed.).
Addison-Wesley Professional.

Brown, S. (s. f.). *The C4 model for visualising software architecture*. https://c4model.com

Congreso de la República de Colombia. (2011). *Ley 1480 de 2011, por medio de la cual se expide el
Estatuto del Consumidor*.

Gamma, E., Helm, R., Johnson, R., & Vlissides, J. (1994). *Design patterns: Elements of reusable
object-oriented software*. Addison-Wesley.

International Organization for Standardization. (2023). *ISO/IEC 25010:2023, Systems and software
engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality
model*.

Nygard, M. (2011). *Documenting architecture decisions*. Cognitect.
