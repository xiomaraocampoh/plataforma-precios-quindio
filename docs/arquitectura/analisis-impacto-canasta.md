# Análisis de impacto de la ampliación A1: canasta comparada

**Anexo 1 de la guía · Corte 3 · Arquitectura de Software II y Modelos de Calidad**

- **Fecha:** 2026-11-24
- **Base analizada:** `main` @ `fccb9fd` (núcleo del Corte 2, sin el módulo comercial fusionado)
- **Opción del bloque A:** A1, canasta comparada. **Escenario de referencia:** EC-07 (Anexo 1, §6).
- **Plantilla:** 8.3 del Anexo 1 (registro de análisis de impacto). Las columnas *Tipo de cambio* y
  *Esfuerzo estimado* se llenan **antes de construir**; la de *Esfuerzo real*, al cierre.
- **Declaración de uso de IA:** este documento se redactó con apoyo de un asistente de IA generativa
  (Claude, Anthropic) a partir de la lectura del código y del Anexo 1. Las estimaciones son una
  **propuesta para que el equipo la apruebe o ajuste**; el equipo debe poder defender cada cifra.

**Marcas de estado.** *Verificado* = comprobado en el código en esta fecha. *Propuesto* = decisión o
estimación pendiente de aprobación. *Planificado* = se medirá al cerrar la ampliación.

---

## 1. Resumen

La canasta entra como **un módulo nuevo** (`apps/canasta`) que **solo lee** del núcleo. El núcleo
necesita **una sola extensión aditiva**: una función pública en `comparacion/selectors.py` que entregue
las filas vigentes de varios productos a la vez desde la caché por producto, reutilizando lo que ya
existe (`_calcular_filas_de` y el patrón de `primeras_filas`, *verificado*). `ranking.py`, `precios`,
`catalogo`, `establecimientos` y `moderacion` **no cambian**.

El trabajo se separa en tres bloques para que el contraste del Entregable 6 se haga por aparte:

| Bloque | Qué incluye | Estimado (h) | Con 15 % de contingencia (h) |
|---|---|---|---|
| **Mínimo exigible A1** | Canasta de hasta 20 productos, con o sin cuenta; total normalizado; productos sin precio señalados; orden declarado; TDD; API; k6 | **67** | **77** |
| **Extensión del Anexo** | Mejor combinación de dos establecimientos | **9** | **10** |
| **Plus del equipo** | Asistente de compras con IA (tool use) | **38** | **44** |
| **Total** | | **114** | **131** |

El **mínimo tiene prioridad** (regla 3 del Anexo): la extensión y el plus solo empiezan cuando el
mínimo pase sus pruebas y la prueba de carga de EC-07.

---

## 2. Requerimiento del cambio

El Anexo 1 (A1) pide que el consumidor arme una lista de productos y que la plataforma le indique en
qué establecimiento resulta más económica la compra completa y qué productos no tienen precio vigente
en cada uno. La canasta es **informativa**: no genera pedidos ni se envía a ningún comercio.

| ID | Requisito | Bloque | Prioridad |
|---|---|---|---|
| RF-A1-01 | Crear una canasta de hasta 20 productos **sin cuenta** (vive en la sesión) | Mínimo | M |
| RF-A1-02 | Con cuenta, **guardar** la canasta (máx. 20 productos garantizado también en la BD) | Mínimo | M |
| RF-A1-03 | Calcular el total por establecimiento con precios normalizados por unidad de medida | Mínimo | M |
| RF-A1-04 | Señalar los productos sin precio vigente en cada establecimiento, **sin sumarlos como cero**, y mostrar la cobertura (n de m) | Mínimo | M |
| RF-A1-05 | Ordenar los establecimientos por un criterio declarado, que la persona puede cambiar y que siempre se muestra | Mínimo | M |
| RF-A1-06 | Filtrar por municipio y barrio (los filtros solo reducen; no reordenan) | Mínimo | S |
| RF-A1-07 | Ver el detalle por producto (presentación usada, precio, precio por unidad) y un enlace a su comparación | Mínimo | S |
| RF-A1-08 | API de solo lectura `POST /api/v1/canasta/calcular/` documentada en OpenAPI | Mínimo | S |
| RF-A1-09 | Mostrar el ahorro posible por promociones «pague X lleve Y» sin alterar el total ni el orden | Mínimo (depende del módulo comercial) | C |
| RF-A1-10 | Sugerir la combinación de dos establecimientos que minimiza el costo total | Extensión | C |
| RF-A1-11 | Asistente conversacional que arma la canasta a partir de una petición en lenguaje natural | Plus | C |
| RF-A1-12 | El asistente pregunta ante un producto ambiguo y ofrece «Solicitar producto» si no existe | Plus | C |

