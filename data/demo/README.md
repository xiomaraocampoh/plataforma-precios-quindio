# Datos de prueba (data/demo/)

> **Datos de prueba; pueden no coincidir con los precios actuales.**
> No son datos oficiales ni una lista de precios de ningún comercio. Sirven para probar la
> aplicación en local con un catálogo y unos precios realistas.

Fecha de consulta de las fuentes: **16 de noviembre de 2026**.

## Cómo cargarlos

```bash
python manage.py cargar_datos_prueba                  # todo (idempotente)
python manage.py cargar_datos_prueba --solo-catalogo  # sin precios ni escenarios
python manage.py cargar_datos_prueba --limpiar        # borra los de prueba y vuelve a cargar
CUENTAS_PRUEBA_PASSWORD=... python manage.py crear_cuentas_prueba   # para poder ingresar
```

Los precios quedan con `es_demo=True`. `--limpiar` borra solo eso. Si un dato real usa un
producto o un establecimiento de prueba, ese producto o establecimiento se conserva.
Los autores son las cuentas de `crear_cuentas_prueba`. Si no existen, se crean sin contraseña
utilizable.

## Archivos

| Archivo | Contenido |
|---|---|
| `marcas.csv` | 67 marcas reales colombianas e importadas |
| `categorias.csv` | 14 categorías; `perecedera` (si/no) cambia la vigencia a 3 días |
| `productos.csv` | 70 productos: nombre, marca, categoría (5 marcas o más por categoría) |
| `presentaciones.csv` | 97 presentaciones: cantidad y unidad (g, kg, ml, L, und) y código de barras |
| `establecimientos.csv` | 13 locales: 8 de cadenas, 4 tiendas ficticias y 1 sugerido pendiente |
| `precios.csv` | 438 precios: presentación, local, precio, fuente y antigüedad |
| `acciones.csv` | 4 «Sigue igual» y 2 denuncias abiertas |
| `solicitudes.csv` | 2 solicitudes de producto. Una se parece a un producto existente (D-05) |

`precios.csv` no guarda una fecha fija. Guarda `dias_atras` y `horas_atras` contados desde el
momento de la carga, para que el conjunto no envejezca. `fecha_consulta` es el día en que se
consultó la fuente. `fuente_tipo` es `reportante` u `oficial`; en la aplicación, `oficial` es la
fuente «comercio».

## Fuentes

Las páginas se consultaron a mano y fueron pocas. No se automatizaron descargas, no se saltó
robots.txt, inicios de sesión ni CAPTCHA, y no se descargaron imágenes.

| Sitio | Resultado |
|---|---|
| exito.com | Las páginas de producto responden 403 a lectores automáticos, y no se intentó saltar el bloqueo. Se tomaron 6 precios que el buscador muestra para la URL pública de la página (ver abajo). |
| d1.com.co | La portada solo muestra 3 kits de donación con precio. No sirvió para precios de canasta. |
| aratiendas.com | La portada no muestra precios ni un localizador legible. |
| olimpica.com, carulla.com | robots.txt permite las páginas de producto, pero no se encontró ninguna página legible con precio de estas referencias. Carulla no tiene una sede confirmada en el Quindío, así que no se le asignaron precios. |
| LosPrecios.co | Sigue el historial de precios de un solo comercio en línea. No sirve para comparar supermercados. |

**Precios con URL** (fuente `oficial`, en «Éxito Armenia Centro»):

| Producto | Precio | URL |
|---|---|---|
| Café molido Águila Roja 125 g | $8.060 | https://www.exito.com/cafe-tostado-y-molido-125-gr-770212/p |
| Arroz blanco premium Diana 4 kg | $26.150 | https://www.exito.com/arroz-diana-premium-4-kg-317356/p |
| Aceite vegetal multiusos Frescampo 750 ml | $6.600 | https://www.exito.com/aceite-vegetal-frescampo-750-ml-3125554/p |
| Aceite vegetal multiusos Frescampo 2000 ml | $14.890 | https://www.exito.com/aceite-vegetal-frescampo-2000-ml-3125555/p |
| Leche deslactosada Alquería 1100 ml | $6.480 | https://www.exito.com/leche-deslactosada-en-bolsa-x-1100-ml-627371/p |
| Papel higiénico acolchamax Familia x12 | $25.900 | https://www.exito.com/papel-acolchamax-extra-grande-familia-288-mts-3117420/p |

