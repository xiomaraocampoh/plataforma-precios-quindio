# ADR-0026: Escaneo en vivo e interpretación de etiquetas de precio

- **Estado:** Propuesto (apagado por defecto; requiere la aprobación del equipo y de la propietaria
  antes de activarse, como el ADR-022)
- **Fecha:** 2026-11-24
- **Autores:** Equipo; borrador con apoyo de IA, pendiente de revisión humana
- **Escenarios de calidad afectados:** EC-01 (registro ≤ 15 s), EC-06 (neutralidad), EC-04
  (desempeño); Ley 1581 de 2012
- **Métricas que lo verifican:** M-01, M-02, M-13, M-15, M-06
- **Amplía:** [ADR-022](0022-reconocimiento-de-productos-por-foto-con-ia.md) (foto manual con IA)

## Contexto

La prueba con usuarios **PUX-01** midió **M-01 = 0 %**: nadie registró un precio en 15 s o menos, y
la mediana fue de **40,6 s**. El PR #28 (registro rápido) quitó la lista de presentaciones y recuerda
la última tienda, pero la persona todavía tiene que buscar el producto y escribir el precio parada
frente a la góndola. En la tienda, el precio ya está escrito en la **etiqueta del estante**, junto con
el producto, la cantidad y a veces el precio por unidad.

El ADR-022 permite identificar un producto con una foto que la persona toma a propósito. Eso exige
encuadrar, tocar el botón y esperar. Un lector de QR, en cambio, reconoce solo apenas el código queda
en cuadro, y esa es la experiencia que se busca.

Fuerzas:

- **Rapidez (EC-01).** Cada toque y cada campo escrito cuentan en 3G y con una sola mano.
- **Exactitud (M-02).** Leer mal un precio o una unidad es peor que no leerlo: termina en un precio
  publicado equivocado.
- **Neutralidad (EC-06).** Una etiqueta de «oferta» no puede subir posiciones en la comparación.
- **Privacidad (Ley 1581).** Una cámara abierta en una tienda puede captar personas.
- **Costo.** Cada imagen enviada a la IA cuesta dinero, y un video tiene decenas de cuadros por
  segundo.
- **Inyección de instrucciones.** El texto impreso (o pegado) en una etiqueta lo lee la IA y no debe
  poder cambiar su comportamiento.

## Alternativas consideradas

| Alternativa | A favor | En contra |
|---|---|---|
| A. Solo la foto manual (ADR-022) | Ya existe; una consulta por intención explícita | No elimina toques ni espera; no lee el precio de la etiqueta; con ella M-01 sigue en 0 % |
| B. OCR en el dispositivo (p. ej. Tesseract.js o la API Shape Detection) | Gratis por cuadro; la imagen no sale del teléfono | Descarga pesada (varios MB) en 3G; precisión baja con etiquetas variadas, reflejos y letra pequeña; no sabe *qué* número es el precio ni separar «antes» de «ahora»; `TextDetector` no está disponible en la mayoría de navegadores |
| C. IA en vivo con control de envío (**elegida**) | Reconoce el empaque y la etiqueta (precio, promoción, precio por unidad, tienda) sin tocar nada; el código de barras sigue local y gratis | Costo por cuadro enviado; dependencia externa; la imagen sale del teléfono |
| D. Enviar todos los cuadros o un video | La mayor capacidad de reconocer | Costo y consumo de datos inaceptables; ráfagas que agotan el cupo en segundos |

## Decisión

Se ofrece un **escáner en vivo** opcional (C), apagado por defecto (`ESCANEO_VIVO_ACTIVO=False`) y
solo disponible con `ANTHROPIC_API_KEY`:

1. **Primero el código de barras, siempre local.** En cada cuadro, `BarcodeDetector` (o zxing de
   respaldo) intenta leer un GTIN. Si lo encuentra, abre la comparación como hoy, sin gastar nada.