Las reglas de cálculo se desarrollan con TDD (`tests/unit/canasta/`), como exige el Anexo.

---

## 3. Punto de partida (*verificado*)

| Aspecto | Estado en `main` | Implicación para la canasta |
|---|---|---|
| Comparación por varios productos | `comparacion/selectors.py::_calcular_filas_de(producto_ids)` trae las filas vigentes de N productos con un número constante de consultas | Se reutiliza; no hay que escribir otra consulta de precios |
| Caché por producto | `primeras_filas` hace `cache.get_many` de las claves y calcula las que faltan en un solo lote | El mismo patrón sirve para 20 productos |
| Vigencia | El selector ya descarta precios vencidos (`es_vigente`, ADR-0003) | Un precio vencido nunca llega a la canasta |
| Normalización | `catalogo/domain/normalizacion.py::precio_por_unidad`, `a_unidad_base`, `exigir_comparables` | Se usan tal cual (CLAUDE.md: nunca a mano) |
| Filtros | `comparacion/domain/filtros.py` (municipio, barrio) | Se reutilizan sobre las filas |
| Orden neutral | `ranking.py::_clave_neutral` (precio por unidad → nombre → id) | **No se toca.** El orden de la canasta es otra función, en `canasta/domain` |
| Precio oficial (ADR-018) | Propuesto; se resolverá dentro de `FilaComparacion` | La canasta usa el precio que entregue el selector, sin lógica propia |
| Módulo comercial | `apps/comercios` es un esqueleto (`apps.py`); **no hay promociones ni puerto de extensiones**; la rama `feat/modulo-comercial` no existe | RF-A1-09 depende de él (sección 6) |
| IA | `integraciones/clients/vision.py`: puerto `ReconocedorDeProductos` y adaptador `ReconocedorClaude` con timeout y modelo configurable (ADR-022) | El asistente copia ese patrón |
| Límites de uso | `core/limites.py::permitir` (contador en caché con hash del sujeto) | Se reutiliza para los topes del asistente |

---

## 4. Registro de análisis de impacto (plantilla 8.3)

Tipo de cambio: **Nuevo**, **Modificado** (se agrega comportamiento sin romper contratos existentes;
equivale a *extensión* en el análisis del módulo comercial) o **Sin cambio**. Para M-18 se registra
aparte si algún cambio es **estructural** (cambia límites de módulo, contratos públicos o el modelo de
datos del núcleo): la meta es **0**.

### 4.1 Mínimo exigible A1

