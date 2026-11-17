# Evidencia: búsqueda por foto encuentra el producto del catálogo

- **Fecha:** 2026-11-16 · **Rama:** `fix/foto-encuentra-productos`
- **Cómo:** `runserver` local con `ANTHROPIC_API_KEY` en el `.env` (la clave no se muestra ni se
  versiona), la base local con los datos de `data/demo/`, y `POST /buscar-por-foto/` con cada foto
  (HTMX, con CSRF).
- **Fotos:** portadas públicas de Open Food Facts (CC-BY-SA), no fotos tomadas en una tienda:
  - Arroz Diana: código 7702511000021
  - Spaghetti Doria: 7702085013021
  - Café Sello Rojo: 7702032110988
  - Nutella 3017620422003, que no está en el catálogo
  
  Las imágenes no se versionan.

| Foto | Lo que leyó la IA (nombre · marca · tamaño) | Primer candidato | ¿Correcto? |
|---|---|---|---|
| Arroz Diana | Arroz · Diana · 1000 g | Arroz blanco premium · Diana | Sí |
| Spaghetti Doria | Spaghetti · Doria · 500 g | Spaghetti · Doria (luego Comarrico, La Muñeca, Monticello, Barilla) | Sí |
| Café Sello Rojo | Café molido · Sello Rojo | Café molido · Sello Rojo (luego Café molido sin marca, Águila Roja, Juan Valdez) | Sí |
| Nutella (no existe en el catálogo) | Crema de avellanas · Nutella · 400 g | Ninguno: «Aún no está en nuestro catálogo», con el botón «Buscar «Crema de avellanas» por texto» y «Solicitar este producto» | Sí |

Antes del arreglo, las tres primeras fotos respondían «Aún no está en nuestro catálogo». La causa
era que se buscaba la frase «Arroz Diana» completa. Lo reproduce
`tests/integration/test_foto_encuentra_productos.py`.

**Observación:** la IA leyó «1000 g», pero el catálogo tiene «1 kg». El bono por presentación compara
la cantidad y la unidad tal como vienen, así que aquí no sumó. Aun así, la marca y el nombre
bastaron. Una mejora futura es convertir a la unidad base antes de comparar.