2. **Control de envío** (`integraciones/domain/escaneo.py::decidir_envio`, probado con casos límite y
   replicado en `static/js/escanear.js`). Un cuadro va a la IA solo si la imagen está **quieta**
   (diferencia media entre cuadros reducidos a 160 × 120 menor a 0,05), está **nítida** (varianza del
   laplaciano ≥ 40), **no hay otro envío en curso** y pasaron **al menos 1,5 s** desde el anterior.
   Hay un **tope por sesión** (`ESCANEO_MAX_FOTOGRAMAS_SESION`, 20); al alcanzarlo el escáner se pausa y
   ofrece «Seguir escaneando». El navegador reduce el cuadro a **768 px** y lo recodifica en JPEG (se
   pierde el EXIF).
3. **Una sola llamada** (`ReconocedorClaude.escanear`) clasifica el cuadro (`producto`, `etiqueta` o
   `nada`) y extrae los datos con **salida estructurada** (`output_config.format` con JSON schema),
   `max_tokens` de 1024, esfuerzo `low`, **timeout corto** (`RECONOCIMIENTO_TIMEOUT_VIVO_S`, 6 s) y **sin
   reintentos**. El modelo es configurable aparte (`RECONOCIMIENTO_MODELO_VIVO`, por defecto
   `claude-haiku-5-5`, rápido y económico); la foto manual sigue con `RECONOCIMIENTO_MODELO`. Si la IA
   falla, el escáner sigue con el código de barras.
4. **La IA solo extrae; el dominio decide.** `interpretar_etiqueta` lee los precios colombianos
   (`$12.900`, `12,900`, `12 900`, `12.900,00`) sin confundir miles con decimales; rechaza precios ≤ 0 o
   por encima de `PRECIO_MAXIMO_ETIQUETA` y las unidades desconocidas; verifica el precio por unidad
   impreso contra el precio y la cantidad (tolerancia del 2 %). Si no cuadra, **baja la confianza y no
   corrige nada**. Los textos se limpian y se acotan (`limpiar_texto`): el texto de la etiqueta es un
   dato, no una instrucción, y así lo dice también el prompt del sistema.
5. **Lo que se muestra sale del catálogo.** El precio por unidad es el **calculado** con
   `precio_por_unidad`; el impreso aparece solo como dato. La tienda se propone únicamente si la que
   nombra la etiqueta coincide **sin dudas** con una del directorio
   (`establecimientos/domain/coincidencia.py`). Si no, se usa la última tienda de la persona y se ofrece
   «Sugerir este establecimiento». **Nunca se crea una tienda.** Si el producto no está en el catálogo,
   se ofrece «Solicitar este producto» con los datos prellenados (flujo D-05).
