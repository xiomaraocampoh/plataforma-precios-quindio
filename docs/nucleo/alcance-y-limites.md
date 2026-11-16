# Alcance y límites conocidos del núcleo

Documento de apoyo para la sustentación. Dice con claridad **qué hace la plataforma, qué no hace y
por qué**. Cada límite lleva su razón (una decisión registrada, un requisito de la guía o el alcance
del corte) y el paso que habría que dar para cubrirlo.

- **Fecha:** 2026-11-16
- **Base:** `main` (`ccc0c8c`) más el filtro por rango de precio de esta rama
- **Cómo se verificó:** lectura del código y de las rutas, y ejecución de las pruebas. Las filas que
  dependen de lo informado por el equipo (y no del repositorio) están marcadas.

**Nota sobre los ADR citados:** usan la numeración de los documentos del Drive del 14 de noviembre
de 2026; en `docs/adr/` aún no coincide del todo (decisión D-1 pendiente del equipo).

**Estado:** *Existe* · *Parcial* · *No existe* · *Pendiente* (planificado, aún sin hacer).

## 1. Catálogo, marcas y filtros

| Tema | Estado | Qué hay hoy | Por qué | Para cubrirlo |
|---|---|---|---|---|
| Crear presentaciones | Existe | El administrador las agrega dentro de cada producto en `/admin/` (cantidad y unidad). Cualquier usuario puede solicitarlas en `/catalogo/solicitar/`; quedan pendientes hasta que moderación las apruebe | RF-06: el catálogo es canónico para poder comparar por unidad | — |
| Crear unidades nuevas (libra, docena…) | No existe | Hay 5 unidades fijas: g, kg, ml, L y und (`catalogo/domain/normalizacion.py`) | Cada unidad necesita una regla de conversión probada con TDD; solo se comparan magnitudes iguales | Agregar la unidad, su conversión y sus pruebas |
| Marcas | Parcial | Es un campo de texto del producto; **no hay una tabla de marcas**. Se filtra por marca exacta en `/productos/?marca=` | Para el núcleo bastaba el texto con la restricción única (nombre normalizado + marca) que evita duplicados | Un modelo `Marca` con su migración |
| Fotos de productos | No existe | No hay campos de imagen ni almacenamiento de archivos | No está en los requisitos. El análisis de otras plataformas (Open Prices) concluyó que exigir foto añade fricción (EC-01) y puede exponer datos personales (Ley 1581) | Almacenamiento de archivos, política de privacidad y moderación de imágenes |
| Escaneo de código de barras | Existe, con límites | Botón en el buscador: cámara en vivo o foto, decodificada **en el navegador** (BarcodeDetector o ZXing vendorizado en `static/vendor/zxing`). Solo viajan los dígitos | RF-04. Una foto procesada en el servidor sería dato personal potencial (Ley 1581) y añade fricción (EC-01) | — |
| Cámara en vivo | Parcial | Exige HTTPS o `localhost`; por HTTP en la red local (p. ej. `http://192.168…`) el navegador la bloquea y queda «Tomar una foto» o escribir el número | Restricción de seguridad de los navegadores, no del código | Servir con HTTPS (el despliegue en la nube ya lo hace) |
| Reconocer un producto por foto (IA) | Existe, opcional y apagada por defecto | Con `ANTHROPIC_API_KEY`: el modelo de Anthropic extrae nombre, marca y tamaño de la foto; la persona confirma entre candidatos del catálogo. Requiere sesión y tiene tope por hora | ADR-019. Envía la foto a un tercero (se reduce y limpia en el navegador, no se guarda): exige aprobar la política de datos. **Sin medición de precisión aún** | Probar con fotos reales de Armenia, elegir modelo (costo) y aprobar el ADR |
| Filtro por **rango de precio** | Existe | En la comparación: «Precio desde» y «Precio hasta», sobre el **precio total** del empaque. Acepta `2.500`, `$2.500` y `2500,50`; si es inválido avisa y no filtra. Solo reduce: el orden neutral no cambia | Decisión del equipo (2026-11-16). Se filtra el precio total porque es el que ve primero la persona (RF-16) | Un filtro equivalente por precio por unidad |
| Filtro por unidad | Parcial | Solo en el administrador (presentaciones). En la web la comparación ya ordena por precio por unidad | RF-16: el precio total va primero y el precio por unidad es un dato secundario (la encuesta mostró que el 90 % compara por precio total o por marca) | Un filtro por unidad base (kg, L, und) |
| Filtros en la API | No existe | `GET /api/v1/comparacion/<id>/` no recibe parámetros de filtro | Los filtros se hicieron para la pantalla | Agregar parámetros opcionales (cambio aditivo permitido en `/v1`) |

