# ADR-0030: Asistente de compras con la API de Anthropic: la IA interpreta, el dominio calcula

- **Estado:** Propuesto (requiere la aprobación del equipo y de la propietaria antes de activarse, como el ADR-022)
- **Fecha:** 2026-11-24
- **Autores:** Equipo; borrador con apoyo de IA, pendiente de revisión humana
- **Escenarios relacionados:** EC-14 (propio), EC-07 (Anexo 1), EC-06; Ley 1581 de 2012
- **Métricas que lo verifican:** M-25, M-15, M-06, M-24
- **Plantilla:** 8.1 del Anexo 1 (adaptada de Nygard, 2011)

## Contexto
Es un **plus** del equipo, fuera del mínimo de A1: la persona escribe «mercado de la semana para 4
personas» o «lo del desayuno» y obtiene la canasta comparada sin buscar producto por producto.

Fuerzas:

- **Exactitud y neutralidad.** Un modelo de lenguaje puede inventar precios o «recomendar» una tienda.
  EC-07 y EC-06 exigen que totales, faltantes y orden salgan de reglas verificables.
- **Inyección de instrucciones.** El texto de la persona y los nombres del catálogo (que pueden venir
  de solicitudes de usuarios) llegan al modelo; no deben poder cambiar su comportamiento.
- **Privacidad (Ley 1581).** Lo que se envía a Anthropic es una transferencia a un tercero.
- **Costo y abuso.** Cada mensaje tiene costo por tokens; el asistente puede usarse sin cuenta.
- **Precedente.** `ReconocedorClaude` (ADR-022) ya establece el patrón puerto/adaptador con timeout,
  modelo configurable, topes de uso y desactivación sin `ANTHROPIC_API_KEY`.

Hechos de la API consultados para esta decisión (referencia de la API de Anthropic, precios en caché
al 2026-11-03; **se deben confirmar en la página de precios antes de activar**):

| Modelo | ID | Entrada (USD / millón de tokens) | Salida (USD / millón de tokens) |
|---|---|---|---|
| Claude Opus 5.5 | `claude-opus-5-5` | 4,00 | 20,00 |
| Claude Sonnet 5.5 | `claude-sonnet-5-5` | 2,00 | 10,00 |
| Claude Haiku 5.5 | `claude-haiku-5-5` | 0,10 (hasta 100 K de entrada) | 0,50 |

En Opus 5.5 y Sonnet 5.5, forzar una herramienta (`tool_choice` de tipo `any` o `tool`) devuelve
error 400: se usa `tool_choice: auto` con `strict: true` en cada herramienta. En Opus 5.5 el
razonamiento no se puede desactivar; la profundidad se controla con `output_config.effort`.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| A. Sin IA: solo el formulario de la canasta | Cero costo, cero riesgo de datos | No cubre la necesidad del plus (pedir en lenguaje natural) |
| B. La IA calcula y redacta la respuesta completa | Respuesta fluida | Puede inventar precios, totales o el orden; imposible garantizar EC-07, EC-06 ni EC-14 |
| C. Una sola llamada que extrae una lista estructurada (como ADR-022) y el sistema hace el resto | Simple; sin bucle; costo mínimo | No puede preguntar ante ambigüedad ni explicar el resultado en conversación |
| **D. Tool use con cálculo determinista: la IA interpreta y llama herramientas de solo lectura; el dominio calcula** | La IA nunca produce las cifras; aclara ambigüedades; la explicación es conversacional | Un bucle que hay que acotar; más pruebas; costo por mensaje mayor que C |

## Decisión
**D.** La IA interpreta la petición, pide aclaraciones y explica; **los cálculos, el orden y las cifras
son del dominio** de la canasta (ADR-0027 a 0029).

1. **Puerto y adaptador.** `integraciones/clients/asistente.py` define el puerto `ModeloConversacional`
   y el adaptador `AsistenteClaude` (SDK oficial `anthropic`), con timeout, modelo configurable
   `ASISTENTE_MODELO` (por defecto `claude-opus-5-5`, como `RECONOCIMIENTO_MODELO`; Sonnet 5.5 o Haiku
   5.5 se evalúan con una prueba de calidad y costo) y toda falla traducida a «no disponible». Las
   pruebas usan un cliente falso que devuelve llamadas de herramienta predefinidas, sin red.
2. **Bucle de agente en el servidor**, escrito a mano (no el *Tool Runner* beta) para controlar cada
   vuelta: **máximo 6 llamadas de herramienta por mensaje**; al superarlo se corta y se muestra lo
   que el dominio haya calculado. `stop_reason` se revisa siempre (`refusal`, `max_tokens`).
