# Evidencias: escáner en vivo (ADR-0026, M-01, M-03)

Capturas generadas el 24-11-2026 por `tests/integration/e2e/test_escaneo_vivo_navegador.py`
(Playwright, Chromium, cámara falsa con un video `.y4m` de una etiqueta y reconocedor falso):

```bash
GUARDAR_EVIDENCIAS=1 pytest tests/integration/e2e/test_escaneo_vivo_navegador.py
```

| Archivo | Vista |
|---|---|
| `hoja-etiqueta-movil-light.png` / `hoja-etiqueta-movil-dark.png` | Hoja de la etiqueta, 390 × 844, sin tocar «Tomar foto» |
| `registro-prellenado-movil-light.png` / `registro-prellenado-movil-dark.png` | Registro con producto, presentación, tienda y precio prellenados |

En cada vista, la misma prueba verifica:

- **Aparición sin tocar nada:** la hoja se abre porque el cuadro quieto y nítido se envió solo.
- **1.4.3 Contraste:** cada texto de la hoja alcanza 4,5:1 (3:1 si es grande), también con el sistema
  en modo oscuro. La hoja usa tokens claros propios.
- **2.5.8 Tamaño del objetivo:** los enlaces y botones de la hoja y de los controles miden 24 px o más.
- **4.1.3 Mensajes de estado:** el resultado está en una región `aria-live="polite"` y el foco va al
  título de la hoja.
- **1.4.1 Uso del color:** «Promoción» lleva texto y una estrella, no solo color.
- **M-01:** desde la hoja bastan dos toques, «Registrar este precio» y «Guardar precio».

Esta verificación no reemplaza una revisión con axe o Lighthouse, un lector de pantalla y teléfonos
reales de gama baja. Los umbrales de quietud y nitidez deben ajustarse en campo.