| Componente | Tipo de cambio | Esfuerzo estimado (h) | Esfuerzo real (h) | Observaciones |
|---|---|---|---|---|
| Artefactos previos: este análisis, EC-07 refinado, ADR 0027–0030, trazabilidad | Nuevo | 5 | | Fase 0; precede al primer commit de código (regla 2 del Anexo) |
| `canasta/domain/items.py`: `ItemCanasta` y validación (vacía, > 20, cantidad ≤ 0, unidad incompatible) | Nuevo | 4 | | TDD; usa `a_unidad_base` y `exigir_comparables` |
| `canasta/domain/calculo.py`: `calcular_canasta` (presentación elegida, costo normalizado, sin precio, cobertura) | Nuevo | 8 | | TDD; núcleo de EC-07 y ADR-0028/0029 |
| `canasta/domain/orden.py`: `ordenar_opciones` con criterios declarados y empates | Nuevo | 3 | | TDD; ADR-0028. No reutiliza ni modifica `_clave_neutral` |
| `canasta/domain/promociones.py`: ahorro posible «pague X lleve Y» por empaques | Nuevo | 4 | | TDD con promociones falsas; depende del módulo comercial para datos reales (ADR-0029) |
| `comparacion/selectors.py`: función pública `filas_vigentes_de(producto_ids)` | **Modificado** | 2 | | Aditiva; extrae el patrón de `primeras_filas`. No cambia firmas existentes |
| `canasta/selectors.py`: selector cacheado con filtro de municipio y barrio | Nuevo | 4 | | Número constante de consultas (ADR-0027) |
| `canasta/models.py` + migración `0001`: `Canasta`, `ItemGuardado` | Nuevo | 4 | | `UNIQUE(canasta, producto)`; `CHECK posicion BETWEEN 1 AND 20` + `UNIQUE(canasta, posicion)` garantiza el máximo de 20 en la BD (un `CHECK` no puede contar filas) |
| `canasta/services.py`: canasta en sesión y guardada | Nuevo | 4 | | La canasta sin cuenta no toca la BD |
| Interfaz HTMX `/canasta/` (vistas, plantillas, parciales) | Nuevo | 10 | | Reutiliza la búsqueda existente; 3 opciones destacadas; «Ordenado por: …»; WCAG 2.2 AA |
| API `POST /api/v1/canasta/calcular/` + serializers + OpenAPI | Nuevo | 4 | | Solo lectura, sin autor, lista blanca, `throttle_scope = "canasta"` |
| Configuración: `INSTALLED_APPS`, rutas, *scope* de limitación, navegación | Modificado | 1 | | `config/settings/base.py`, `config/urls.py`, `templates/base.html` |
| Contratos de `.importlinter` | Modificado | 1 | | Agregar `apps.canasta.domain` a los contratos de dominio; contrato nuevo «canasta solo lee» (sección 5) |
| Pruebas de integración | Nuevo | 6 | | Con y sin cuenta, máx. 20, sin N+1, EC-06, M-15 |
| Prueba de carga `tests/load/k6/canasta.js` y evidencia | Nuevo | 4 | | 200 VU, 20 productos, p95 < 3000 ms, errores < 1 % |
| Documentación de cierre (resultados EC-07, ADR, `requisitos-y-rutas.md`) | Modificado | 3 | | |
| **Total mínimo** | | **67** | | **77 h con 15 % de contingencia** |

### 4.2 Extensión del Anexo: combinación de dos establecimientos

| Componente | Tipo de cambio | Esfuerzo estimado (h) | Esfuerzo real (h) | Observaciones |
|---|---|---|---|---|
| `canasta/domain/combinacion.py`: `mejor_combinacion` | Nuevo | 5 | | TDD. Prueba todos los pares (con 20 productos y decenas de tiendas son pocos miles de pares); cada producto va a la tienda del par donde es más barato; prioriza cobertura, luego total |
| Selector, interfaz y API: bloque «Combinando dos tiendas» | Modificado (dentro de `canasta`) | 3 | | Aparte de las opciones ordenadas; no las reordena |
| Pruebas de integración | Nuevo | 1 | | |
| **Total extensión** | | **9** | | **10 h con contingencia** |

### 4.3 Plus del equipo: asistente de compras con IA

| Componente | Tipo de cambio | Esfuerzo estimado (h) | Esfuerzo real (h) | Observaciones |
|---|---|---|---|---|
| `integraciones/clients/asistente.py`: puerto `ModeloConversacional` y adaptador `AsistenteClaude` | Nuevo | 5 | | Timeout, `ASISTENTE_MODELO`, cliente falso para pruebas (ADR-0030) |
| `asistente/domain/`: validación de argumentos de herramientas y de la salida (cifras no derivadas) | Nuevo | 5 | | TDD; pruebas de inyección |
| `asistente/services.py`: bucle de agente (máx. 6 llamadas de herramienta) y herramientas | Nuevo | 8 | | Herramientas de solo lectura sobre `catalogo`, `canasta` |
| Topes por sesión, IP y usuario; `throttle_scope`; ocultar sin `ANTHROPIC_API_KEY` | Nuevo | 2 | | Reutiliza `core/limites.py` |
| Interfaz `/asistente/` (chat accesible, tarjeta HTMX, botones de opciones, detener) | Nuevo | 10 | | `role="log"`, `aria-live="polite"` |
| Pruebas de integración (ambiguo, inexistente, cifra inventada, inyección, tope) | Nuevo | 6 | | Sin red: cliente falso con llamadas predefinidas |
| Política de datos y aprobación de la propietaria | Modificado | 2 | | Igual que ADR-022: dato a un tercero |
| **Total plus** | | **38** | | **44 h con contingencia** |

