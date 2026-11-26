# ADR-0024: Fotos de producto guardadas en la base de datos y subidas desde el panel

- **Estado:** Propuesto
- **Fecha:** 2026-11-19
- **Autores:** Equipo; redactado con apoyo de IA
- **Escenarios de calidad afectados:** EC-01 (registro rápido), EC-04 (carga), EC-06 (neutralidad)
- **Métricas que lo verifican:** M-01, M-03, M-15, M-18

## Contexto
PUX-01 mostró que reconocer el producto en listas de texto era lo más lento. Se quiere una
presentación tipo catálogo (foto del empaque, descripción y precios por establecimiento). El
despliegue (Render, plan gratuito) tiene disco efímero: lo subido a una carpeta se pierde en cada
reinicio. Contenido y derechos de las fotos los decide el equipo; no se descargan de terceros.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| Archivos en disco (`MEDIA_ROOT`) | Simple | Se pierden en Render gratuito |
| Almacenamiento externo (S3, Cloudinary) | Escalable | Cuenta, secretos y costo nuevos; datos fuera del país |
| Solo íconos por categoría | Sin derechos de autor | No reconoce el producto concreto |
| **Foto reducida en la base de datos** | Sobrevive a reinicios; respaldo con la base; sin servicios nuevos | Aumenta el tamaño de la base; hay que limitar el peso |

## Decisión
- Tabla aparte `FotoProducto` (uno a uno con `Producto`), con los bytes en un `BinaryField`, el tipo
  y una versión (`sha256[:12]`). Los listados la unen con `defer("foto__contenido")`: nunca traen los bytes.
- Se sube solo desde el panel (`/panel/`, Editor de catálogo) o con `manage.py cargar_fotos`. La
  acción queda en la auditoría (M-14). No hay subida pública.
- Reglas de validación en `catalogo/domain/fotos.py` (Python puro); el procesado con **Pillow**
  (nueva dependencia) en `catalogo/imagenes.py`: valida antes de decodificar, corrige la orientación,
  quita metadatos EXIF, recorta cuadrado y reduce a 480×480 WebP.
- Se sirve en `/productos/<id>/foto/?v=<versión>` con `ETag` y caché inmutable; solo productos públicos.
- Sin foto se muestra el ícono de la categoría (`domain/iconos.py`).
- `Producto.descripcion` (opcional, 500 caracteres) se edita en el panel y se muestra en la ficha.
- **Neutralidad (EC-06):** la foto y la descripción son presentación; no entran en `_clave_neutral`.
  El orden de los precios sigue siendo por precio por unidad.
- **Privacidad (Ley 1581):** la foto quita EXIF (ubicación, autor) y se pide sin personas ni datos
  personales; no se muestra nada del reportante.

## Consecuencias
- **Positivas:** catálogo reconocible de un vistazo; fotos que no se pierden; sin servicios externos.
- **Negativas:** la base crece (≈ 20–40 KB por foto). Pillow es una dependencia nueva que procesa
  archivos no confiables: por eso se limita tamaño (5 MB), formato y dimensiones antes de decodificar.
  La migración de datos de siembra no puede usar columnas nuevas del modelo real; por eso la foto va en
  tabla aparte y la prueba de «migrate después de cargar» ejecuta las funciones de siembra sin
  retroceder el esquema.
- **Riesgos:** derechos de autor de las fotos (usar fotos propias del equipo o con permiso);
  crecimiento de la base si el catálogo supera varios miles de productos.
- **Revisar si:** el catálogo supera ≈ 5 000 productos o la base gratuita se acerca a su límite;
  entonces pasar a almacenamiento de objetos con la misma interfaz de servicio.