3. **Herramientas, todas de solo lectura y con esquema estricto:**
   - `buscar_productos(texto)` → candidatos del catálogo (id, nombre, presentaciones).
   - `armar_canasta(items: [{producto_id, cantidad, unidad}])` → valida con el dominio (máx. 20, ids
     existentes, cantidad > 0, unidad compatible) y devuelve errores como datos.
   - `calcular_canasta(municipio?, criterio?)` → el resultado de `calcular_canasta` y
     `ordenar_opciones`.
   Ninguna herramienta escribe en la BD, envía correos ni abre URLs.
4. **Las cifras se muestran en una tarjeta del sistema**, no en el texto del modelo: la plantilla
   HTMX renderiza el resultado del dominio (las 3 opciones, total, cobertura, faltantes, criterio).
   El texto del modelo pasa por un validador de dominio: si menciona un precio, total o cantidad que no
   está en el resultado, **se descarta** y solo se muestra la tarjeta (EC-14).
5. **Neutralidad.** El prompt del sistema prohíbe recomendar por marca, patrocinio o preferencia; el
   orden lo decide `ordenar_opciones` y el modelo solo lo conoce por el resultado que recibe.
6. **Ambigüedad e inexistencia.** Si `buscar_productos` devuelve varios candidatos («leche»), el
   asistente pregunta y la interfaz muestra botones con las opciones; si no hay ninguno, lo dice y
   ofrece «Solicitar producto» (flujo existente del catálogo).
7. **Inyección.** El texto de la persona y del catálogo se envía como datos delimitados; el prompt del
   sistema indica que no son instrucciones. Aun si el modelo las obedeciera, solo puede llamar
   herramientas de lectura cuyos argumentos valida el dominio, y no controla las cifras ni el orden.
8. **Privacidad (Ley 1581).** No se envían nombre, usuario, correo ni ubicación exacta; el municipio
   solo si la persona lo escribe. La conversación vive en la sesión, se borra al cerrarla y **no se
   guarda en la BD ni en los registros** (los registros guardan solo eventos sin contenido). La
   política de tratamiento de datos se actualiza antes de activar la función.
9. **Costo y abuso.** Topes por sesión, por huella de IP (nunca la IP en claro) y por usuario, más un
   tope diario total, con `core/limites.py`; `throttle_scope = "asistente"`. El prompt del sistema y
   las definiciones de herramientas son fijos (sin fechas ni datos por petición) para aprovechar el
   *prompt caching*. Sin `ANTHROPIC_API_KEY`, el asistente no aparece y queda la canasta normal.

## Consecuencias
- (+) La exactitud y la neutralidad no dependen del modelo: dependen de reglas ya probadas con TDD.
- (+) Inclusión: quien no sabe buscar producto por producto puede pedir en sus palabras.
- (−) **Dato potencialmente personal a un tercero** (el texto de la persona): exige actualizar la
  política de datos y la aprobación de la propietaria.
- (−) Costo por mensaje y dependencia externa. No se afirma un costo por conversación hasta medirlo
  (`usage` de las respuestas) en una muestra.
- (−) El validador de cifras puede descartar respuestas correctas pero redactadas con números en otro
  formato; se acepta: la tarjeta siempre muestra el resultado.
- (−) Más superficie de pruebas (bucle, validación, inyección, topes).
- **Alternativa más estricta disponible:** no entregar al modelo los montos (solo nombres, cobertura y
  faltantes). Se adopta si el validador muestra descartes frecuentes.
- **Fuera de la prueba de carga** (EC-07): su latencia es la de la API externa y cada petición tiene
  costo; se mide por aparte en una muestra pequeña.
- **Evidencia que haría revisar la decisión:** cifras no derivadas que superen el validador, casos de
  inyección con efecto, o un costo por conversación que supere el presupuesto del equipo.

## Verificación
1. **M-25 (EC-14):** pruebas unitarias del validador de salida y de integración con el cliente falso
   que devuelve un texto con un total inventado: la respuesta se descarta y se muestra la tarjeta.
2. **Inyección:** conjunto de mensajes y nombres de producto con instrucciones («ignora tus reglas…»);
   el resultado y el orden son idénticos a los de la misma petición sin ellas.
3. **Límites:** prueba con un cliente falso que pide más de 6 herramientas (se corta), y pruebas de
   tope por sesión, IP y usuario (respuesta 429 o mensaje de tope).
4. **M-15:** prueba que inspecciona el cuerpo enviado al cliente falso: no contiene nombre, usuario,
   correo ni ubicación de la persona; y que la conversación no queda en la BD.
5. **M-06:** el orden de la tarjeta es el de `ordenar_opciones` (misma prueba de neutralidad de la
   canasta).
6. **Ambigüedad e inexistencia:** pruebas con «leche» (botones de opciones) y con un producto que no
   existe («Solicitar producto»).
7. **Sin clave:** con `ANTHROPIC_API_KEY` vacía, `/asistente/` no aparece en la navegación y responde
   404.