Los otros 432 precios dicen `fuente = aproximado`. Son precios de referencia razonables para
noviembre de 2026. Para cada local se aplicó un factor de precio: los discount son más baratos y
las tiendas de barrio más caras. A eso se sumó una variación fija de ±3 %.

**Códigos de barras.** `7702511000021` (Arroz Diana 1 kg) y `7702511000014` (Diana 500 g, el de la
solicitud pendiente) son públicos: vienen de
[Open Food Facts](https://world.openfoodfacts.org/product/7702511000021/arroz-diana).
Los códigos `2000000001012`, `…029`, `…036` y `…043` son internos de prueba. Usan el prefijo GS1
20, de circulación restringida, así que no pertenecen a ningún producto real. Sirven para probar
el escáner.

**Direcciones.** Los localizadores oficiales de tiendas no se pudieron leer: Éxito responde 403,
Olímpica devuelve una página truncada y la de Ara es demasiado grande.

- *Éxito Armenia Centro* (Cl. 19 # 17-27) sale de la
  [lista de puntos Éxito de la Cámara de Comercio de Medellín](https://www.camaramedellin.com.co/Portals/0/Documentos/Matricula-Mercantil/PUNTOS%20EXITO%20MEDELLIN%20Y%20REGIONES44eb.pdf).
- *Olímpica Portal del Quindío* (Av. Bolívar # 19N-46) sale de un
  [listado de puntos de Banco Serfinanza (2020)](https://bancoserfinanza.com/wp-content/uploads/2020/11/OFICINAS-Y-PUNTOS-17-11-2020.pdf).
- Las demás sedes de cadena tienen `fuente_direccion = aproximado`: el municipio y el barrio son
  plausibles, pero **la dirección no está verificada**.
- Las 5 tiendas de barrio son **ficticias** (`ficticia = si`).

## Escenarios para probar las reglas

| Escenario (`escenario` en precios.csv) | Dónde | Qué se espera |
|---|---|---|
| `vencido_reportado` / `limite_reportado` | Arroz Florhuila 1 kg: Tienda El Paisa (8 días) / Tienda La Bendición (6 días) | El primero no se muestra; el segundo sí |
| `vencido_perecedero` / `limite_perecedero` | Leche Colanta 1100 ml: Tienda Doña Gloria (4 días) / Tienda El Paisa (2 días) | Ventana de 3 días |
| `vencido_oficial` / `limite_oficial` | Chocolate Corona 250 g: Olímpica (31 días) / Éxito Calarcá (29 días) | Ventana de 30 días |
| `base_anomalia` + `anomalo` | Café Sello Rojo 500 g en D1 Granada: 3 precios cerca de $19.700 y uno de $31.500 | El de $31.500 queda **en revisión** |
| `confianza_alta` | Arroz Diana 1 kg en Ara Centro: 3 personas, $6.150 | Confianza **alta** |
| `acciones.csv` | 4 «Sigue igual» y 2 denuncias | Cola de moderación con denuncias abiertas |
| `solicitudes.csv` | «Arroz blanco premiun» Diana 500 g | El moderador ve el parecido con «Arroz blanco premium» |
| `establecimientos.csv`, `estado = pendiente` | Tienda La Esperanza (Quimbaya) | Sugerencia pendiente de aprobar |
| Distinto tamaño | Roa, Supremo y Riopaila 500 g y 1 kg; Fab 500 g y 1 kg | Comparación por precio por kg |