6. **La persona confirma.** «Registrar este precio» abre el registro rápido (PR #28) con producto,
   presentación, tienda y precio prellenados; guardar es un toque. Exige sesión (si no hay, pide
   ingresar y vuelve con los datos) y pasa por `registrar_reporte` como cualquier registro: 30 por hora,
   anomalías por mediana, idempotencia sin conexión (ADR-009) e invalidación de la caché. El reporte
   guarda `origen` (`manual` o `etiqueta`, TextChoices) para medir M-01; **no** se expone en la API
   pública (lista blanca, M-15).
7. **Neutralidad (EC-06).** Nada de esto entra en `_clave_neutral`. La promoción leída se muestra
   como la etiqueta «Promoción» en la hoja del escáner y **no se guarda** en el reporte: las promociones
   son del módulo comercial (Corte III, ADR-0014).
8. **Uso y abuso.** `POST /escanear/fotograma/` consume **el mismo cupo** por hora y por día que la
   foto (`RECONOCIMIENTOS_*`) y tiene además su `throttle_scope` «escaneo» (`LIMITE_ESCANEO`, 40/min).

## Costos por fotograma

Estimación con los precios de la API en caché al 2026-11-03. **Se deben confirmar en la página de
precios antes de activar y medir con `response.usage` en un piloto.**

| Concepto | Supuesto | Tokens |
|---|---|---|
| Imagen de 768 × 576 px | ≈ ancho × alto / 750 | ≈ 590 |
| Instrucciones, esquema y texto | prompt del sistema y JSON schema | ≈ 800 |
| Salida | JSON corto más razonamiento con esfuerzo `low` | ≈ 300 |

| Modelo | Entrada (USD/M) | Salida (USD/M) | Por fotograma | Sesión con tope de 20 | Sesión típica (3–6 envíos) |
|---|---|---|---|---|---|
| `claude-haiku-5-5` (en vivo) | 0,10 | 0,50 | ≈ USD 0,0003 | ≈ USD 0,006 | ≈ USD 0,001–0,002 |
| `claude-opus-5-5` (referencia: foto manual de 1024 px) | 4,00 | 20,00 | ≈ USD 0,012 | — | — |

Con el tope diario actual (`RECONOCIMIENTOS_POR_DIA_TOTAL=300`), el gasto máximo del escáner en vivo
es de unos USD 0,09 al día. Las instrucciones quedan por debajo del mínimo que se puede almacenar en
caché, así que no se usa caché de prompts.

## Privacidad

- La imagen se reduce y se recodifica **en el navegador** (se pierden EXIF y ubicación). Solo se envían
  cuadros quietos y nítidos, no un video.
- En el servidor la imagen **vive en memoria** durante la petición: no se guarda en disco, en la base de
  datos ni en los registros. El log anota solo el tipo de resultado y la confianza, sin usuario ni IP
  (prueba `test_la_imagen_no_se_registra_en_los_logs`).
- La pantalla avisa que los cuadros se envían a Anthropic y no se guardan. La política de tratamiento
  de datos debe mencionar el escaneo en vivo antes de activarlo (pendiente, como en el ADR-022).
- Riesgo conocido: un cuadro puede captar a otra persona en la tienda. Lo mitigan el encuadre cercano
  que exige la regla de nitidez, el tope por sesión y el botón «Pausar escaneo».

## Consecuencias

- (+) Desde que aparece la hoja, bastan **dos toques** («Registrar este precio» y «Guardar precio») y
  ningún campo escrito. Se espera mejorar M-01, pero **no se debe afirmar una mejora** hasta repetir
  PUX-01 con el escáner activo.
- (+) El código de barras sigue siendo la vía principal, gratis y privada; sin clave o con el
  interruptor apagado, todo funciona como antes.
- (+) `origen` permite comparar el tiempo y la tasa de anomalías entre los registros escritos a mano y
  los leídos de una etiqueta.
- (−) **El cupo es compartido con la foto:** con los valores actuales (20 por hora con cuenta, 10 sin
  cuenta), una sola sesión que llegue al tope agota el cupo de la hora. Al activar el escáner conviene
  subir `RECONOCIMIENTOS_POR_HORA` (p. ej. 60) y `RECONOCIMIENTOS_POR_DIA_TOTAL` según el presupuesto.
  Lo decide el equipo.
- (−) Dependencia externa y costo variable; los umbrales de quietud y nitidez son iniciales y deben
  ajustarse con teléfonos reales de gama baja.
- (−) Precisión no medida: no hay todavía un conjunto de etiquetas reales de Armenia. **No se debe
  afirmar un porcentaje de acierto** hasta medirlo.
- **Revisar esta decisión si:** el costo real por sesión supera 3 veces la estimación; la tasa de
  reportes `origen=etiqueta` en revisión por anomalía supera a la de los manuales; o el OCR en el
  dispositivo alcanza una precisión comparable sin descargas pesadas.

## Verificación

- Dominio (TDD): `tests/unit/integraciones/test_etiqueta.py`, `test_escaneo.py`,
  `tests/unit/establecimientos/test_coincidencia.py`.
- Adaptador sin red: `tests/unit/integraciones/test_reconocedor_claude.py`.
- Integración con reconocedor falso: `tests/integration/test_escaneo_vivo.py` (M-01, M-02, M-13, M-15,
  EC-06).
- Navegador con cámara falsa: `tests/integration/e2e/test_escaneo_vivo_navegador.py` (la hoja aparece
  sin tocar «Tomar foto», registro prellenado, contraste, objetivos de 24 px, `aria-live` y foco).
