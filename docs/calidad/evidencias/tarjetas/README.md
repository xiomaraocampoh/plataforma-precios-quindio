# Evidencias: tarjetas de precio completas (RF-16, M-03)

Capturas generadas el 16-11-2026 por `tests/integration/e2e/test_tarjetas_navegador.py`
(Playwright, Chromium):

```bash
GUARDAR_EVIDENCIAS=1 pytest tests/integration/e2e/test_tarjetas_navegador.py
```

| Archivo | Vista |
|---|---|
| `comparacion-movil-claro.png` / `comparacion-movil-oscuro.png` | Comparación, 390 × 844 |
| `comparacion-escritorio-claro.png` / `comparacion-escritorio-oscuro.png` | Comparación, 1280 × 900 |
| `productos-movil-claro.png` / `productos-movil-oscuro.png` | Listado de productos, 390 × 844 |
| `registro-equivale-movil.png` | Registro: «Equivale a $X por kg» en vivo |

En cada vista, la misma prueba verifica estos criterios:

- **1.4.3 Contraste.** Cada texto visible de la tarjeta alcanza ≥ 4,5:1 (≥ 3:1 si es texto grande)
  sobre su fondo real, mezclando las capas translúcidas (`tests/integration/e2e/contraste.js`).
  La prueba encontró un fallo previo: «Sigue igual» y «Denunciar» tenían 3,02:1 sobre la tarjeta
  oscura. Se corrigió en `static/css/app.css`.
- **2.5.8 Tamaño del objetivo.** Los enlaces, botones y `summary` de la tarjeta miden 24 × 24 px o
  más.
- **1.4.10 Reajuste.** No hay desplazamiento horizontal a 390 px.
- **1.4.1 Uso del color.** La confianza siempre se dice con texto («Confianza media») y no depende
  solo del color.
- **1.3.1 y 3.2.5.** Las verifica `tests/integration/test_tarjetas.py`: cada tarjeta tiene su `h2`
  con `aria-labelledby`, los encabezados no saltan niveles, no hay referencias ARIA rotas y
  «Ver en el mapa» avisa que se abre en otra pestaña.

Esta verificación no reemplaza una revisión con axe o Lighthouse y un lector de pantalla; se
recomienda hacerla antes del cierre del corte.