## 2. Vigencia, confianza y alertas

| Tema | Estado | Qué hay hoy | Por qué | Para cubrirlo |
|---|---|---|---|---|
| Precios vencidos | Existe | Dejan de mostrarse como vigentes: 7 días (reportado), 3 (perecedero) y 30 (oficial). El botón «Sigue igual» renueva la vigencia | ADR-005 / EC-02 | — |
| Datos de prueba de precios viejos | Existe | `python manage.py cargar_demo --con-vencidos` carga precios justo fuera de la ventana (8, 4 y 31 días) y otros dentro del límite (6, 2 y 29 días) | Para ensayar el vencimiento y «Sigue igual» | — |
| Aviso que empuje a confirmar un precio viejo | No existe | Solo el botón; no hay notificaciones | Las alertas (RF-C08) son opcionales y el equipo las difirió (ADR-016) | Una tarea programada y envío de correo |
| Precios «muy altos» | Existe, con otro mecanismo | Un precio a más de 50 % de la mediana de los últimos 7 días (con al menos 3 muestras) queda **«en revisión»** y se muestra con confianza baja | ADR-006 / EC-03 | — |
| Alerta al usuario por precio alto o bajo | No existe | — | ADR-016 | Ver arriba |

## 3. Datos externos

| Tema | Estado | Qué hay hoy | Por qué | Para cubrirlo |
|---|---|---|---|---|
| Datos del DANE (SIPSA) | Parcial | Se importa un archivo CSV con `python manage.py importar_sipsa archivo.csv`. Se muestra como bloque aparte, «Referencia mayorista», que **no entra en el orden** | ADR-010: es una referencia, nunca compite con precios de tienda | Cliente en línea (`ClienteSipsa`, pendiente) |
| Alertar si un precio supera al del DANE | No existe ni está en el diseño | — | SIPSA es mayorista (por kg): casi cualquier precio de tienda lo superaría, así que la alerta sería ruido | — |

## 4. Módulo comercial y registro

| Tema | Estado | Qué hay hoy | Por qué | Para cubrirlo |
|---|---|---|---|---|
| Entrar como dueño de un comercio | No existe (Corte 3) | El rol «comercio» existe en la base de datos, pero ninguna pantalla lo usa; `apps/comercios` está reservado | La guía introduce el módulo como cambio de alcance en el Corte 3, para medir EC-05 | Ver el análisis de impacto del módulo comercial |
| Registro sin conexión | Parcial | El servidor ya es idempotente por `id_cliente` (un reenvío no duplica). **Falta la cola en el navegador**: hay un `TODO` en el formulario | ADR-009 y RF-12 (prioridad S). En la encuesta, el 80 % reportó buena señal | Guardar el registro en el navegador y reenviarlo al recuperar la conexión (M-22) |

## 5. Entrega del Corte 2 *(según lo informado por el equipo el 2026-11-16; no verificado en el repositorio)*

| Tema | Estado |
|---|---|
| Despliegue en internet | Pendiente. Corre en local con Docker Compose y en el CI; falta elegir proveedor (ADR-017) |
| SonarQube | Configurado, aún no ejecutado |
| Prueba de usabilidad con 5 personas (EC-01) | Pendiente; el kit de la prueba está listo |

## Cómo presentarlo en la sustentación

Para cada límite conviene decir tres cosas: **qué no hace**, **por qué** (la decisión o el alcance) y
**qué haría falta para cubrirlo**. Un límite dicho con su razón muestra criterio de diseño; uno
descubierto por quien evalúa suele leerse como un descuido.
