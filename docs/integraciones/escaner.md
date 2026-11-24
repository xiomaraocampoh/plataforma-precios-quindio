# Escáner: código de barras, foto y modo en vivo · RF-04 y RF-11

El botón de la cámara en el buscador de inicio abre el escáner (`static/js/escanear.js`). Tiene tres
niveles, y cada uno funciona aunque falte el siguiente:

| Nivel | Qué hace | Sale del teléfono | Requiere |
|---|---|---|---|
| Código de barras | Lee un GTIN con `BarcodeDetector` (o zxing de respaldo) y abre la comparación | Solo los dígitos | Nada |
| Foto con IA (ADR-022) | «Tomar foto» o una imagen de la galería: identifica el producto | La foto, reducida a 1024 px | `ANTHROPIC_API_KEY` |
| Escáner en vivo (ADR-0026) | Reconoce solo el empaque o la **etiqueta de precio**, como un lector de QR | Algunos cuadros quietos, a 768 px | `ANTHROPIC_API_KEY` y `ESCANEO_VIVO_ACTIVO=True` |

## Cómo funciona el modo en vivo

1. La cámara queda abierta. En cada cuadro se intenta primero el **código de barras**, que es local y
   gratis.
2. Si no hay código, `decidir_envio` (en `apps/integraciones/domain/escaneo.py`, copiada en el JS)
   decide si vale la pena enviar el cuadro. Debe cumplir todo esto:
   - **quieto**: la diferencia media con el cuadro anterior es menor de 0,05;
   - **nítido**: la varianza del laplaciano es de 40 o más;
   - no hay otro envío en curso;
   - pasaron 1,5 s (`ESCANEO_INTERVALO_MS`) desde el último;
   - no se llegó al tope de la sesión (`ESCANEO_MAX_FOTOGRAMAS_SESION`). Al llegar, el escáner se
     pausa y ofrece «Seguir escaneando».
3. `POST /escanear/fotograma/` responde:
   - **204** si no hay nada: el escáner sigue sin abrir nada;
   - **200** con la hoja de **producto** («Ver comparación», o «Solicitar este producto» si no está en
     el catálogo);
   - **200** con la hoja de **etiqueta**: precio grande, marca «Promoción» si aplica, precio por unidad
     **calculado**, tienda propuesta, «Registrar este precio» y «Ver comparación»;
   - **429** por el cupo o por el ritmo, y **503** si la IA no respondió: el escáner sigue con el código
     de barras.
4. Cuando reconoce algo, vibra (salvo con `prefers-reduced-motion`), lo anuncia por `aria-live`, lleva
   el foco al título de la hoja y **pausa** el escaneo hasta que la persona cierre la hoja o elija una
   acción.
5. «Registrar este precio» abre `/precios/registrar/` con todo prellenado y `origen=etiqueta`. La
   persona revisa y toca «Guardar precio». Sin sesión, primero inicia sesión y vuelve con los datos.

Controles: «Producto o etiqueta» o «Solo código de barras» (este no envía nada a la IA), «Pausar
escaneo» (`aria-pressed`), «Tomar foto» de respaldo, «Galería» y «Escribir».

## Probar en local

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...        # clave real: cada cuadro enviado cuesta (ver ADR-0026)
ESCANEO_VIVO_ACTIVO=True
python manage.py runserver
```

- La cámara en vivo exige un contexto seguro: `http://localhost:8000` sirve en el computador. En un
  celular de la misma red hace falta HTTPS (por ejemplo un túnel); por HTTP solo queda la galería.
- Sin clave, las pruebas cubren todo con un reconocedor falso:
  `pytest tests/unit/integraciones tests/integration/test_escaneo_vivo.py` y, con
  `python -m playwright install chromium`,
  `pytest tests/integration/e2e/test_escaneo_vivo_navegador.py` (cámara falsa con un video `.y4m` que
  la prueba genera).

## Variables

| Variable | Por defecto | Para qué |
|---|---|---|
| `ESCANEO_VIVO_ACTIVO` | `False` | Interruptor del modo en vivo |
| `RECONOCIMIENTO_MODELO_VIVO` | `claude-haiku-5-5` | Modelo rápido y económico para los cuadros |
| `RECONOCIMIENTO_TIMEOUT_VIVO_S` | `6` | Tiempo máximo por cuadro, sin reintentos |
| `ESCANEO_MAX_FOTOGRAMAS_SESION` | `20` | Tope de cuadros enviados por sesión |
| `ESCANEO_INTERVALO_MS` | `1500` | Mínimo entre dos envíos |
| `PRECIO_MAXIMO_ETIQUETA` | `2000000` | Un precio leído mayor se descarta |
| `LIMITE_ESCANEO` | `40/min` | Ritmo máximo del endpoint (`throttle_scope` «escaneo») |
| `RECONOCIMIENTOS_POR_HORA`, `_ANONIMO_POR_HORA`, `_POR_DIA_TOTAL` | 20, 10, 300 | Cupo **compartido** con la foto: cada cuadro cuenta |

## Privacidad

La imagen no se guarda en el servidor (ni en disco, ni en la base de datos, ni en los registros). El
log solo anota el tipo de resultado y la confianza. El aviso del escáner dice que los cuadros van a
Anthropic y no se guardan.
