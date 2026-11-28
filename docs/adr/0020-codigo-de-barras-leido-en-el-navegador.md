# ADR-0020: Leer el código de barras en el navegador, sin enviar la imagen

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27)
- **Fecha:** 2026-11-16 (consolidado del cierre del Corte 2); archivado en el repositorio el 2026-11-27
- **Autores:** Equipo; redactado a partir del código existente con apoyo de IA
- **Escenarios de calidad afectados:** EC-01, EC-15 (confidencialidad)
- **Métricas que lo verifican:** M-01, M-15

## Contexto
Escribir el nombre de un producto desde el celular es lento y propenso a errores (RF-04). Casi todos
los productos empacados tienen un código GTIN que identifica la presentación exacta. Esta decisión
ya estaba en el código sin ADR; se registró en el consolidado del Corte 2 y aquí se archiva.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| **A. Decodificar en el navegador (`BarcodeDetector` o ZXing servido localmente) y enviar solo los dígitos** | La imagen no sale del celular; sin costo por consulta; sin servicios externos | La cámara en vivo exige HTTPS; algunos navegadores necesitan ZXing |
| B. Enviar la foto al servidor para decodificarla | Funciona igual en todos los navegadores | Viaja una imagen (datos y privacidad) y aumenta la carga del servidor |
| C. Servicio externo de reconocimiento | Sin mantener la librería | Costo, dependencia y envío de imágenes a un tercero |

## Decisión
Alternativa A. La búsqueda ofrece leer el código con la cámara; la imagen se decodifica en el
navegador y al servidor solo viajan los dígitos. El servidor valida el dígito de control GS1 en el
dominio y busca la presentación. Sin cámara queda la búsqueda por nombre. La búsqueda por foto con
IA es otra decisión ([ADR-0022](0022-reconocimiento-de-productos-por-foto-con-ia.md)) y el escaneo
en vivo de etiquetas la amplía ([ADR-0026](0026-escaneo-en-vivo-e-interpretacion-de-etiquetas.md)).

## Consecuencias
- (+) Ningún dato de imagen sale del celular para leer el código de barras.
- (+) Validar el dígito de control evita buscar con lecturas erróneas.
- (−) La cámara en vivo solo funciona con HTTPS o en `localhost`.

## Evidencia en el código
- `static/js/escanear.js` y `static/vendor/zxing/`.
- `apps/catalogo/domain/codigo_barras.py` (`normalizar_codigo`, `es_gtin_valido`), probado con TDD.