### 4.4 Componentes sin cambio (*verificado* por lectura)

| Componente | Tipo de cambio | Observaciones |
|---|---|---|
| `comparacion/domain/ranking.py` (`_clave_neutral`, `ordenar_neutral`) | Sin cambio | El orden de la comparación por producto sigue igual (EC-06) |
| `precios` (registro, vigencia, confianza, idempotencia) | Sin cambio | La canasta no escribe precios |
| `catalogo/domain/normalizacion.py` | Sin cambio | Se reutiliza |
| `establecimientos`, `moderacion`, `cuentas`, `notificaciones`, `administracion` | Sin cambio | |
| Modelos y migraciones existentes | Sin cambio | Solo la migración inicial de `canasta` |

### 4.5 Método de estimación

Descomposición por componentes y juicio del equipo, con **15 % de contingencia**, igual que en el
análisis del módulo comercial, para que las dos mediciones de M-17 sean comparables. Las cifras toman
como referencia el tamaño real de piezas parecidas ya construidas (por ejemplo, los filtros de la
comparación y el reconocimiento por foto). **El equipo debe confirmar o ajustar las cifras antes del
primer commit de código.**

**Riesgo para la estimación.** La ampliación se hace en paralelo con el módulo comercial y con un plazo
de dos semanas. Si el equipo no tiene capacidad para los 131 h, se recorta en este orden: plus,
extensión. El mínimo no se recorta.

---

## 5. Dependencias y contratos de arquitectura

```
apps.canasta ──lee──▶ comparacion.selectors (filas_vigentes_de)
             ──lee──▶ catalogo.selectors (búsqueda, presentaciones)
             ──usa──▶ catalogo.domain.normalizacion
             ──lee──▶ precios.selectors (solo si hiciera falta la política de vigencia)
             ──puerto──▶ promociones (lo implementa comercios al registrarse; ADR-0029)
apps.asistente ──usa──▶ apps.canasta (services/selectors/domain)
               ──usa──▶ integraciones.clients.asistente (puerto)
```

Contratos de `import-linter` previstos (se agregan en el mismo PR que crea los módulos):

1. `apps.canasta.domain` y `apps.asistente.domain` entran en `dominio-puro` y
   `dominio-sin-capas-superiores`.
2. `apps.canasta` y `apps.asistente` entran en `capas-por-modulo`.
3. **Nuevo «el núcleo no depende de la canasta»:** ningún módulo del núcleo importa `apps.canasta` ni
   `apps.asistente`.
4. **Nuevo «la canasta solo lee»:** `apps.canasta` no importa `services`, `views`, `api` ni `forms` de
   otros módulos, ni `apps.comercios` (las promociones llegan por el puerto).

**M-18 (segunda medición de EC-05).** El único archivo del núcleo que cambia con lógica es
`comparacion/selectors.py`, de forma aditiva. Se clasificará con `git diff --stat` igual que en el
módulo comercial.

---

## 6. Decisiones de diseño (preguntas del Anexo)

| Pregunta del Anexo | Respuesta propuesta | ADR |
|---|---|---|
| ¿Cómo se compara una canasta cuando un establecimiento no tiene precio vigente para uno de los productos? | Nunca se suma como cero ni se inventa. Se lista como «Sin precio vigente», el total es parcial y se declara la cobertura (n de m). Por defecto se ordena primero por cobertura, luego por total y luego por nombre; la persona puede cambiar el criterio y siempre se le muestra cuál se usa | ADR-0028 |
| ¿El total se calcula en cada consulta o se precalcula? ¿Qué implica frente a EC-02 y EC-07? | En cada consulta, sobre la caché por producto de la comparación. EC-02 se cumple sin invalidaciones nuevas; EC-07 se verifica con k6. El precálculo exigiría invalidar cada canasta que contenga un producto cuando cambia su precio | ADR-0027 |
| ¿Cómo se aplican las promociones «pague X lleve Y» a las cantidades de la canasta? | La cantidad pedida se convierte a empaques de la presentación elegida; la promoción se aplica sobre esos empaques y se muestra como «ahorro posible», sin cambiar el total comparado ni el orden (coherente con ADR-014) | ADR-0029 |
| (Plus) ¿Cómo se usa la IA sin poner en riesgo la exactitud y la neutralidad? | La IA interpreta la petición y explica; los cálculos y el orden son del dominio. Las cifras se muestran en una tarjeta generada por el sistema | ADR-0030 |

