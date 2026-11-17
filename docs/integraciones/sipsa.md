# Integración SIPSA (DANE) · RF-07

El Sistema de Información de Precios y Abastecimiento del Sector Agropecuario (SIPSA) del DANE
publica precios **mayoristas** diarios por mercado. La plataforma los muestra como **referencia**,
en una tarjeta aparte de la comparación. Nunca entran al orden neutral (EC-06), porque no son
precios de venta al público en tiendas del Quindío.

## Estado

| Pieza | Estado |
|---|---|
| Importación desde CSV descargado a mano (`importar_sipsa archivo.csv`) | Implementada |
| Servicio web SOAP del DANE (`importar_sipsa --servicio-web`) | **Implementada** (operación `promediosSipsaCiudad`) |

## Servicio web (SOAP 1.2)

- **WSDL:** <https://appweb.dane.gov.co/sipsaWS/SrvSipsaUpraBeanService?WSDL>.
- **Documentación:** «Documentación Webservice SIPSA», DANE, marzo de 2020, en la
  [página del servicio web de SIPSA](https://www.dane.gov.co/index.php/estadisticas-por-tema/agropecuario/sistema-de-informacion-de-precios-sipsa/servicio-web-para-consulta-de-la-base-de-datos-de-sipsa).
- No pide autenticación: son datos públicos. El DANE publica los datos diarios después de las 2 p. m.
- **Operación usada:** `promediosSipsaCiudad`. Devuelve `ciudad`, `producto`, `precioPromedio` y
  `fechaCaptura` de cada producto en cada ciudad. Armenia tiene unos 30 productos frescos (frutas,
  verduras y tubérculos), con su precio promedio por kilogramo.
- **Tamaño:** la respuesta trae todas las ciudades y el historial desde 2020: unos 120 MB, y tarda
  alrededor de 1 minuto. El cliente la lee en streaming, guarda solo la ciudad pedida y los últimos
  `--dias`, y usa `defusedxml`, que rechaza DTD y entidades. Por ese tamaño se usa desde un comando
  y **nunca** dentro de una petición web.
- **Resiliencia:** el timeout es de 180 s (`SIPSA_SOAP_TIMEOUT_S`). Si SIPSA falla, el comando
  termina con un mensaje claro y la comparación sigue funcionando con los datos anteriores.

```bash
python manage.py importar_sipsa --servicio-web                    # Armenia, últimos 7 días
python manage.py importar_sipsa --servicio-web --crear-faltantes  # crea los frescos que falten
python manage.py importar_sipsa --servicio-web --ciudad PEREIRA --dias 3
```

`--crear-faltantes` crea cada producto que falta en el catálogo con los servicios del catálogo:

- categoría «Frutas y verduras» (perecedera), sin marca y con presentación de 1 kg;
- respeta la regla de duplicados (D-05): si el nombre se parece a uno existente, no crea otro y lo
  informa.

Sin la opción, los productos que no están en el catálogo solo se informan. El catálogo de prueba
(`data/demo/`) no tiene frescos, así que la primera vez conviene usar la opción.

**Prueba real (17 de noviembre de 2026):** tardó 1 min 7 s y dejó 90 precios de referencia de
Armenia: 30 productos, con datos del 9, 10 y 12 de noviembre.

**Frecuencia:** una vez al día, después de las 2 p. m. Se corre a mano (en local con la
`DATABASE_URL` de producción, o en la consola del PaaS). Si más adelante hay un worker o un cron,
se programa ahí.

Las otras operaciones (`promediosSipsaSemanaMadr`, `promediosSipsaMesMadr`, `promediosSipsaParcial`,
`promedioAbasSipsaMesMadr` y `consultarInsumosSipsaMesMadr`) son de mercados mayoristas,
abastecimiento e insumos agrícolas. No se usan: no son precios comparables para la canasta.

## Importar un archivo

1. Descarga del sitio del DANE (SIPSA → precios mayoristas → boletín diario) la tabla del día, en
   CSV o en Excel guardado como CSV.
2. Deja solo las columnas **producto**, **mercado**, **precio** (precio promedio por kilogramo, en
   pesos) y **fecha**. Los encabezados pueden llevar tildes o mayúsculas, y el separador puede ser
   `;` o `,`. Los precios aceptan formato colombiano (`4.500`, `$ 4.500,50`) y las fechas
   `AAAA-MM-DD` o `DD/MM/AAAA`.
3. Ejecuta:

   ```bash
   python manage.py importar_sipsa ruta/al/archivo.csv
   python manage.py importar_sipsa archivo.csv --codificacion latin-1   # si Excel lo guardó en ANSI
   ```

El comando:

- asocia cada fila a un producto del catálogo por nombre normalizado, exacto o con similitud ≥ 0,85;
- informa las filas sin producto;
- informa las filas con errores, indicando la línea;
- se puede repetir sin duplicar: actualiza `(producto, mercado, fecha)`.

Ejemplo de archivo válido:

```csv
producto;mercado;precio;fecha
Arroz blanco;Armenia, Mercar;4.180;14/11/2026
Papa pastusa;Armenia, Mercar;1.950;14/11/2026
```
