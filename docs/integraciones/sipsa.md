# Integración SIPSA (DANE) · RF-07

El Sistema de Información de Precios y Abastecimiento del Sector Agropecuario (SIPSA) del DANE
publica precios **mayoristas** diarios por mercado. La plataforma los muestra como **referencia**,
en una tarjeta aparte de la comparación. Nunca entran al orden neutral (EC-06), porque no son
precios de venta al público en tiendas del Quindío.

## Estado

| Pieza | Estado |
|---|---|
| Importación desde CSV descargado a mano (`importar_sipsa`) | **Implementada** |
| Cliente en línea `ClienteSipsa.precios_del_dia` | **Pendiente**: lanza `SipsaNoDisponibleError` |

El cliente en línea sigue pendiente porque el DANE no publica una API estable y documentada con
términos de uso para consumo automático. Cuando exista, `ClienteSipsa` debe implementar el puerto
`FuentePreciosExterna` (`apps/integraciones/clients/sipsa.py`) con:

- `timeout` obligatorio (`SIPSA_TIMEOUT_S`);
- `SIPSA_BASE_URL` por variable de entorno;
- degradación sin error visible: si SIPSA falla, la comparación sigue funcionando.

Reutiliza `apps/integraciones/domain/sipsa.py` para interpretar precios y fechas.

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