---

## 7. Riesgos

| Riesgo | Escenario | Mitigación |
|---|---|---|
| Un producto sin precio se suma como cero y la tienda incompleta aparece como la más barata | EC-07 | Regla de dominio con TDD; tipo de dato que separa «sin precio» de «precio»; prueba `# EC-07` |
| La canasta de 20 productos multiplica las consultas | EC-07, EC-04 | `get_many` de 20 claves + un solo lote para las faltantes; `django_assert_num_queries` |
| Un atributo comercial cuela en el orden de la canasta | EC-06 | `ordenar_opciones` solo recibe totales, cobertura y nombres; prueba que compara el orden con y sin promociones |
| La persona confunde un total parcial con uno completo | EC-07 (corrección funcional) | «n de m productos», lista de faltantes y «Ordenado por: …» siempre visibles |
| El módulo comercial no llega a tiempo | RF-A1-09 | La canasta funciona sin promociones; el puerto queda vacío hasta que `comercios` se registre |
| El asistente muestra cifras inventadas o sigue instrucciones del texto | EC-14 (propio) | Cifras solo en la tarjeta del sistema; validación de salida; herramientas de solo lectura; pruebas de inyección |
| Costo y datos personales enviados a un tercero (asistente) | Ley 1581 | Topes, sin datos de identidad, conversación solo en sesión; aprobación de la propietaria (ADR-0030) |
| La ampliación consume las horas del módulo comercial | EC-05 | Mínimo primero; recorte declarado en 4.5 |

---

## 8. Pendientes de decisión del equipo

1. **Aprobar o ajustar las estimaciones** (secciones 4.1 a 4.3) y el método. Sin esto no se escribe código.
2. **Choque de numeración de escenarios (D-A1-1).** La especificación del Corte 2 usa EC-07 para
   privacidad y EC-08 para el registro sin conexión, pero el Anexo 1 asigna **EC-07 a EC-13** a la
   ampliación. Se propone conservar la numeración del Anexo (es la que leerá el docente), renombrar
   los escenarios propios del equipo como **EC-15** (privacidad) y **EC-16** (sin conexión) y numerar
   el escenario del asistente como **EC-14**. Hasta que el equipo decida, este documento usa EC-07
   solo en el sentido del Anexo.
3. **Módulo comercial (D-A1-2).** No está fusionado y su rama no existe; esta rama sale de `main`. Las
   promociones de la canasta dependen del puerto de extensiones (DP-1, opción B del análisis del
   módulo comercial), que todavía no existe.
4. **Bloque B.** El Anexo exige además una opción del bloque B (B1, B2 o B3). No forma parte de este
   análisis.
5. **ADR-0030 (asistente).** Requiere la aprobación de la propietaria antes de activarse, igual que el
   ADR-022.

---

## Referencias (APA 7)

Bass, L., Clements, P., & Kazman, R. (2021). *Software architecture in practice* (4.ª ed.).
Addison-Wesley Professional.

Congreso de la República de Colombia. (2012). *Ley Estatutaria 1581 de 2012, por la cual se dictan
disposiciones generales para la protección de datos personales*.

Corporación Universitaria Empresarial Alexander von Humboldt. (2026). *Anexo 1. Cambio de alcance del
corte 3: funcionalidades de ampliación* [Documento del curso].

International Organization for Standardization. (2023). *ISO/IEC 25010:2023, Systems and software
engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality
model*.

Nygard, M. (2011). *Documenting architecture decisions*. Cognitect.
